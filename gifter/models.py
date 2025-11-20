from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from accounts.models import Profile


class WishlistItem(models.Model):

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
        help_text="This item is wanted by this profile (the gift receiver).",
    )

    title = models.CharField(
        max_length=200,
        help_text="Short name of the item, e.g. 'PS5 Controller'.",
    )

    description = models.TextField(
        blank=True,
        help_text="Details, color, size, notes.",
    )

    link = models.URLField(
        max_length=500,
        blank=True,
        help_text="Optional link to buy this item.",
    )

    price_estimate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Approx price or budget for this item (e.g. 29.99).",
    )

    image = models.ImageField(
        upload_to="wishlist/",
        blank=True,
        null=True,
        help_text="Optional photo / screenshot of the item.",
    )

    # Claim / purchase state ---------------------------------------------

    is_claimed = models.BooleanField(
        default=False,
        help_text="Someone said they plan to buy this.",
    )
    claimed_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        related_name="claims_made",
        blank=True,
        null=True,
        help_text="Which profile claimed this item.",
    )
    claimed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    is_purchased = models.BooleanField(
        default=False,
        help_text="Item has been purchased.",
    )
    purchased_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        related_name="purchases_made",
        blank=True,
        null=True,
        help_text="Which profile bought this item.",
    )
    purchased_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # newest first

    def __str__(self):
        return f"{self.title} ({self.profile.user.get_full_name() or self.profile.user.username})"

    # --------------------------
    # Business logic helpers
    # --------------------------

    def can_edit(self, viewer_profile: Profile) -> bool:
        """
        Who can edit/delete/update this wishlist item?

        - The owner of the wishlist (the profile this item belongs to) can edit.
        - A Parent in the same Family can edit Child wishlist items.
        - Otherwise no.
        """
        if viewer_profile.pk == self.profile.pk:
            return True
        if viewer_profile.can_edit_profile(self.profile):
            return True
        return False

    def can_parent_claim(self, viewer_profile: Profile) -> bool:
        """
        Who can mark 'claim' or 'purchase'?
        - Only Parent profiles.
        - Parents cannot claim an item that is already claimed by someone else
          (single claimer rule).
        """
        if not viewer_profile.is_parent:
            return False
        # prevent claiming if already claimed by someone else
        if self.is_claimed and self.claimed_by and self.claimed_by != viewer_profile:
            return False
        return True

    def claim(self, viewer_profile: Profile):
        """
        Mark this item as claimed by viewer_profile.
        Only allowed if can_parent_claim() is True.
        Sets claimed_by, claimed_at, is_claimed.
        """
        if not self.can_parent_claim(viewer_profile):
            raise PermissionError("You are not allowed to claim this item.")
        self.is_claimed = True
        self.claimed_by = viewer_profile
        if not self.claimed_at:
            self.claimed_at = timezone.now()

    def unclaim(self, viewer_profile: Profile):
        """
        Allow the claimer (or theoretically a superuser UI later) to unclaim.
        We'll keep this for future admin or parent flows.
        """
        if not viewer_profile.is_parent:
            raise PermissionError("Only parents can unclaim.")
        # Only the claimer or a parent from same family as the wishlist owner can unclaim.
        if (
            self.claimed_by
            and self.claimed_by != viewer_profile
            and not viewer_profile.can_edit_profile(self.profile)
        ):
            raise PermissionError("You cannot unclaim this item.")
        self.is_claimed = False
        self.claimed_by = None

    def mark_purchased(self, viewer_profile: Profile):
        """
        Mark item as purchased.
        Only Parent accounts can do this.
        """
        if not viewer_profile.is_parent:
            raise PermissionError("Only parents can mark purchased.")
        self.is_purchased = True
        self.purchased_by = viewer_profile
        if not self.purchased_at:
            self.purchased_at = timezone.now()

    def clear_purchased(self, viewer_profile: Profile):
        """
        Undo purchase state (adminy / parenty power).
        """
        if not viewer_profile.is_parent:
            raise PermissionError("Only parents can clear purchase state.")
        self.is_purchased = False
        self.purchased_by = None
        self.purchased_at = None


