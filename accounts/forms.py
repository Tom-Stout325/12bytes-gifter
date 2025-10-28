from django import forms
from .models import Profile


class ProfileForm(forms.ModelForm):
    """
    Form for creating/updating a user's profile, including:
    - household info (family, role)
    - avatar selection (default / library / upload)
    - personal info (sizes, dates, preferences)
    - private notes (hidden from children)
    """

    class Meta:
        model = Profile
        fields = [
            # Household relationship / permissions
            "family",
            "role",

            # Avatar controls
            "avatar_source",
            "avatar_library_filename",
            "avatar_upload",

            # Personal / gift helper info
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
            # Household
            "family": forms.Select(
                attrs={"class": "form-select"}
            ),
            "role": forms.Select(
                attrs={"class": "form-select"}
            ),

            # Avatar
            #
            # avatar_source is a radio with choices from Profile.AVATAR_SOURCE_CHOICES:
            #   "default" / "library" / "upload"
            "avatar_source": forms.RadioSelect(
                attrs={"class": "form-check-input"}
            ),

            # avatar_library_filename will be filled in when the user clicks
            # a preset avatar thumbnail in the gallery UI. We keep it hidden
            # so they don't have to type anything.
            "avatar_library_filename": forms.HiddenInput(),

            # avatar_upload is the user's uploaded custom avatar
            "avatar_upload": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/png,image/jpeg"}
            ),

            # Personal info
            "birthday": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "anniversary": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),

            "shirt_size": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "pants_size": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "shoe_size": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "hobbies_sports": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "favorite_stores": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "favorite_websites": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "private_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        We expect the view to optionally pass viewer_profile=<Profile of logged-in user>.
        That allows us to hide 'private_notes' from a child editing themself.
        """
        viewer_profile = kwargs.pop("viewer_profile", None)
        super().__init__(*args, **kwargs)

        # Don't let non-parents see or edit private_notes about themselves.
        # This preserves the same behavior you already had.
        if viewer_profile and not viewer_profile.is_parent():
            self.fields.pop("private_notes", None)

        # (Optional UX polish, not strictly required:
        # You could also reorder fields here or group them in the template.)

    def clean(self):
        """
        Enforce correct avatar data depending on avatar_source.

        - default: nothing else required
        - library: must include avatar_library_filename
        - upload: must include avatar_upload,
                  unless profile already HAS an upload stored and is just re-saving
        """
        cleaned_data = super().clean()

        source = cleaned_data.get("avatar_source")
        library_filename = cleaned_data.get("avatar_library_filename")
        uploaded_file = cleaned_data.get("avatar_upload")

        # Handle library avatar case
        if source == Profile.AVATAR_SOURCE_LIBRARY:
            if not library_filename:
                raise forms.ValidationError(
                    "Please choose one of the preset avatars."
                )

        # Handle upload avatar case
        if source == Profile.AVATAR_SOURCE_UPLOAD:
            # If they already had an upload on file (self.instance.avatar_upload),
            # we allow them to keep it without re-uploading every time.
            has_existing_upload = bool(self.instance and self.instance.avatar_upload)

            if not uploaded_file and not has_existing_upload:
                raise forms.ValidationError(
                    "Please upload an image to use as your avatar."
                )

        # default avatar requires nothing else
        return cleaned_data

    def save(self, commit=True):
        """
        Normalize avatar-related fields before saving, so the Profile is always
        internally consistent with the user's choice.

        Rules:
        - avatar_source = "default":
            We ignore library and upload for display, but we don't have to delete them.
        - avatar_source = "library":
            We make sure avatar_library_filename is already set (clean() enforces that).
        - avatar_source = "upload":
            The ModelForm will already have attached the uploaded file to instance.avatar_upload.
        """

        profile = super().save(commit=False)
        source = self.cleaned_data.get("avatar_source")

        if source == Profile.AVATAR_SOURCE_DEFAULT:
            # You *can* choose to cleanup here if you want things tidy:
            # profile.avatar_library_filename = ""
            # (We do NOT have to delete avatar_upload; keeping it is nice in case
            #  they switch back to 'upload' later.)
            profile.avatar_source = Profile.AVATAR_SOURCE_DEFAULT

        elif source == Profile.AVATAR_SOURCE_LIBRARY:
            profile.avatar_source = Profile.AVATAR_SOURCE_LIBRARY
            # self.cleaned_data["avatar_library_filename"] is already set.
            # we intentionally leave any previous avatar_upload in place; we just won't use it.

        elif source == Profile.AVATAR_SOURCE_UPLOAD:
            profile.avatar_source = Profile.AVATAR_SOURCE_UPLOAD
            # avatar_upload is already handled by ModelForm from request.FILES

        if commit:
            profile.save()

            # NOTE:
            # If you're doing any additional processing like resizing the uploaded
            # image or renaming it consistently, you'd do it here, after save.

        return profile
