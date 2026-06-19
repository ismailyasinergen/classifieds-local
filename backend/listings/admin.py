from django.contrib import admin
from django.utils import timezone
from datetime import timedelta

from .models import Listing, ListingFavorite, ListingImage, ListingReport


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
