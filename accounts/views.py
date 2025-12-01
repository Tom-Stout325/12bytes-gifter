from __future__ import annotations

from datetime import date
import calendar
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.contrib.staticfiles import finders
from django.db import transaction
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    ParentRegistrationForm,
    ChildCreateForm,
    ProfileSetupForm,
    ProfileEditForm,
    FamilySetupForm,
    AccountSettingsForm,
)
from .models import Profile, Family
from gifter.models import WishlistItem

User = get_user_model()






# --- Help page (public) ---
def help(request):
    """Public help/FAQ page with getting-started instructions."""
    return render(request, "accounts/help.html")


def _is_admin(user) -> bool:
    return bool(user.is_superuser or user.is_staff)



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
    return True  


def home(request):
    """
    Anonymous → full-screen home with Login/Register.
    Authenticated:
      - parent not approved      → pending_approval page
      - approved but incomplete  → profile edit w/ warning
      - approved + complete      → gifter:all_families
    """
    if not request.user.is_authenticated:
        return render(request, "accounts/home.html")

    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"is_approved": False},
    )

    # --- Approval gate for parents ---
    if profile.is_parent and not profile.is_approved:
        messages.info(
            request,
            "Your parent account is pending approval from an admin. "
            "You’ll be able to manage your family once approved."
        )
        return redirect("accounts:pending_approval")

    # --- Profile completeness gate (for everyone else) ---
    if not _profile_complete(profile):
        messages.warning(request, "Please complete your profile before continuing.")
        return redirect("accounts:profile_edit")

    # --- Fully approved + complete: send into Gifter ---
    return redirect("gifter:all_families")





def post_login_redirect(request):
    """Compatibility route; just use home logic."""
    return home(request)



class RootLoginView(LoginView):
    """Redirect authenticated users using home routing."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return home(request)
        return super().dispatch(request, *args, **kwargs)


# ---------------------------
# Registration
# ---------------------------

@transaction.atomic
def register(request):
    """
    Registration view for new Parent accounts.

    Flow:
    - User fills in basic info + chooses to create or join a Family.
    - We create the User and Parent Profile (is_approved = False).
    - We either create a new Family or link to an existing one.
    - We assign the user into parent1 / parent2 slot if available.
    - We then redirect to 'pending_approval' so the admin can approve.
    """

    if request.method == "POST":
        form = ParentRegistrationForm(request.POST)
        if form.is_valid():
            # ----- 1. Create the User -----
            user = form.save(commit=False)
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.email = form.cleaned_data["email"]
            user.save()

                        # ----- 2. Resolve family (create or join) -----
            new_family_name = form.cleaned_data.get("new_family_name")
            existing_family = form.cleaned_data.get("existing_family")

            if new_family_name:
                # Create a new family with the provided display name
                family = Family.objects.create(display_name=new_family_name)
            else:
                # Join the chosen existing family
                family = existing_family


            # ----- 3. Create or update Profile as Parent -----
            profile, created = Profile.objects.get_or_create(user=user)
            profile.role = Profile.ROLE_PARENT
            profile.family = family
            profile.is_approved = False  # admin will flip this later
            profile.save()

            # ----- 4. Assign parent slot on the family -----
            # Note: we already validated open slots in the form, so this should succeed.
            family.assign_parent_slot(user)

            # ----- 5. (Optional) Notify admin for approval -----
            # You already have email logic somewhere; keep or move it here.
            # For example:
            #
            # from django.core.mail import send_mail
            # send_mail(
            #     subject="New Gifter parent registration pending approval",
            #     message=f"A new parent has registered: {user.get_full_name()} ({user.username})",
            #     from_email=settings.DEFAULT_FROM_EMAIL,
            #     recipient_list=[settings.ADMINS[0][1]]  # or another address
            # )

            # ----- 6. Redirect to "pending approval" page -----
            # You already have a 'pending_approval' view/URL in accounts.
            return redirect("accounts:pending_approval")
    else:
        form = ParentRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})

# ---------------------------
# Profile Setup & Edit
# ---------------------------

@login_required
def profile_setup(request):
    """
    Onboarding: select role/family (parents optional), optional dates, avatar pick/upload.
    If role=Parent and a family is chosen, atomically assign the next open parent slot.
    """
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"is_approved": False},
    )

    if request.method == "POST":
        form = ProfileSetupForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            prof = form.save(commit=False)

            # Assign parent slot if applicable
            if prof.role == Profile.ROLE_PARENT and prof.family_id:
                with transaction.atomic():
                    Family.objects.select_for_update().get(
                        pk=prof.family_id
                    ).assign_parent_slot(request.user)

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

    # Build avatar gallery list for the modal
    avatar_dir = os.path.join(settings.BASE_DIR, "static", "images", "avatars", "users")
    try:
        available_avatars = sorted(
            f for f in os.listdir(avatar_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        )
    except FileNotFoundError:
        available_avatars = []

    return render(
        request,
        "accounts/profile_setup.html",
        {
            "form": form,
            "profile": profile,
            "available_avatars": available_avatars,
        },
    )


from django.contrib.auth import get_user_model
User = get_user_model()


@login_required
def profile_edit(request):
    """
    Full editor with user fields and avatar controls.

    - By default edits the logged-in user's profile.
    - If ?child=<username> is present AND the viewer has permission,
      edits that child's profile instead.
    """
    viewer_profile = get_object_or_404(Profile, user=request.user)

    # Optional child username from query string (used by "Edit Child's Profile" button)
    child_username = request.GET.get("child")

    # Default target is the viewer themself
    target_user = request.user
    target_profile = viewer_profile

    if child_username:
        # Look up the child user/profile
        target_user = get_object_or_404(User, username=child_username)
        target_profile = get_object_or_404(Profile, user=target_user)

        # Permission check: can this viewer edit this profile?
        if not viewer_profile.can_edit_profile(target_profile):
            # You can use PermissionDenied or a friendlier redirect + message if you prefer
            raise Http404("You do not have permission to edit this profile.")

    if request.method == "POST":
        form = ProfileEditForm(
            request.POST,
            request.FILES,
            instance=target_profile,
            user=target_user,           # <-- who we're editing (child or self)
            viewer_profile=viewer_profile,  # <-- who is doing the editing
        )
        if form.is_valid():
            prof = form.save()

            # Parent-slot assignment only applies to parent profiles
            if prof.role == Profile.ROLE_PARENT and prof.family_id:
                with transaction.atomic():
                    Family.objects.select_for_update().get(
                        pk=prof.family_id
                    ).assign_parent_slot(target_user)

            messages.success(request, "Profile updated.")
            return redirect("accounts:profile_detail", username=target_user.username)
    else:
        form = ProfileEditForm(
            instance=target_profile,
            user=target_user,
            viewer_profile=viewer_profile,
        )

    avatar_dir = os.path.join(settings.BASE_DIR, "static", "images", "avatars", "users")
    available_avatars = sorted(
        [
            f
            for f in os.listdir(avatar_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
        ]
    )

    return render(
        request,
        "accounts/profile_edit.html",
        {
            "form": form,
            "profile": target_profile,  
            "setup_mode": False,
            "available_avatars": available_avatars,
        },
    )



@login_required
@transaction.atomic
def add_child(request):
    """
    Allow an approved Parent to create a Child user within their family.

    - Child gets User + Profile(role=Child, family = parent's family, is_approved=True).
    - Email is optional; username is used for login.
    - Ex-parents or non-parents cannot use this view.
    """
    parent_profile = request.user.profile

    # Must be a parent with a family (and, by our earlier logic, already approved)
    if not parent_profile.is_parent:
        raise Http404("Only parents can add children.")
    if not parent_profile.family:
        messages.error(request, "You must have a family set up before adding children.")
        return redirect("accounts:profile_setup")

    if request.method == "POST":
        form = ChildCreateForm(request.POST)
        if form.is_valid():
            # --- 1. Create the child User ---
            child_user = form.save(commit=False)
            child_user.first_name = form.cleaned_data["first_name"]
            child_user.last_name = form.cleaned_data["last_name"]
            # Email is optional; it's OK if it's blank
            child_user.email = form.cleaned_data.get("email", "") or ""
            child_user.save()  # will trigger the User post_save signal (profile creation + email, for now)

            # --- 2. Configure the child's Profile ---
            child_profile, _ = Profile.objects.get_or_create(user=child_user)
            child_profile.role = Profile.ROLE_CHILD
            child_profile.family = parent_profile.family
            # Children do NOT require admin approval
            child_profile.is_approved = True
            child_profile.save()

            messages.success(
                request,
                f"Child account created for {child_user.get_full_name() or child_user.username}."
            )
            return redirect("accounts:profile_detail", username=child_user.username)
    else:
        form = ChildCreateForm()

    return render(request, "accounts/add_child.html", {"form": form, "parent_profile": parent_profile})




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
    # if not target_profile.is_approved:
    #     messages.error(request, "Test")
    #     return redirect("accounts:profile_edit" if viewer_profile.user == target_user else "accounts:pending_approval")

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



@login_required
@transaction.atomic
def add_child(request):
    """
    Allow an approved Parent to create a Child user within their family.

    - Child gets User + Profile(role=Child, family = parent's family, is_approved=True).
    - Email is optional; username is used for login.
    - Ex-parents or non-parents cannot use this view.
    """
    parent_profile = request.user.profile

    # Must be a parent with a family (and, by our earlier logic, already approved)
    if not parent_profile.is_parent:
        raise Http404("Only parents can add children.")
    if not parent_profile.family:
        messages.error(request, "You must have a family set up before adding children.")
        return redirect("accounts:profile_setup")

    if request.method == "POST":
        form = ChildCreateForm(request.POST)
        if form.is_valid():
            # --- 1. Create the child User ---
            child_user = form.save(commit=False)
            child_user.first_name = form.cleaned_data["first_name"]
            child_user.last_name = form.cleaned_data["last_name"]
            # Email is optional; it's OK if it's blank
            child_user.email = form.cleaned_data.get("email", "") or ""
            child_user.save()  # will trigger the User post_save signal (profile creation + email, for now)

            # --- 2. Configure the child's Profile ---
            child_profile, _ = Profile.objects.get_or_create(user=child_user)
            child_profile.role = Profile.ROLE_CHILD
            child_profile.family = parent_profile.family
            # Children do NOT require admin approval
            child_profile.is_approved = True
            child_profile.save()

            messages.success(
                request,
                f"Child account created for {child_user.get_full_name() or child_user.username}."
            )
            return redirect("accounts:profile_detail", username=child_user.username)
    else:
        form = ChildCreateForm()

    return render(request, "accounts/add_child.html", {"form": form, "parent_profile": parent_profile})

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


# ------------------------------------
# Admin-only in-app Family management
# ------------------------------------

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



def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """
    Move forward or backward by `delta` months.
    Returns (new_year, new_month).
    """
    new_month = month + delta
    new_year = year + (new_month - 1) // 12
    new_month = ((new_month - 1) % 12) + 1
    return new_year, new_month


@login_required
def occasions_month(request):
    """
    Show birthdays and anniversaries for a given month, grouped by day.

    Scope: all approved profiles in the system (not just the viewer's family).
    """
    today = timezone.localdate()

    # Get month/year from querystring or default to current month
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        year = today.year
        month = today.month

    # Ensure month is sane
    if month < 1 or month > 12:
        year = today.year
        month = today.month

    first_of_month = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last_of_month = date(year, month, last_day)

    viewer_profile = request.user.profile

    # All approved profiles, system-wide
    profiles_qs = (
        Profile.objects
        .select_related("user", "family")
        .filter(is_approved=True)
    )

    events: list[dict] = []

    for profile in profiles_qs:
        # Birthday
        if profile.birthday:
            try:
                bday_this_year = profile.birthday.replace(year=year)
            except ValueError:
                # e.g. Feb 29 on a non-leap year – skip for now
                bday_this_year = None

            if bday_this_year and bday_this_year.month == month:
                turning_age = year - profile.birthday.year
                events.append(
                    {
                        "date": bday_this_year,
                        "kind": "birthday",
                        "profile": profile,
                        "age": turning_age,
                        "years": None,
                    }
                )

        # Anniversary
        if profile.anniversary:
            try:
                anniv_this_year = profile.anniversary.replace(year=year)
            except ValueError:
                anniv_this_year = None

            if anniv_this_year and anniv_this_year.month == month:
                years_married = year - profile.anniversary.year
                events.append(
                    {
                        "date": anniv_this_year,
                        "kind": "anniversary",
                        "profile": profile,
                        "age": None,
                        "years": years_married,
                    }
                )

    # Sort events by date, then kind, then name
    events.sort(
        key=lambda e: (
            e["date"],
            e["kind"],
            (e["profile"].user.first_name or ""),
            (e["profile"].user.last_name or ""),
        )
    )

    # Group by date in insertion order
    grouped_events: dict[date, list[dict]] = {}
    for event in events:
        grouped_events.setdefault(event["date"], []).append(event)

    # Prev / next month
    prev_year, prev_month = _shift_month(year, month, -1)
    next_year, next_month = _shift_month(year, month, +1)

    context = {
        "month_year_label": first_of_month.strftime("%B %Y"),  # e.g. "November 2025"
        "year": year,
        "month": month,
        "grouped_events": grouped_events,
        "first_of_month": first_of_month,
        "last_of_month": last_of_month,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "today": today,
        "viewer_profile": viewer_profile,
    }

    return render(request, "accounts/occasions_month.html", context)





def service_worker(request):
    """
    Serve the service worker from the root URL so it controls the whole site.
    """
    sw_path = finders.find("js/service-worker.js")  # look inside static/js/

    if not sw_path:
        raise Http404("Service worker file not found.")

    with open(sw_path, "r", encoding="utf-8") as f:
        js = f.read()

    return HttpResponse(js, content_type="application/javascript")




def offline(request):
    return render(request, "offline.html")
