

# class RegisterForm(forms.ModelForm):
#     password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
#     confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))

#     class Meta:
#         model = User
#         fields = ["first_name", "last_name", "username", "email"]
#         widgets = {
#             "first_name": forms.TextInput(attrs={"class": "form-control"}),
#             "last_name": forms.TextInput(attrs={"class": "form-control"}),
#             "username": forms.TextInput(attrs={"class": "form-control"}),
#             "email": forms.EmailInput(attrs={"class": "form-control"}),
#         }

#     def clean(self):
#         cleaned = super().clean()
#         pw = cleaned.get("password")
#         cpw = cleaned.get("confirm_password")
#         if pw and cpw and pw != cpw:
#             raise forms.ValidationError("Passwords do not match.")
#         return cleaned

