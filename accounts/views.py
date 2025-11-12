from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    RegisterForm,
    ProfileSetupForm,
    ProfileEditForm,
    FamilySetupForm,
    AccountSettingsForm,
)
from .models import Profile, Family
from gifter.models import WishlistItem  # used in profile_detail

User = get_user_model()


# ---------------------------
# Helpers
# ---------------------------

def _profile_complete(profile: Profile) -> bool:
    """First/last/email required; any avatar source counts (default/library/upload)."""
    u = profile.user
    if not (u.first_name and u.last_name and u.email):
        return False
    if profile.avatar_source == profile.AVATAR_SOURCE_UPLOAD:
        return bool(profile.avatar_upload)
    if profile.avatar_source == profile.AVATAR_SOURCE_LIBRARY:
        return bool(profile.avatar_library_filename)
    return True  # default avatar counts


def _is_admin(user: User) -> bool:
    return bool(user.is_superuser or user.is_staff)




def home(request):
    """
    Anonymous → full-screen home with Login/Register.
    Authenticated:
      - not approved → profile detail w/ notice
      - approved but incomplete → profile edit w/ warning
      - approved + complete → gifter:all_families
    """
    if not request.user.is_authenticated:
        return render(request, "accounts/home.html")

    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"is_approved": False})

    if not profile.is_approved:
        messages.info(request, "Your profile is pending approval.")
        return redirect("accounts:profile_detail", username=request.user.username)

    if not _profile_complete(profile):
        messages.warning(request, "Please complete your profile before continuing.")
        return redirect("accounts:profile_edit")

    return redirect("gifter:all_families")


class RootLoginView(LoginView):
    """Redirect authenticated users using home routing."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return home(request)
        return super().dispatch(request, *args, **kwargs)


# ---------------------------
# Registration
# ---------------------------

def register(request):
    """
    Create a User account.
    - Profile row is created by the User post_save signal with is_approved=False.
    - Admin notification email is sent from that signal.
    - If already authenticated, route via home.
    """
    if request.user.is_authenticated:
        return home(request)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()  # triggers profile creation + admin email via signals
            messages.success(request, "Account created! Please complete your profile.")
            return redirect("accounts:profile_setup")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def post_login_redirect(request):
    """Compatibility route; just use home logic."""
    return home(request)


# ---------------------------
# Profile Setup & Edit
# ---------------------------

@login_required
def profile_setup(request):
    """
    Onboarding: select role/family (parents optional), optional dates.
    If role=Parent and a family is chosen, atomically assign the next open parent slot.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"is_approved": False})

    if request.method == "POST":
        form = ProfileSetupForm(request.POST, instance=profile)
        if form.is_valid():
            prof = form.save(commit=False)
            if prof.role == Profile.ROLE_PARENT and prof.family_id:
                with transaction.atomic():
                    Family.objects.select_for_update().get(pk=prof.family_id).assign_parent_slot(request.user)
            prof.save()
            messages.success(request, "Profile saved.")

            if not prof.is_approved:
                messages.info(request, "Your profile is pending approval.")
                return redirect("accounts:profile_detail", username=request.user.username)

            if not _profile_complete(prof):
                messages.warning(request, "Please complete your profile before continuing.")
                return redirect("accounts:profile_edit")

            return redirect("gifter:all_families")
    else:
        form = ProfileSetupForm(instance=profile)

    return render(request, "accounts/profile_setup.html", {"form": form, "profile": profile})


@login_required
def profile_edit(request):
    """
    Full editor with user fields and avatar controls; password changes via PasswordChangeView.
    """
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == "POST":
        form = ProfileEditForm(
            request.POST, request.FILES,
            instance=profile, user=request.user, viewer_profile=profile
        )
        if form.is_valid():
            prof = form.save()
            if prof.role == Profile.ROLE_PARENT and prof.family_id:
                with transaction.atomic():
                    Family.objects.select_for_update().get(pk=prof.family_id).assign_parent_slot(request.user)
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile_detail", username=request.user.username)
    else:
        form = ProfileEditForm(instance=profile, user=request.user, viewer_profile=profile)

    return render(request, "accounts/profile_form.html", {"form": form, "profile": profile, "setup_mode": False})


@login_required
def pending_approval(request):
    p = get_object_or_404(Profile, user=request.user)
    if p.is_approved:
        return redirect("gifter:all_families")
    return render(request, "accounts/pending_approval.html", {"p": p})


# ---------------------------
# Profiles & Lists
# ---------------------------

@login_required
def profile_detail(request, username):
    viewer_profile = get_object_or_404(Profile, user=request.user)
    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(Profile, user=target_user)

    # Viewer can access this page even if pending; enforce template behaviors with helpers
    if not target_profile.is_approved:
        messages.error(request, "This profile is not available yet.")
        return redirect("accounts:profile_edit" if viewer_profile.user == target_user else "accounts:pending_approval")

    wishlist_items = (
        WishlistItem.objects.filter(profile=target_profile)
        .select_related("claimed_by__user", "purchased_by__user", "profile", "profile__user")
        .order_by("-created_at")
    )

    context = {
        "target_profile": target_profile,
        "target_user": target_user,
        "wishlist_items": wishlist_items,
        "viewer_profile": viewer_profile,
        "can_view_purchase_info": viewer_profile.can_view_purchase_info_for(target_profile),
        "can_view_private_notes": viewer_profile.can_view_private_notes_for(target_profile),
        "can_edit_wishlist": viewer_profile.can_edit_profile(target_profile),
    }
    return render(request, "accounts/profile_detail.html", context)


@login_required
def profile_list(request):
    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    profiles = (
        Profile.objects.filter(is_approved=True)
        .select_related("user", "family")
        .order_by("family__display_name", "user__first_name", "user__last_name", "user__username")
    )
    return render(request, "accounts/profile_list.html", {"profiles": profiles, "viewer_profile": viewer_profile})


# ---------------------------
# Account settings (user fields only; kept for parity)
# ---------------------------

@login_required
def account_settings(request):
    if request.method == "POST":
        form = AccountSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Account settings updated.")
            return redirect("accounts:account_settings")
    else:
        form = AccountSettingsForm(instance=request.user)
    return render(request, "accounts/account_settings.html", {"form": form})


# ---------------------------
# Admin-only in-app Family management
# ---------------------------

@user_passes_test(_is_admin)
def family_manage_list(request):
    families = Family.objects.select_related("parent1", "parent2").order_by("display_name")
    return render(request, "accounts/family_manage_list.html", {"families": families})


@user_passes_test(_is_admin)
def family_manage_create(request):
    if request.method == "POST":
        form = FamilySetupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Family created.")
            return redirect("accounts:family_manage_list")
    else:
        form = FamilySetupForm()
    return render(request, "accounts/family_manage_form.html", {"form": form})


@user_passes_test(_is_admin)
def family_manage_update(request, pk: int):
    fam = get_object_or_404(Family, pk=pk)
    if request.method == "POST":
        form = FamilySetupForm(request.POST, instance=fam)
        if form.is_valid():
            form.save()
            messages.success(request, "Family updated.")
            return redirect("accounts:family_manage_list")
    else:
        form = FamilySetupForm(instance=fam)
    return render(request, "accounts/family_manage_form.html", {"form": form, "family": fam})
