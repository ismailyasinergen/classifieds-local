from django.contrib import admin

from .models import ListingPromotion, PromotionPackage


@admin.register(PromotionPackage)
class PromotionPackageAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "package_type",
        "duration_days",
        "price",
        "priority",
        "is_active",
    ]
    list_filter = [
        "package_type",
        "is_active",
    ]
    search_fields = [
        "name",
    ]


@admin.register(ListingPromotion)
class ListingPromotionAdmin(admin.ModelAdmin):
    list_display = [
        "listing",
        "package",
        "user",
        "payment_status",
        "status",
        "price_snapshot",
        "payment_reference",
        "payment_proof",
        "paid_at",
        "starts_at",
        "ends_at",
        "created_at",
    ]
    list_filter = [
        "payment_status",
        "status",
        "package__package_type",
        "created_at",
    ]
    search_fields = [
        "listing__title",
        "user__username",
        "package__name",
        "payment_reference",
        "payment_proof",
    ]
