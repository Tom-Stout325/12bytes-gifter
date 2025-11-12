from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import Profile

def ensure_profile(required_family=False):
    """Ensure the logged-in user has a Profile (and optionally a Family).
    Redirects to setup if missing; never 404s due to Profile/Family absence.
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            profile, _ = Profile.objects.get_or_create(
                user=request.user,
                defaults={"role": getattr(Profile, "ROLE_PARENT", "Parent")},
            )
            if required_family and not profile.family and profile.role == getattr(Profile, "ROLE_PARENT", "Parent"):
                # send parents without a family to your setup wizard/page
                return redirect("accounts:profile_setup")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
