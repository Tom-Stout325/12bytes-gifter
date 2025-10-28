from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django import forms

from .forms import ProfileForm
from .models import Profile



# --- Simple registration form ---
class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


# --- Register view ---
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, "Your account has been created! Please log in.")
            return redirect(reverse("accounts:login"))
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})



@login_required
def profile_setup(request):
    """
    After the user registers, they come here to complete their Profile.
    They can also return here later to update their info.

    This view:
    - Ensures the user has a Profile row
    - Lets them set household info, avatar, sizes, etc.
    - Enforces avatar_source / avatar_library_filename / avatar_upload logic
    """

    # 1. Ensure this user actually has a Profile.
    #    (Still doing on-demand create, though in production you might move this
    #    to a post-save signal on User.)
    profile, created = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "role": Profile.ROLE_CHILD,     # sensible default, can be changed by user
            "avatar_source": Profile.AVATAR_SOURCE_DEFAULT,
        },
    )

    # 2. Build the list of available stock avatars for the gallery.
    #    For now, we define it manually. Later, you could glob static/images/avatars/users/.
    available_avatars = [
        "avatar_1.png", "avatar_2.png", "avatar_3.png", "avatar_4.png",
        "avatar_5.png", "avatar_6.png", "avatar_7.png", "avatar_8.png",
        "avatar_9.png", "avatar_10.png", "avatar_11.png", "avatar_12.png",
        "avatar_13.png", "avatar_14.png", "avatar_15.png", "avatar_16.png",
        "avatar_17.png", "avatar_18.png", "avatar_19.png", "avatar_20.png",
        "avatar_21.png",
    ]

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
            viewer_profile=profile,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Profile saved.")

            # If your workflow requires approval (like a parent reviewing a child's profile),
            # keep that logic:
            if not profile.is_approved:
                return redirect("accounts:pending_approval")

            return redirect(
                "accounts:profile_detail",
                username=request.user.username,
            )

    else:
        form = ProfileForm(
            instance=profile,
            viewer_profile=profile,
        )

    return render(
        request,
        "accounts/profile_form.html",
        {
            "form": form,
            "profile": profile,
            "setup_mode": True,
            "available_avatars": available_avatars,
        },
    )

@login_required
def profile_edit(request):
    """
    Existing users come here to edit/update their Profile.

    This view:
    - Assumes the Profile already exists
    - Reuses the same form and template as profile_setup
    - Renders the template with setup_mode = False so the UI says "Edit Profile"
    """

    # Unlike profile_setup, we do NOT create the profile here.
    # If somehow a profile doesn't exist (shouldn't happen for normal users),
    # you can decide whether to 404 or fall back to setup.
    profile = get_object_or_404(Profile, user=request.user)

    available_avatars = [
        "avatar_1.png", "avatar_2.png", "avatar_3.png", "avatar_4.png",
        "avatar_5.png", "avatar_6.png", "avatar_7.png", "avatar_8.png",
        "avatar_9.png", "avatar_10.png", "avatar_11.png", "avatar_12.png",
        "avatar_13.png", "avatar_14.png", "avatar_15.png", "avatar_16.png",
        "avatar_17.png", "avatar_18.png", "avatar_19.png", "avatar_20.png",
        "avatar_21.png",
    ]

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
            viewer_profile=profile,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")

            # keep approval flow consistent
            if not profile.is_approved:
                return redirect("accounts:pending_approval")

            return redirect(
                "accounts:profile_detail",
                username=request.user.username,
            )

    else:
        form = ProfileForm(
            instance=profile,
            viewer_profile=profile,
        )

    return render(
        request,
        "accounts/profile_form.html",
        {
            "form": form,
            "profile": profile,
            "setup_mode": False, 
            "available_avatars": available_avatars,
        },
    )


@login_required
def pending_approval(request):
    """
    Shown if a user is logged in but not yet approved.
    They should NOT be able to browse other profiles.
    """
    profile = get_object_or_404(Profile, user=request.user)

    # If they somehow are approved now, send them to their profile.
    if profile.is_approved:
        return redirect("accounts:profile_detail", username=request.user.username)

    return render(
        request,
        "accounts/pending_approval.html",
        {"profile": profile},
    )


from gifter.models import WishlistItem
# ... keep your other imports ...


@login_required
def profile_detail(request, username):
    """
    View any user's profile page.
    - viewer must be approved
    - target must be approved
    - show wishlist items
    - hide purchase info unless rules allow
    - show private notes only to Parents
    """

    viewer_profile = get_object_or_404(Profile, user=request.user)
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(Profile, user=target_user)

    if not target_profile.is_approved:
        messages.error(request, "This profile is not available yet.")
        return redirect("gifter:home")

    # Get wishlist items for this profile (person being viewed)
    wishlist_items = (
            WishlistItem.objects.filter(profile=target_profile)
            .select_related("claimed_by__user", "purchased_by__user")
            .order_by("-created_at")
        )

        # Permission flags
    can_view_purchase_info = viewer_profile.can_view_purchase_info_for(target_profile)
    can_view_private_notes = viewer_profile.can_view_private_notes_for(target_profile)

    # NEW: who can add wishlist items for this target?
    can_edit_wishlist = viewer_profile.can_edit_profile(target_profile)

    return render(
        request,
        "accounts/profile_detail.html",
        {
            "target_profile": target_profile,
            "target_user": target_user,
            "wishlist_items": wishlist_items,
            "can_view_purchase_info": can_view_purchase_info,
            "can_view_private_notes": can_view_private_notes,
            "viewer_profile": viewer_profile,
            "can_edit_wishlist": can_edit_wishlist,
        },
    )
    
    
    
    
    
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch

@login_required
def profile_list(request):
    """
    Show all approved profiles to an approved user.
    This is mainly for testing / navigation.
    """
    viewer_profile = get_object_or_404(Profile, user=request.user)

    # Block access if the viewer themself isn't approved yet
    if not viewer_profile.is_approved:
        return redirect("accounts:pending_approval")

    # Get all approved profiles, ordered by family then name
    profiles = (
        Profile.objects
        .filter(is_approved=True)
        .select_related("user", "family")
        .order_by("family__name", "user__first_name", "user__last_name", "user__username")
    )

    return render(
        request,
        "accounts/profile_list.html",
        {
            "profiles": profiles,
            "viewer_profile": viewer_profile,
        },
    )
