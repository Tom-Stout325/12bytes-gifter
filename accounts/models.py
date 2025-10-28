from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify



User = settings.AUTH_USER_MODEL




class Family(models.Model):
    parent1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="family_as_parent1",
        limit_choices_to={"profile__role": "Parent"},
        null=True, 
    blank=True,
    )
    parent2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="family_as_parent2",
        limit_choices_to={"profile__role": "Parent"},
        null=True,  
    blank=True,
    )

    # Optional custom display name (“Anthony & Erica” or “The Stout Family”)
    display_name = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    # Housekeeping
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Family"
        verbose_name_plural = "Families"
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name or f"{self.parent1} & {self.parent2}"

    def save(self, *args, **kwargs):
        # Auto-generate display name if not manually set
        if not self.display_name:
            p1_name = self.parent1.first_name or self.parent1.username
            p2_name = self.parent2.first_name or self.parent2.username
            self.display_name = f"{p1_name} & {p2_name}"

        # Auto-create slug from display name
        if not self.slug:
            base_slug = slugify(self.display_name)
            unique_slug = base_slug
            counter = 1
            while Family.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug

        super().save(*args, **kwargs)





def user_avatar_upload_path(instance, filename):
    """
    Store uploaded avatar images at:
    media/avatars/users/<user_id>.png (or .jpg, etc.)
    We ignore the original filename and just keep the extension.
    """
    # pull extension
    ext = filename.split('.')[-1].lower()
    return f"avatars/users/{instance.user.id}.{ext}"



class Profile(models.Model):
    ROLE_PARENT = "Parent"
    ROLE_CHILD = "Child"
    ROLE_CHOICES = [
        (ROLE_PARENT, "Parent"),
        (ROLE_CHILD, "Child"),
    ]
    
    AVATAR_SOURCE_DEFAULT = "default"
    AVATAR_SOURCE_LIBRARY = "library"
    AVATAR_SOURCE_UPLOAD = "upload"

    AVATAR_SOURCE_CHOICES = [
        (AVATAR_SOURCE_DEFAULT, "Default"),
        (AVATAR_SOURCE_LIBRARY, "Library Choice"),
        (AVATAR_SOURCE_UPLOAD, "Uploaded Image"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile",)
    family = models.ForeignKey("accounts.Family", on_delete=models.SET_NULL, null=True,blank=True, related_name="members",)
    role = models.CharField(max_length=10,choices=ROLE_CHOICES,)
    
    # avatar logic
    avatar_choice = models.CharField(max_length=255, blank=True, help_text="Name/key of a preloaded avatar image.",)
    avatar_upload = models.ImageField(upload_to="avatars/", blank=True, null=True, help_text="User-uploaded avatar image.",)
    avatar_source = models.CharField(max_length=20, choices=AVATAR_SOURCE_CHOICES, default=AVATAR_SOURCE_DEFAULT, 
        help_text=(
            "Where this profile's avatar comes from: default_user.png, "
            "one of the stock library avatars, or a custom upload."),)
    avatar_library_filename = models.CharField(max_length=255, blank=True,
        help_text=(
            "Filename of a static avatar in static/images/avatars/users/, "
            "e.g. 'avatar_12.png'. Only used if avatar_source='library'."),)

    avatar_upload = models.ImageField(upload_to=user_avatar_upload_path, blank=True, null=True, help_text=(
            "User-uploaded avatar stored in media/avatars/users/. "
            "Only used if avatar_source='upload'."),)
    
    # personal dates
    birthday = models.DateField(null=True, blank=True)
    anniversary = models.DateField(blank=True, null=True, help_text="Optional anniversary date.",)

    # sizing / favorites
    shirt_size = models.CharField(max_length=50, blank=True)
    pants_size = models.CharField(max_length=50, blank=True)
    shoe_size = models.CharField(max_length=50, blank=True)

    hobbies_sports = models.TextField(blank=True)
    favorite_stores = models.TextField(blank=True)
    favorite_websites = models.TextField(blank=True)

    # private notes (parents only can view in UI)
    private_notes = models.TextField(blank=True, help_text="Visible only to Parent users in the UI.",)

    # approval gating
    is_approved = models.BooleanField(default=False, help_text="Must be true before this user can access the full app.",)

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

    def __str__(self):
            return f"Profile for {self.user.username}"

    def get_avatar_url(self):
        """
        Returns the URL that templates should use for this user's avatar <img src="...">.

        Priority:
        1. If avatar_source == 'upload' and we have an uploaded file, use that.
        2. If avatar_source == 'library' and we have a library filename, build static path.
        3. Otherwise fall back to the default_user.png static avatar.
        """

        # Case 1: user-uploaded avatar
        if (
            self.avatar_source == self.AVATAR_SOURCE_UPLOAD
            and self.avatar_upload
            and hasattr(self.avatar_upload, "url")
        ):
            return self.avatar_upload.url  # served from MEDIA_URL

        # Case 2: picked from library
        if (
            self.avatar_source == self.AVATAR_SOURCE_LIBRARY
            and self.avatar_library_filename
        ):
            # Build a static-style path.
            # This assumes your library avatars live in:
            #   static/images/avatars/users/<filename>
            return settings.STATIC_URL + "images/avatars/users/" + self.avatar_library_filename

        # Case 3: default
        # Fallback to default_user.png in static/images/avatars/
        return settings.STATIC_URL + "images/avatars/default_user.png"
    
    
    
    