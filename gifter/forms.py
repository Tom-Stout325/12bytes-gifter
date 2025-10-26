from django import forms
from .models import WishlistItem


class WishlistItemForm(forms.ModelForm):
    class Meta:
        model = WishlistItem
        fields = [
            "title",
            "description",
            "link",
            "price_estimate",
            "image",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Item name (ex: PS5 Controller)"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Color, size, model, details..."}
            ),
            "link": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://example.com/product"}
            ),
            "price_estimate": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "29.99", "step": "0.01", "min": "0"}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
        }
