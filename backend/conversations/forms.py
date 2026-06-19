from django import forms

from .models import ListingMessage


class ListingMessageForm(forms.ModelForm):
    class Meta:
        model = ListingMessage
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Write your message to the seller...",
                }
            )
        }
