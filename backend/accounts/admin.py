from django.contrib import admin

from .models import SellerStore, UserProfile


@admin.action(description="Approve seller verification")
def approve_verification(modeladmin, request, queryset):
    queryset.update(verification_status=UserProfile.VerificationStatus.APPROVED)


@admin.action(description="Reject seller verification")
def reject_verification(modeladmin, request, queryset):
    queryset.update(verification_status=UserProfile.VerificationStatus.REJECTED)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "phone",
        "location",
        "business_name",
        "verification_status",
    ]
    list_filter = [
        "verification_status",
    ]
    search_fields = [
        "user__username",
        "user__email",
        "business_name",
        "phone",
        "location",
    ]
    actions = [
        approve_verification,
        reject_verification,
    ]



@admin.register(SellerStore)
class SellerStoreAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "owner",
        "slug",
        "location",
        "is_active",
        "updated_at",
    ]
    list_filter = [
        "is_active",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "name",
        "headline",
        "description",
        "location",
        "owner__username",
        "owner__email",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]


# TRUST_SAFETY_EVENT_ADMIN_V1
from django.contrib import admin as _trust_safety_admin

try:
    from .models import TrustSafetyEvent

    @_trust_safety_admin.register(TrustSafetyEvent)
    class TrustSafetyEventAdmin(_trust_safety_admin.ModelAdmin):
        list_display = (
            "id",
            "event_type",
            "actor",
            "target_user",
            "listing",
            "created_at",
        )
        list_filter = ("event_type", "created_at")
        search_fields = (
            "title",
            "public_note",
            "internal_note",
            "actor__username",
            "actor__email",
            "target_user__username",
            "target_user__email",
            "listing__title",
        )
        readonly_fields = ("created_at",)
except _trust_safety_admin.sites.AlreadyRegistered:
    pass
