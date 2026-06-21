from django.contrib import admin
from django.utils import timezone
from datetime import timedelta

from .models import Listing, ListingFavorite, ListingImage, ListingReport, SavedSearch


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


@admin.action(description="Approve selected listings")
def approve_listings(modeladmin, request, queryset):
    queryset.update(status=Listing.Status.APPROVED)


@admin.action(description="Reject selected listings")
def reject_listings(modeladmin, request, queryset):
    queryset.update(status=Listing.Status.REJECTED)


@admin.action(description="Mark selected listings as pending")
def mark_pending(modeladmin, request, queryset):
    queryset.update(status=Listing.Status.PENDING)


@admin.action(description="Archive selected listings")
def archive_listings(modeladmin, request, queryset):
    queryset.update(status=Listing.Status.ARCHIVED)


@admin.action(description="Renew selected listings for 30 days")
def renew_listings(modeladmin, request, queryset):
    queryset.update(
        status=Listing.Status.APPROVED,
        expires_at=timezone.now() + timedelta(days=30),
    )


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "owner",
        "price",
        "location",
        "status",
        "is_featured",
        "featured_priority",
        "featured_until",
        "created_at",
        "expires_at",
    ]
    list_filter = [
        "status",
        "category",
        "is_featured",
        "featured_priority",
        "featured_until",
        "created_at",
        "expires_at",
    ]
    search_fields = [
        "title",
        "description",
        "location",
        "owner__username",
    ]
    readonly_fields = [
        "created_at",
    ]
    inlines = [ListingImageInline]
    actions = [
        approve_listings,
        reject_listings,
        mark_pending,
        archive_listings,
        renew_listings,
    ]


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ["listing", "uploaded_at"]
    search_fields = ["listing__title"]


@admin.register(ListingFavorite)
class ListingFavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "listing", "created_at"]
    search_fields = ["user__username", "listing__title"]
    list_filter = ["created_at"]



@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = [
        "listing",
        "reporter",
        "reason",
        "status",
        "created_at",
        "reviewed_at",
    ]
    list_filter = [
        "status",
        "reason",
        "created_at",
    ]
    search_fields = [
        "listing__title",
        "reporter__username",
        "details",
        "admin_note",
    ]


# SAVED_SEARCH_FOUNDATION_V77
# SAVED_SEARCH_NOTIFICATIONS_FOUNDATION_V80
# SAVED_SEARCH_NOTIFICATION_ADMIN_POLISH_V84
@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "user",
        "user_email",
        "notification_status",
        "email_notifications_enabled",
        "last_notification_checked_at",
        "last_notification_sent_at",
        "created_at",
        "updated_at",
    ]
    search_fields = ["name", "querystring", "user__email", "user__username"]
    list_filter = [
        "email_notifications_enabled",
        "created_at",
        "updated_at",
        "last_notification_checked_at",
        "last_notification_sent_at",
    ]
    readonly_fields = [
        "notification_status",
        "user_email",
        "query_preview",
        "last_notification_checked_at",
        "last_notification_sent_at",
        "created_at",
        "updated_at",
    ]

    @admin.display(description="User email", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email or "(no email)"

    @admin.display(description="Notification status")
    def notification_status(self, obj):
        if not obj.email_notifications_enabled:
            return "Disabled"
        if not obj.user.email:
            return "Enabled, no recipient"
        if obj.last_notification_sent_at:
            return f"Last sent {obj.last_notification_sent_at:%Y-%m-%d %H:%M}"
        if obj.last_notification_checked_at:
            return f"Checked {obj.last_notification_checked_at:%Y-%m-%d %H:%M}"
        return "Enabled, never checked"

    @admin.display(description="Query preview")
    def query_preview(self, obj):
        querystring = obj.querystring or ""
        if len(querystring) > 120:
            return f"{querystring[:117]}..."
        return querystring or "(empty)"
