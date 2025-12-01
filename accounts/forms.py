from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
User = get_user_model()

from .models import Profile, Family

User = get_user_model()




# ---------------------------
# Registration
# ---------------------------

class ParentRegistrationForm(UserCreationForm):
    """
    Registration form for new Parent users.

    - Always creates a Parent profile.
    - Parent can either create a new Family OR join an existing one.
    """

    # Basic user fields
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)

    # Family options (no more family_mode)
    new_family_name = forms.CharField(
        max_length=200,
        required=False,
        help_text=(
            "Create your family name. For example: Tom & Leslie, "
            "Grandma Susan, or The Rivera Household."
        ),
        label="New family name",
    )

    existing_family = forms.ModelChoiceField(
        queryset=Family.objects.all().order_by("display_name"),
        required=False,
        label="Select existing family to join",
        help_text="Choose your spouse/partner's family if it already exists.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )

    def clean(self):
        """
        Enforce that the user either:
        - Enters a new_family_name, OR
        - Selects an existing_family,
        but not both and not neither.
        """
        cleaned_data = super().clean()
        new_family_name = cleaned_data.get("new_family_name")
        existing_family = cleaned_data.get("existing_family")

        if not new_family_name and not existing_family:
            msg = "Please enter a new family name or select an existing family."
            self.add_error("new_family_name", msg)
            self.add_error("existing_family", msg)

        if new_family_name and existing_family:
            msg = "Choose either a new family name or an existing family, not both."
            self.add_error("new_family_name", msg)
            self.add_error("existing_family", msg)

        return cleaned_data




class ChildCreateForm(UserCreationForm):
    """
    Form for parents to create a child account.

    - Email is optional (username will be used for login).
    - Profile role/family will be set in the view.
    """

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="First name",
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Last name",
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        label="Email (optional)",
        help_text="Optional. Teens can use their email, younger kids can leave this blank.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }



# ---------------------------
# Onboarding: lean setup (role/family/dates)
# ---------------------------

class ProfileSetupForm(forms.ModelForm):
    """
    Onboarding form: role/family/dates + avatar choice + sizes/favorites.
    Mirrors the fields rendered in profile_setup.html so all inputs persist.
    Hides private notes for children.
    """
    class Meta:
        model = Profile
        fields = [
            # core setup fields
            "role", "family", "birthday", "anniversary",
            # avatar selection
            "avatar_source", "avatar_library_filename", "avatar_upload",
            # clothing sizes & favorites
            "shirt_size", "pants_size", "shoe_size",
            "hobbies_sports", "favorite_stores", "favorite_websites",
            "private_notes",
        ]
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
            "family": forms.Select(attrs={"class": "form-select"}),
            "birthday": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "anniversary": forms.DateInput(attrs={"type": "date", "class": "form-control"}),

            # avatar widgets (consistent with ProfileEditForm)
            "avatar_source": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "avatar_library_filename": forms.HiddenInput(),
            "avatar_upload": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),

            # sizes & favorites
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

        # Family optional for setup
        self.fields["family"].required = False

        # Friendly label for role dropdown
        self.fields["role"].empty_label = "Select your role…"

        # Hide private notes from children
        if self.instance and self.instance.role == Profile.ROLE_CHILD:
            self.fields.pop("private_notes", None)
        class ProfileSetupForm(forms.ModelForm):

            def clean(self):
                cleaned = super().clean()
                src = cleaned.get("avatar_source")

                if src == Profile.AVATAR_SOURCE_DEFAULT:
                    # ignore any previously chosen gallery/upload
                    cleaned["avatar_library_filename"] = ""
                    cleaned["avatar_upload"] = None

                elif src == Profile.AVATAR_SOURCE_LIBRARY:
                    # keep filename, drop upload
                    cleaned["avatar_upload"] = None

                elif src == Profile.AVATAR_SOURCE_UPLOAD:
                    # keep upload, drop filename
                    cleaned["avatar_library_filename"] = ""

                return cleaned

            def save(self, commit=True):
                """Apply normalization to the instance so it persists exactly as chosen."""
                obj = super().save(commit=False)
                src = self.cleaned_data.get("avatar_source")

                if src == Profile.AVATAR_SOURCE_DEFAULT:
                    obj.avatar_library_filename = ""
                    obj.avatar_upload = None

                elif src == Profile.AVATAR_SOURCE_LIBRARY:
                    # filename already in cleaned_data via hidden field
                    obj.avatar_upload = None

                elif src == Profile.AVATAR_SOURCE_UPLOAD:
                    obj.avatar_library_filename = ""

                if commit:
                    obj.save()
                return obj




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

        if self.user:
            self.user.first_name = self.cleaned_data.get("first_name", self.user.first_name)
            self.user.last_name  = self.cleaned_data.get("last_name",  self.user.last_name)
            self.user.username   = self.cleaned_data.get("username",   self.user.username)
            self.user.email      = self.cleaned_data.get("email",      self.user.email)
            self.user.save()

        src = self.cleaned_data.get("avatar_source")
        if src == Profile.AVATAR_SOURCE_DEFAULT:
            profile.avatar_library_filename = ""
            profile.avatar_upload = None
        elif src == Profile.AVATAR_SOURCE_LIBRARY:
            profile.avatar_upload = None
        elif src == Profile.AVATAR_SOURCE_UPLOAD:
            profile.avatar_library_filename = ""

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
