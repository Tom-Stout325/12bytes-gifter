from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import Profile

def ensure_profile(required_family=False):
    """
    Ensure the logged-in user has a Profile (and optionally a Family).

    - Always creates a Profile row if missing.
    - If the user is a Parent and not approved, redirect to pending_approval.
    - If required_family=True and a Parent has no family, redirect to profile_setup.
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            profile, _ = Profile.objects.get_or_create(
                user=request.user,
                defaults={"role": getattr(Profile, "ROLE_PARENT", "Parent")},
            )

            # --- Global approval gate for parents ---
            if profile.is_parent and not profile.is_approved:
                return redirect("accounts:pending_approval")

            # --- Optional family requirement for parents ---
            if (
                required_family
                and profile.is_parent
                and not profile.family
            ):
                # send parents without a family to your setup wizard/page
                return redirect("accounts:profile_setup")

            return view_func(request, *args, **kwargs)

        return _wrapped
    return decorator
