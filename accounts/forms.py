from django import forms
from .models import Profile, Family


class ProfileSetupForm(forms.ModelForm):
    """
    Form shown after registration so the user can finish their profile.
    Also used by users to update their info later.
    """

    class Meta:
        model = Profile
        fields = [
            "family",
            "role",
            "avatar_choice",
            "avatar_upload",
            "birthday",
            "anniversary",
            "shirt_size",
            "pants_size",
            "shoe_size",
            "hobbies_sports",
            "favorite_stores",
            "favorite_websites",
            "private_notes",
        ]
        widgets = {
            "family": forms.Select(attrs={"class": "form-select"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "avatar_choice": forms.TextInput(attrs={"class": "form-control", "placeholder": "optional preset avatar key"}),
            "avatar_upload": forms.ClearableFileInput(attrs={"class": "form-control"}),

            "birthday": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "anniversary": forms.DateInput(attrs={"class": "form-control", "type": "date"}),

            "shirt_size": forms.TextInput(attrs={"class": "form-control"}),
            "pants_size": forms.TextInput(attrs={"class": "form-control"}),
            "shoe_size": forms.TextInput(attrs={"class": "form-control"}),

            "hobbies_sports": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "favorite_stores": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "favorite_websites": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "private_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        # We'll optionally pass request.user.profile into this form so we can
        # hide private_notes for Child users filling out their own profile.
        viewer_profile = kwargs.pop("viewer_profile", None)
        super().__init__(*args, **kwargs)

        # If the logged-in user is a Child editing themself,
        # they should not even see private_notes.
        if viewer_profile and not viewer_profile.is_parent():
            self.fields.pop("private_notes", None)
