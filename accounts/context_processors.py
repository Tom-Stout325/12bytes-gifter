# accounts/context_processors.py
from django.core.exceptions import ObjectDoesNotExist


def user_profile(request):
    """
    Adds ``user_profile`` to every template context.
    - ``None`` for anonymous users
    - ``None`` if the related Profile does not exist
    - The Profile instance otherwise
    """
    profile = None

    # ``request.user`` is always present, but may be AnonymousUser
    user = getattr(request, "user", None)

    if user and user.is_authenticated:
        try:
            profile = user.profile  # <-- your OneToOneField
        except ObjectDoesNotExist:
            # Profile row missing – safe fallback
            profile = None
        except AttributeError:
            # ``user`` has no ``profile`` attribute (should not happen)
            profile = None

    return {"user_profile": profile}