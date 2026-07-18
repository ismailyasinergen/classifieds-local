from django.urls import path
from . import views as listing_views_v130

from .views import (
    ListingCreateView,
    ListingDeleteView,
    ListingDetailView,
    ListingListView,
    saved_search_create,
    saved_search_delete,
    saved_search_list,
    saved_search_notifications_toggle,
    ListingUpdateView,
    listing_approve,
    listing_archive,
    listing_favorite_toggle,
    listing_feature_days_update,
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
from listings.listing_promotion_views import listing_feature_priority_update
from .listing_comparison_views_v274 import (
    listing_comparison_clear_v274,
    listing_comparison_toggle_v274,
    listing_comparison_view_v274,
)
from .listing_price_alerts_v285 import listing_price_alert_toggle_v285
from .listing_price_alert_management_v289 import (
    listing_price_alert_management_v289,
    listing_price_alert_remove_v289,
)

app_name = "listings"

urlpatterns = [
    path("listings/", ListingListView.as_view(), name="listing_list"),
    path(
        "listings/price-alerts/",
        listing_price_alert_management_v289,
        name="listing_price_alert_management_v289",
    ),
    path(
        "listings/price-alerts/<int:pk>/remove/",
        listing_price_alert_remove_v289,
        name="listing_price_alert_remove_v289",
    ),
    # LISTING_COMPARISON_V274
    path(
        "listings/compare/clear/",
        listing_comparison_clear_v274,
        name="listing_compare_clear",
    ),
    path(
        "listings/compare/",
        listing_comparison_view_v274,
        name="listing_compare",
    ),
    path(
        "listings/<int:pk>/compare/",
        listing_comparison_toggle_v274,
        name="listing_compare_toggle",
    ),
    # SAVED_SEARCH_FOUNDATION_V77
    path("listings/saved-searches/", saved_search_list, name="saved_search_list"),
    path("listings/saved-searches/create/", saved_search_create, name="saved_search_create"),
    # SAVED_SEARCH_NOTIFICATIONS_FOUNDATION_V80
    path(
        "listings/saved-searches/<int:pk>/notifications/",
        saved_search_notifications_toggle,
        name="saved_search_notifications_toggle",
    ),
    path("listings/saved-searches/<int:pk>/delete/", saved_search_delete, name="saved_search_delete"),
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
    path(
        "listings/<int:pk>/price-alert/",
        listing_price_alert_toggle_v285,
        name="listing_price_alert_toggle_v285",
    ),
    path("listings/<int:pk>/feature/", listing_feature_toggle, name="listing_feature_toggle"),
    path("listings/<int:pk>/feature-priority/", listing_feature_priority_update, name="listing_feature_priority_update"),
    path("listings/<int:pk>/feature-days/", listing_feature_days_update, name="listing_feature_days_update"),
    path("listings/<int:pk>/report/", listing_report_create, name="listing_report"),

    path("listing-images/<int:pk>/delete/", listing_image_delete, name="listing_image_delete"),
    path("saved-searches/bulk/", listing_views_v130.saved_search_bulk_action, name="saved_search_bulk_action"),
    path("saved-searches/<int:pk>/rename/", listing_views_v130.saved_search_rename, name="saved_search_rename"),
]

from .saved_search_notification_audit_operator_views import (
    SavedSearchNotificationAuditEventListView,
)


V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_URL = (
    "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_URL"
)


urlpatterns.insert(
    0,
    path(
        "staff/saved-search-notification-audit/",
        SavedSearchNotificationAuditEventListView.as_view(),
        name="saved-search-notification-audit-events",
    ),
)
