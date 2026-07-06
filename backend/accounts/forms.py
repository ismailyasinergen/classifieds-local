from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import SellerStore, UserProfile


User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["phone", "location"]



class SellerStoreForm(forms.ModelForm):
    class Meta:
        model = SellerStore
        fields = [
            "name",
            "headline",
            "description",
            "location",
            "is_active",
        ]
        labels = {
            "name": "Store name",
            "headline": "Short headline",
            "description": "About your store",
            "location": "Store location",
            "is_active": "Show my public store",
        }
        help_texts = {
            "name": "Leave blank to use your username as the store name.",
            "headline": "A short trust-building line shown on your public store and listing detail.",
            "is_active": "Turn this off to hide your public store page from buyers.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }
