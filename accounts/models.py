from django.conf import settings
from django.db import models
from django.utils import timezone


class Family(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # optional convenience for later (filtering, URLs, etc.)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    # housekeeping
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Family"
        verbose_name_plural = "Families"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    ROLE_PARENT = "Parent"
    ROLE_CHILD = "Child"
    ROLE_CHOICES = [
        (ROLE_PARENT, "Parent"),
        (ROLE_CHILD, "Child"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    family = models.ForeignKey(
        Family,
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name="members",
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
    )

    # avatar logic
    avatar_choice = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name/key of a preloaded avatar image.",
    )
    avatar_upload = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        help_text="User-uploaded avatar image.",
    )

    # personal dates
    birthday = models.DateField()
    anniversary = models.DateField(
        blank=True,
        null=True,
        help_text="Optional anniversary date.",
    )

    # sizing / favorites
    shirt_size = models.CharField(max_length=50, blank=True)
    pants_size = models.CharField(max_length=50, blank=True)
    shoe_size = models.CharField(max_length=50, blank=True)

    hobbies_sports = models.TextField(blank=True)
    favorite_stores = models.TextField(blank=True)
    favorite_websites = models.TextField(blank=True)

    # private notes (parents only can view in UI)
    private_notes = models.TextField(
        blank=True,
        help_text="Visible only to Parent users in the UI.",
    )

    # approval gating
    is_approved = models.BooleanField(
        default=False,
        help_text="Must be true before this user can access the full app.",
    )

    # housekeeping
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    #
    # Convenience helpers for permissions/visibility
    #

    def is_parent(self) -> bool:
        return self.role == self.ROLE_PARENT

    def same_family_as(self, other: "Profile") -> bool:
        return self.family_id is not None and self.family_id == other.family_id

    def can_edit_profile(self, target: "Profile") -> bool:
        """
        Editing rules:
        - You can always edit yourself.
        - A Parent can edit any Child in the same Family.
        - Otherwise no.
        """
        if self.pk == target.pk:
            return True
        if self.is_parent() and target.role == self.ROLE_CHILD and self.same_family_as(target):
            return True
        return False

    def can_view_private_notes_for(self, target: "Profile") -> bool:
        """
        Viewing 'private_notes':
        - Only Parents can view.
        - Parents can view notes for anyone (including other Parents).
        - Children can never view.
        """
        return self.is_parent()

    def can_view_purchase_info_for(self, target: "Profile") -> bool:
        """
        Wishlist purchase visibility matrix:

        - Parent viewing THEMSELVES: cannot see purchase info.
        - Parent viewing SOMEONE ELSE: can see purchase info.
        - Child (anyone): cannot see purchase info.
        """
        if not self.is_parent():
            return False
        # parent looking at themselves
        if self.pk == target.pk:
            return False
        return True

    def is_fully_approved(self) -> bool:
        """
        Shortcut to check gate for app access.
        """
        return bool(self.is_approved)

    def age(self):
        """Optional helper, nice for UI. Not required but handy."""
        if not self.birthday:
            return None
        today = timezone.now().date()
        years = today.year - self.birthday.year
        # correct if birthday hasn't happened yet this year
        if (today.month, today.day) < (self.birthday.month, self.birthday.day):
            years -= 1
        return years
