from django.urls import path
from django.contrib.auth import views as auth_views

from . import views_family
from . import views

app_name = "accounts"

urlpatterns = [
    # Registration / login / logout
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="gifter:home"), name="logout"),

    # Onboarding / approval status
    path("setup/", views.profile_setup, name="profile_setup"),
    path("edit/", views.profile_edit, name="profile_edit"),
    path("pending/", views.pending_approval, name="pending_approval"),

    # Profiles
    path("profile/<str:username>/", views.profile_detail, name="profile_detail"),
    path("profiles/", views.profile_list, name="profile_list"),

    # Password change (logged-in users)
    path("password/change/", auth_views.PasswordChangeView.as_view(
        template_name="accounts/password_change.html"),
        name="password_change",
    ),
    path("password/change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="accounts/password_change_done.html"),
        name="password_change_done",
    ),

    # Password reset (forgot password flow)
    path("password/reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html"),
        name="password_reset",
    ),
    path("password/reset/sent/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path("password/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path("password/reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    
    path("families/", views_family.family_list, name="family_list"),
    path("families/<slug:slug>/", views_family.family_detail, name="family_detail"),
]
