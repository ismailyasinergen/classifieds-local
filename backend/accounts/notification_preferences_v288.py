"""Authenticated notification delivery preference settings for v288."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from listings.models import NotificationDeliveryPreference


class NotificationDeliveryPreferenceFormV288(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["aria-describedby"] = f"id_{name}_helptext"

    class Meta:
        model = NotificationDeliveryPreference
        fields = [
            "listing_price_alert_email_enabled",
            "saved_search_new_listing_email_enabled",
            "saved_search_price_drop_email_enabled",
        ]
        labels = {
            "listing_price_alert_email_enabled": "Listing price-alert emails",
            "saved_search_new_listing_email_enabled": (
                "Saved-search new-listing emails"
            ),
            "saved_search_price_drop_email_enabled": (
                "Saved-search price-drop emails"
            ),
        }
        help_texts = {
            "listing_price_alert_email_enabled": (
                "Email me when a listing-specific price alert detects a new drop."
            ),
            "saved_search_new_listing_email_enabled": (
                "Email me about new listings matching enabled saved searches."
            ),
            "saved_search_price_drop_email_enabled": (
                "Email me about new price drops matching enabled saved searches."
            ),
        }


@login_required
def notification_delivery_preferences_v288(request):
    preference, _ = NotificationDeliveryPreference.objects.get_or_create(
        user=request.user,
    )
    if request.method == "POST":
        form = NotificationDeliveryPreferenceFormV288(
            request.POST,
            instance=preference,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Notification preferences updated.")
            return redirect("accounts:notification_delivery_preferences_v288")
    else:
        form = NotificationDeliveryPreferenceFormV288(instance=preference)

    return render(
        request,
        "accounts/notification_delivery_preferences_v288.html",
        {
            "form": form,
            "page_title": "Notification preferences",
        },
    )
