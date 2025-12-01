from django.contrib import admin
from .models import WishlistItem, BoardPost, BoardComment





@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "for_user",
        "family_name",
        "price_estimate",
        "is_claimed",
        "claimed_by_user",
        "is_purchased",
        "purchased_by_user",
        "updated_at",
    )
    list_filter = (
        "is_claimed",
        "is_purchased",
        "profile__family",
    )
    search_fields = (
        "title",
        "description",
        "profile__user__username",
        "profile__user__first_name",
        "profile__user__last_name",
    )
    readonly_fields = ("created_at", "updated_at", "claimed_at", "purchased_at")

    fieldsets = (
        ("Who is this gift for?", {
            "fields": ("profile",),
        }),
        ("Gift Details", {
            "fields": (
                "title",
                "description",
                "link",
                "price_estimate",
                "image",
            ),
        }),
        ("Status / Coordination", {
            "fields": (
                "is_claimed",
                "claimed_by",
                "claimed_at",
                "is_purchased",
                "purchased_by",
                "purchased_at",
            ),
            "description": "Only Parents in the app UI will see claim/purchase info.",
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def for_user(self, obj):
        u = obj.profile.user
        return u.get_full_name() or u.username
    for_user.short_description = "For"

    def family_name(self, obj):
        return obj.profile.family.name if obj.profile.family else ""
    family_name.short_description = "Family"

    def claimed_by_user(self, obj):
        if obj.claimed_by:
            u = obj.claimed_by.user
            return u.get_full_name() or u.username
        return ""
    claimed_by_user.short_description = "Claimed By"

    def purchased_by_user(self, obj):
        if obj.purchased_by:
            u = obj.purchased_by.user
            return u.get_full_name() or u.username
        return ""
    purchased_by_user.short_description = "Purchased By"



@admin.register(BoardPost)
class BoardPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at")
    list_filter = ("created_at", "author")
    search_fields = ("title", "body", "author__username", "author__first_name", "author__last_name")


@admin.register(BoardComment)
class BoardCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    list_filter = ("created_at", "author")
    search_fields = ("body", "author__username", "author__first_name", "author__last_name", "post__title")
