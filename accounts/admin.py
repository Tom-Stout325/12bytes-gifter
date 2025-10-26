from django.contrib import admin
from .models import Family, Profile


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    ordering = ("name",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user_full_name",
        "username",
        "family",
        "role",
        "is_approved",
        "birthday",
        "anniversary",
        "updated_at",
    )
    list_filter = ("is_approved", "role", "family")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "family__name",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("User Link", {
            "fields": ("user", "family", "role", "is_approved"),
        }),
        ("Identity / Avatar", {
            "fields": ("avatar_choice", "avatar_upload"),
        }),
        ("Dates", {
            "fields": ("birthday", "anniversary"),
        }),
        ("Sizes & Preferences", {
            "fields": (
                "shirt_size",
                "pants_size",
                "shoe_size",
                "hobbies_sports",
                "favorite_stores",
                "favorite_websites",
            ),
        }),
        ("Private Notes (Parents Only)", {
            "fields": ("private_notes",),
            "description": "Visible to Parent users in the UI. Children will never see this.",
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def user_full_name(self, obj):
        return obj.user.get_full_name() or "(no name)"
    user_full_name.short_description = "Name"

    def username(self, obj):
        return obj.user.username
    username.short_description = "Username"
