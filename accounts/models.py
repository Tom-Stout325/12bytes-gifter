from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, F
from django.template.defaultfilters import slugify
from django.templatetags.static import static
from typing import TYPE_CHECKING
from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


User = get_user_model()

# ---------------------------------------------------------------------
# Avatar upload path
# ---------------------------------------------------------------------
def user_avatar_upload_path(instance: "Profile", filename: str) -> str:
    """
    Store uploaded avatar images at: media/avatars/users/<user_id>.<ext>
    We ignore the original filename and keep the extension.
    """
    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    return f"avatars/users/{instance.user_id}.{ext or 'png'}"


# ---------------------------------------------------------------------
# Family
# ---------------------------------------------------------------------
class Family(models.Model):
    parent1 = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,   # never delete the family if a user is deleted
        related_name="family_as_parent1",
        limit_choices_to={"profile__role": "Parent"},
    )
    parent2 = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="family_as_parent2",
        limit_choices_to={"profile__role": "Parent"},
    )
    display_name = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Family"
        verbose_name_plural = "Families"
        ordering = ["display_name"] 
        constraints = [
            # Disallow the same user in both parent slots (unless one/both are NULL)
            models.CheckConstraint(
                check=~Q(parent1=F("parent2")) | Q(parent1__isnull=True) | Q(parent2__isnull=True),
                name="family_parent1_not_equal_parent2_or_null",
            )
        ]

    def __str__(self) -> str:
        if self.display_name:
            return self.display_name
        p1 = (self.parent1.first_name or self.parent1.username) if self.parent1 else ""
        p2 = (self.parent2.first_name or self.parent2.username) if self.parent2 else ""
        return (f"{p1} & {p2}").strip() or "Family"

    def clean(self):
        if self.parent1 and self.parent2 and self.parent1_id == self.parent2_id:
            raise ValidationError("Parent 1 and Parent 2 must be different users.")

    def save(self, *args, **kwargs):
        # Auto-generate display name if not provided; support 0/1/2 parent cases
        if not self.display_name:
            p1 = (self.parent1.first_name or self.parent1.username) if self.parent1 else ""
            p2 = (self.parent2.first_name or self.parent2.username) if self.parent2 else ""
            if p1 and p2:
                self.display_name = f"{p1} & {p2}"
            elif p1:
                self.display_name = p1
            elif p2:
                self.display_name = p2
            else:
                self.display_name = "New Family"

        # Unique slug from display name
        if not self.slug:
            base = slugify(self.display_name) or "family"
            unique = base
            n = 1
            while Family.objects.filter(slug=unique).exclude(pk=self.pk).exists():
                unique = f"{base}-{n}"
                n += 1
            self.slug = unique

        super().save(*args, **kwargs)

    @transaction.atomic
    def assign_parent_slot(self, user: "AbstractUser") -> "Family":
        """
        Safely assign a registering Parent user to parent1/parent2 if a slot is open.
        Uses a row lock to avoid race conditions.
        """
        fam = Family.objects.select_for_update().get(pk=self.pk)
        if fam.parent1_id is None:
            fam.parent1 = user
        elif fam.parent2_id is None and fam.parent1_id != user.id:
            fam.parent2 = user
        fam.save(update_fields=["parent1", "parent2"])
        return fam

# ---------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------
class Profile(models.Model):
    # Roles
    ROLE_PARENT = "Parent"
    ROLE_CHILD = "Child"
    ROLE_CHOICES = [
        (ROLE_PARENT, "Parent"),
        (ROLE_CHILD, "Child"),
    ]

    # Avatar source
    AVATAR_SOURCE_DEFAULT = "default"
    AVATAR_SOURCE_LIBRARY = "library"
    AVATAR_SOURCE_UPLOAD = "upload"
    AVATAR_SOURCE_CHOICES = [
        (AVATAR_SOURCE_DEFAULT, "Default"),
        (AVATAR_SOURCE_LIBRARY, "Library"),
        (AVATAR_SOURCE_UPLOAD, "Upload"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    family = models.ForeignKey(Family, null=True, blank=True, on_delete=models.SET_NULL, related_name="members")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, blank=True)

    # Approval gate (admin flips this to True)
    is_approved = models.BooleanField(default=False)

    # Personal dates
    birthday = models.DateField(null=True, blank=True)
    anniversary = models.DateField(null=True, blank=True)

    # Avatar fields
    avatar_source = models.CharField(max_length=20, choices=AVATAR_SOURCE_CHOICES, default=AVATAR_SOURCE_DEFAULT)
    avatar_library_filename = models.CharField(max_length=255, blank=True)
    avatar_upload = models.ImageField(upload_to=user_avatar_upload_path, blank=True, null=True)

    # Preferences / notes
    shirt_size = models.CharField(max_length=50, blank=True)
    pants_size = models.CharField(max_length=50, blank=True)
    shoe_size = models.CharField(max_length=50, blank=True)
    hobbies_sports = models.TextField(blank=True)
    favorite_stores = models.TextField(blank=True)
    favorite_websites = models.TextField(blank=True)
    private_notes = models.TextField(blank=True)

    # Audit
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return self.user.get_full_name() or self.user.username

    # ---- Convenience ----
    @property
    def is_parent(self) -> bool:
        return self.role == self.ROLE_PARENT

    def get_avatar_url(self) -> str:
        """
        Resolve the display avatar URL based on the selected source.
        - default: a project default image
        - library: static path to your preloaded avatar file
        - upload: the uploaded file's URL
        """
        if self.avatar_source == self.AVATAR_SOURCE_UPLOAD and self.avatar_upload:
            return self.avatar_upload.url
        if self.avatar_source == self.AVATAR_SOURCE_LIBRARY and self.avatar_library_filename:
            # Adjust this path to where your avatar library lives under /static
            return static(f"images/avatars/users/{self.avatar_library_filename}")
        # Default
        return static("images/avatars/default_user.png")

    # ---- Completeness for routing (first name, last name, email, avatar present) ----
    def is_complete(self) -> bool:
        if not self.user.first_name or not self.user.last_name or not self.user.email:
            return False
        # Consider default avatar acceptable as "complete" (per our plan)
        if self.avatar_source == self.AVATAR_SOURCE_UPLOAD:
            return bool(self.avatar_upload)
        if self.avatar_source == self.AVATAR_SOURCE_LIBRARY:
            return bool(self.avatar_library_filename)
        # default avatar is OK
        return True

    # ---- Permissions for wishlist visibility ----
    def can_view_private_notes_for(self, target: "Profile") -> bool:
        """
        Parents can view private notes for everyone EXCEPT themselves.
        Children never see private notes.
        """
        if not self.is_parent:
            return False
        return target.user_id != self.user_id

    def can_view_purchase_info_for(self, target: "Profile") -> bool:
        """
        Parents can view purchased/claimed info for everyone EXCEPT themselves.
        Children never see purchased/claimed info.
        """
        if not self.is_parent:
            return False
        return target.user_id != self.user_id

    def can_edit_profile(self, target: "Profile") -> bool:
        """
        Who can add/edit wishlist items for a target?
        - Parents can edit anyone in the system (adjust if you want to restrict to family)
        - A user can edit their own profile
        """
        if self.is_parent:
            return True
        return self.user_id == target.user_id

    # ---- Dates: age / years married ----
    def age(self, today: date | None = None) -> int | None:
        if not self.birthday:
            return None
        today = today or date.today()
        years = today.year - self.birthday.year
        if (today.month, today.day) < (self.birthday.month, self.birthday.day):
            years -= 1
        return years

    def years_married(self, today: date | None = None) -> int | None:
        if not self.anniversary:
            return None
        today = today or date.today()
        years = today.year - self.anniversary.year
        if (today.month, today.day) < (self.anniversary.month, self.anniversary.day):
            years -= 1
        return years

    def next_birthday_date(self, today: date | None = None) -> date | None:
        if not self.birthday:
            return None
        today = today or date.today()
        next_dt = self.birthday.replace(year=today.year)
        if next_dt < today:
            next_dt = next_dt.replace(year=today.year + 1)
        return next_dt

    def next_anniversary_date(self, today: date | None = None) -> date | None:
        if not self.anniversary:
            return None
        today = today or date.today()
        next_dt = self.anniversary.replace(year=today.year)
        if next_dt < today:
            next_dt = next_dt.replace(year=today.year + 1)
        return next_dt

    def is_upcoming_birthday(self, days: int = 60, today: date | None = None) -> bool:
        nxt = self.next_birthday_date(today)
        return bool(nxt and (nxt - (today or date.today())).days <= days)

    def is_upcoming_anniversary(self, days: int = 60, today: date | None = None) -> bool:
        nxt = self.next_anniversary_date(today)
        return bool(nxt and (nxt - (today or date.today())).days <= days)
