from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from .models import Profile, Family


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("display_name", "parent1", "parent2", "slug", "created_at")
    search_fields = ("display_name", "parent1__username", "parent1__first_name",
                     "parent2__username", "parent2__first_name")
    list_filter = ()
    readonly_fields = ("slug", "created_at")
    ordering = ("display_name",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "family",
        "is_approved",
        "birthday",
        "anniversary",
        "age_display",
        "years_married_display",
        "updated_at",
    )
    list_filter = ("role", "is_approved", "family")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "family__display_name",
    )
    ordering = ("user__first_name", "user__last_name", "user__username")

    # IMPORTANT: every readonly field must be a real model field OR a method on this admin
    readonly_fields = (
        "avatar_preview",
        "updated_at",
        "age_display",
        "years_married_display",
    )

    fields = (
        "user",
        "family",
        "role",
        "is_approved",
        ("birthday", "anniversary"),
        ("age_display", "years_married_display"),
        "avatar_source",
        "avatar_library_filename",
        "avatar_upload",
        "avatar_preview",
        "shirt_size",
        "pants_size",
        "shoe_size",
        "hobbies_sports",
        "favorite_stores",
        "favorite_websites",
        "private_notes",
        "updated_at",
    )

    # ---- readonly helpers ----
    def age_display(self, obj: Profile):
        val = obj.age()
        return "-" if val is None else val
    age_display.short_description = "Age"

    def years_married_display(self, obj: Profile):
        val = obj.years_married()
        return "-" if val is None else val
    years_married_display.short_description = "Years Married"

    def avatar_preview(self, obj: Profile):
        url = obj.get_avatar_url()
        if not url:
            return "-"
        return format_html('<img src="{}" style="height:64px;width:64px;border-radius:8px;object-fit:cover;" />', url)
    avatar_preview.short_description = "Avatar"
