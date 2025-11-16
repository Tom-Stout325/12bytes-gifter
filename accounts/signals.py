from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile

User = get_user_model()
ADMIN_NOTIFY_EMAIL = "tom@tom-stout.com"


@receiver(post_save, sender=User)
def create_profile_on_user_create(sender, instance: User, created: bool, **kwargs):
    """
    Ensure every new User gets a Profile row with is_approved=False
    and a default avatar configuration.
    """
    if not created:
        return

    Profile.objects.get_or_create(
        user=instance,
        defaults={
            "is_approved": False,
            # Explicitly set avatar_source to 'default' for new users
            "avatar_source": Profile.AVATAR_SOURCE_DEFAULT,
            # No library filename; get_avatar_url() will fall back to default_user.png
            "avatar_library_filename": "",
        },
    )

    # Notify admin of a new registration
    try:
        send_mail(
            subject="Gifter: New registration pending approval",
            message=(
                "A new user has registered:\n\n"
                f"Name: {instance.get_full_name() or instance.username}\n"
                f"Email: {instance.email or '(none provided)'}\n\n"
                "Approve in Django Admin when ready."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[ADMIN_NOTIFY_EMAIL],
            fail_silently=True,
        )
    except Exception:
        # Don't let email issues break registration
        pass
