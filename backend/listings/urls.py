from django.urls import path

from .views import (
    ListingCreateView,
    ListingDeleteView,
    ListingDetailView,
    ListingListView,
    ListingUpdateView,
    listing_approve,
    listing_archive,
    listing_favorite_toggle,
    listing_feature_days_update,
    listing_feature_priority_update,
    listing_feature_toggle,
    listing_image_delete,
    listing_reject,
    listing_renew,
    listing_report_archive_listing,
    listing_report_create,
    listing_report_dismiss,
    listing_report_export_csv,
    listing_report_queue,
    listing_report_review,
    listing_report_suspend_listing,
    moderation_queue,
    my_listing_reports,
)

app_name = "listings"

urlpatterns = [
    path("listings/", ListingListView.as_view(), name="listing_list"),
    path("listings/create/", ListingCreateView.as_view(), name="listing_create"),
    path("listings/moderation/", moderation_queue, name="moderation_queue"),

    path("listings/reports/", listing_report_queue, name="report_queue"),
    path("listings/reports/export.csv", listing_report_export_csv, name="report_export_csv"),
    path("listings/reports/<int:pk>/review/", listing_report_review, name="report_review"),
    path("listings/reports/<int:pk>/dismiss/", listing_report_dismiss, name="report_dismiss"),
    path("listings/reports/<int:pk>/suspend-listing/", listing_report_suspend_listing, name="report_suspend_listing"),
    path("listings/reports/<int:pk>/archive-listing/", listing_report_archive_listing, name="report_archive_listing"),

    path("listings/my-reports/", my_listing_reports, name="my_reports"),

    path("listings/<int:pk>/", ListingDetailView.as_view(), name="listing_detail"),
    path("listings/<int:pk>/edit/", ListingUpdateView.as_view(), name="listing_update"),
    path("listings/<int:pk>/delete/", ListingDeleteView.as_view(), name="listing_delete"),
    path("listings/<int:pk>/approve/", listing_approve, name="listing_approve"),
    path("listings/<int:pk>/reject/", listing_reject, name="listing_reject"),
    path("listings/<int:pk>/archive/", listing_archive, name="listing_archive"),
    path("listings/<int:pk>/renew/", listing_renew, name="listing_renew"),
    path("listings/<int:pk>/favorite/", listing_favorite_toggle, name="listing_favorite_toggle"),
    path("listings/<int:pk>/feature/", listing_feature_toggle, name="listing_feature_toggle"),
    path("listings/<int:pk>/feature-priority/", listing_feature_priority_update, name="listing_feature_priority_update"),
    path("listings/<int:pk>/feature-days/", listing_feature_days_update, name="listing_feature_days_update"),
    path("listings/<int:pk>/report/", listing_report_create, name="listing_report"),

    path("listing-images/<int:pk>/delete/", listing_image_delete, name="listing_image_delete"),
]
