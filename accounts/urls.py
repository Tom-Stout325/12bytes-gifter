from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("home/", views.home, name="home"),

    # Auth
    path("login/", views.RootLoginView.as_view(template_name="registration/login.html", redirect_authenticated_user=True,),name="login",),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("post-login/", views.post_login_redirect, name="post_login_redirect"),

    # Profile
    path("setup/profile/", views.profile_setup, name="profile_setup"),
    path("edit/", views.profile_edit, name="profile_edit"),
    path("profile/<str:username>/", views.profile_detail, name="profile_detail"),
    path("pending/", views.pending_approval, name="pending_approval"),
    path("profiles/", views.profile_list, name="profile_list"),
    path("settings/", views.account_settings, name="account_settings"),

    # Admin-only Family management in-app (optional UI beyond Django admin)
    path("families/manage/", views.family_manage_list, name="family_manage_list"),
    path("families/manage/new/", views.family_manage_create, name="family_manage_create"),
    path("families/manage/<int:pk>/", views.family_manage_update, name="family_manage_update"),

    # Password management (link these from your edit page)
    path(
        "password/change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url=reverse_lazy("accounts:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
    path(
        "password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
