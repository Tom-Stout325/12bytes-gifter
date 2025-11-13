from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from .models import Profile, Family

User = get_user_model()


# ---------------------------
# Registration
# ---------------------------

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))

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
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


# ---------------------------
# Onboarding: lean setup (role/family/dates)
# ---------------------------

class ProfileSetupForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            # household / role
            "role", "family",

            # avatar controls used by the template + JS
            "avatar_source", "avatar_library_filename", "avatar_upload",

            # personal info shown on the page
            "birthday", "anniversary",

            # clothing sizes shown on the page
            "shirt_size", "pants_size", "shoe_size",

            # favorites & notes (since the template renders them)
            "hobbies_sports", "favorite_stores", "favorite_websites", "private_notes",
        ]
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
            "family": forms.Select(attrs={"class": "form-select"}),

            # avatar widgets to match edit form styling
            "avatar_source": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "avatar_library_filename": forms.HiddenInput(),
            "avatar_upload": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),

            "birthday": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "anniversary": forms.DateInput(attrs={"type": "date", "class": "form-control"}),

            "shirt_size": forms.TextInput(attrs={"class": "form-control"}),
            "pants_size": forms.TextInput(attrs={"class": "form-control"}),
            "shoe_size": forms.TextInput(attrs={"class": "form-control"}),

            "hobbies_sports": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "favorite_stores": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "favorite_websites": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "private_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["family"].required = False
        self.fields["role"].empty_label = "Select your role…"



# ---------------------------
# Full editor: includes user fields + avatar + preferences
# ---------------------------

class ProfileEditForm(forms.ModelForm):
    # Editable user fields
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": "form-control"}))

    class Meta:
        model = Profile
        fields = [
            # user fields injected above
            "first_name", "last_name", "username", "email",
            # profile fields
            "family", "role",
            "avatar_source", "avatar_library_filename", "avatar_upload",
            "birthday", "anniversary",
            "shirt_size", "pants_size", "shoe_size",
            "hobbies_sports", "favorite_stores", "favorite_websites",
            "private_notes",
        ]
        widgets = {
            "family": forms.Select(attrs={"class": "form-select"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "avatar_source": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "avatar_library_filename": forms.HiddenInput(),
            "avatar_upload": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "birthday": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "anniversary": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "shirt_size": forms.TextInput(attrs={"class": "form-control"}),
            "pants_size": forms.TextInput(attrs={"class": "form-control"}),
            "shoe_size": forms.TextInput(attrs={"class": "form-control"}),
            "hobbies_sports": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "favorite_stores": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "favorite_websites": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "private_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        viewer_profile = kwargs.pop("viewer_profile", None)
        super().__init__(*args, **kwargs)

        # Pre-fill user fields
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name
            self.fields["username"].initial = self.user.username
            self.fields["email"].initial = self.user.email

        # Family optional in edit
        self.fields["family"].required = False

        # Hide private_notes from children users if that’s your preference
        if viewer_profile and not viewer_profile.is_parent:
            self.fields.pop("private_notes", None)

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.exclude(pk=self.user.pk).filter(username=username) if self.user else User.objects.filter(username=username)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        qs = User.objects.exclude(pk=self.user.pk).filter(email=email) if self.user else User.objects.filter(email=email)
        if qs.exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)

        # Save related user fields
        if self.user:
            self.user.first_name = self.cleaned_data.get("first_name", self.user.first_name)
            self.user.last_name = self.cleaned_data.get("last_name", self.user.last_name)
            self.user.username = self.cleaned_data.get("username", self.user.username)
            self.user.email = self.cleaned_data.get("email", self.user.email)
            self.user.save()

        if commit:
            profile.save()
        return profile


# ---------------------------
# Admin-only Family form (parent slots optional)
# ---------------------------

class FamilySetupForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = ["display_name", "parent1", "parent2"]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "form-control"}),
            "parent1": forms.Select(attrs={"class": "form-select"}),
            "parent2": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent1"].required = False
        self.fields["parent2"].required = False


# ---------------------------
# Optional: user-only account settings (redundant with ProfileEditForm, kept for parity)
# ---------------------------

class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "username":   forms.TextInput(attrs={"class": "form-control"}),
            "email":      forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get("instance")
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.exclude(pk=self.user.pk).filter(username=username)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        qs = User.objects.exclude(pk=self.user.pk).filter(email=email)
        if qs.exists():
            raise forms.ValidationError("This email is already in use.")
        return email
