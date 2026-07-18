from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

from .models import (
    Listing,
    ListingFavorite,
    ListingImage,
    ListingPriceAlert,
    ListingReport,
    NotificationDeliveryEvent,
    NotificationDeliveryPreference,
    SavedSearch,
)


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


@admin.register(ListingPriceAlert)
class ListingPriceAlertAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "listing",
        "baseline_price",
        "last_notified_price",
        "last_notification_sent_at",
        "created_at",
    ]
    search_fields = ["user__username", "user__email", "listing__title"]
    list_filter = ["created_at", "last_notification_sent_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(NotificationDeliveryEvent)
class NotificationDeliveryEventAdmin(admin.ModelAdmin):
    list_display = [
        "notification_type",
        "status",
        "recipient",
        "listing",
        "attempt_count",
        "created_at",
        "sent_at",
    ]
    list_filter = [
        "notification_type",
        "status",
        "created_at",
        "sent_at",
    ]
    search_fields = [
        "event_key",
        "recipient__username",
        "listing__title",
        "saved_search__name",
    ]
    list_select_related = [
        "recipient",
        "listing",
        "listing_price_alert",
        "saved_search",
        "price_transition",
    ]
    readonly_fields = [field.name for field in NotificationDeliveryEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationDeliveryPreference)
class NotificationDeliveryPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "listing_price_alert_email_enabled",
        "saved_search_new_listing_email_enabled",
        "saved_search_price_drop_email_enabled",
        "updated_at",
    ]
    list_filter = [
        "listing_price_alert_email_enabled",
        "saved_search_new_listing_email_enabled",
        "saved_search_price_drop_email_enabled",
    ]
    search_fields = ["user__username", "user__email"]
    list_select_related = ["user"]
    readonly_fields = [
        field.name for field in NotificationDeliveryPreference._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False



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
# SAVED_SEARCH_NOTIFICATION_RUNBOOK_ADMIN_POLISH_V86
# SAVED_SEARCH_NOTIFICATION_ADMIN_ACTIONS_V89
# SAVED_SEARCH_NOTIFICATION_ADMIN_LIST_POLISH_V91
@admin.action(description="Enable email notifications for selected saved searches")
def enable_saved_search_email_notifications(modeladmin, request, queryset):
    updated = queryset.update(email_notifications_enabled=True)
    modeladmin.message_user(
        request,
        f"Enabled email notifications for {updated} saved search(es).",
    )


@admin.action(description="Disable email notifications for selected saved searches")
def disable_saved_search_email_notifications(modeladmin, request, queryset):
    updated = queryset.update(email_notifications_enabled=False)
    modeladmin.message_user(
        request,
        f"Disabled email notifications for {updated} saved search(es).",
    )


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "user",
        "user_email",
        "notification_status",
        "notification_preference",
        "last_notification_checked_at",
        "last_notification_sent_at",
        "created_at",
        "updated_at",
    ]
    search_fields = ["name", "querystring", "user__email", "user__username"]
    list_select_related = ["user"]
    date_hierarchy = "updated_at"
    ordering = ["-updated_at", "-created_at"]
    list_filter = [
        "email_notifications_enabled",
        "created_at",
        "updated_at",
        "last_notification_checked_at",
        "last_notification_sent_at",
    ]
    readonly_fields = [
        "notification_run_guidance",
        "notification_status",
        "user_email",
        "query_preview",
        "last_notification_checked_at",
        "last_notification_sent_at",
        "created_at",
        "updated_at",
    ]
    actions = [
        enable_saved_search_email_notifications,
        disable_saved_search_email_notifications,
    ]

    @admin.display(description="User email", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email or "(no email)"

    @admin.display(description="Email alerts", boolean=True, ordering="email_notifications_enabled")
    def notification_preference(self, obj):
        return obj.email_notifications_enabled

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

    @admin.display(description="Notification run guidance")
    def notification_run_guidance(self, obj):
        return format_html(
            "<strong>Notifications are operator-triggered.</strong><br>"
            "Run a dry-run before using <code>--send</code>. "
            "Send failures are isolated per saved search; failed sends do not update timestamps. "
            "See <code>SAVED_SEARCH_NOTIFICATIONS.md</code> for the runbook."
        )

# V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING
# Admin-only saved-search notification visibility. This block intentionally adds
# no delivery action, no rollback action, no scheduler wiring, and no model change.
# It also preserves the legacy Email alerts preference column and preference-only
# enable/disable actions expected by existing admin smoke tests.
from django.contrib import admin as saved_search_notification_admin_site
from django.contrib.admin.sites import NotRegistered as SavedSearchNotificationAdminNotRegistered

from .models import SavedSearch as SavedSearchNotificationAdminModel


V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING = (
    "V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING"
)


try:
    saved_search_notification_admin_site.site.unregister(SavedSearchNotificationAdminModel)
except SavedSearchNotificationAdminNotRegistered:
    pass


@saved_search_notification_admin_site.register(SavedSearchNotificationAdminModel)
class SavedSearchNotificationAdmin(saved_search_notification_admin_site.ModelAdmin):
    list_display = (
        "saved_search_label",
        "owner_display",
        "notification_status",
        "notification_preference",
        "recipient_email",
        "last_checked_display",
        "last_sent_display",
    )
    list_filter = ("email_notifications_enabled",)
    search_fields = ("name", "querystring", "user__username", "user__email")
    readonly_fields = (
        "notification_status",
        "notification_preference",
        "recipient_email",
        "delivery_readiness",
        "last_checked_display",
        "last_sent_display",
    )
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    ordering = ("user__username", "name", "pk")
    actions = (
        "enable_saved_search_email_notifications",
        "disable_saved_search_email_notifications",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("user")

    @saved_search_notification_admin_site.display(description="Saved search")
    def saved_search_label(self, obj):
        if obj is None:
            return ""
        name = str(getattr(obj, "name", "") or "").strip()
        if name:
            return name
        querystring = str(getattr(obj, "querystring", "") or "").strip()
        if querystring:
            return querystring
        return f"Saved search #{getattr(obj, 'pk', '')}"

    @saved_search_notification_admin_site.display(description="Owner", ordering="user__username")
    def owner_display(self, obj):
        if obj is None:
            return ""
        user = getattr(obj, "user", None)
        username = str(getattr(user, "username", "") or "").strip()
        return username or f"User #{getattr(obj, 'user_id', '')}"

    @saved_search_notification_admin_site.display(
        description="Notification status",
        ordering="email_notifications_enabled",
    )
    def notification_status(self, obj):
        if obj is None:
            return ""
        status = "Enabled" if getattr(obj, "email_notifications_enabled", False) else "Disabled"
        checked_at = getattr(obj, "last_notification_checked_at", None)
        if checked_at is None:
            return f"{status}, never checked"
        return f"{status}, checked {checked_at}"

    @saved_search_notification_admin_site.display(
        description="Email alerts",
        boolean=True,
        ordering="email_notifications_enabled",
    )
    def notification_preference(self, obj):
        if obj is None:
            return False
        return bool(getattr(obj, "email_notifications_enabled", False))

    @saved_search_notification_admin_site.display(description="Recipient email", ordering="user__email")
    def recipient_email(self, obj):
        if obj is None:
            return ""
        user = getattr(obj, "user", None)
        email = str(getattr(user, "email", "") or "").strip()
        return email or "Missing recipient email"

    @saved_search_notification_admin_site.display(description="Delivery readiness")
    def delivery_readiness(self, obj):
        if obj is None:
            return ""
        if not getattr(obj, "email_notifications_enabled", False):
            return "Not ready: notifications disabled"
        user = getattr(obj, "user", None)
        email = str(getattr(user, "email", "") or "").strip()
        if not email:
            return "Not ready: missing recipient email"
        return "Ready for guarded notification flow"

    @saved_search_notification_admin_site.display(
        description="Last checked",
        ordering="last_notification_checked_at",
    )
    def last_checked_display(self, obj):
        if obj is None:
            return ""
        return getattr(obj, "last_notification_checked_at", None) or "Never checked"

    @saved_search_notification_admin_site.display(
        description="Last sent",
        ordering="last_notification_sent_at",
    )
    def last_sent_display(self, obj):
        if obj is None:
            return ""
        return getattr(obj, "last_notification_sent_at", None) or "Never sent"

    @saved_search_notification_admin_site.action(
        description="Enable email notifications for selected saved searches"
    )
    def enable_saved_search_email_notifications(self, request, queryset):
        updated = queryset.update(email_notifications_enabled=True)
        if request is not None:
            self.message_user(
                request,
                f"Enabled email notifications for {updated} saved search(es).",
            )

    @saved_search_notification_admin_site.action(
        description="Disable email notifications for selected saved searches"
    )
    def disable_saved_search_email_notifications(self, request, queryset):
        updated = queryset.update(email_notifications_enabled=False)
        if request is not None:
            self.message_user(
                request,
                f"Disabled email notifications for {updated} saved search(es).",
            )
