from django.contrib import admin

from .models import ListingMessage


@admin.register(ListingMessage)
class ListingMessageAdmin(admin.ModelAdmin):
    list_display = [
        "listing",
        "sender",
        "recipient",
        "is_read",
        "created_at",
    ]
    list_filter = [
        "is_read",
        "created_at",
    ]
    search_fields = [
        "listing__title",
        "sender__username",
        "recipient__username",
        "body",
    ]
