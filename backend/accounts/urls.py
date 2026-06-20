from . import appeal_list_views
from . import appeal_views
from . import evidence_stage_views
from . import extra_evidence_views
from . import notice_views
from . import trust_safety_dashboard_views
from . import trust_safety_report_views
from . import verification_views
from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    MyListingsView,
    RegisterView,
    SavedListingsView,
    dashboard_view,
    logout_view,
    profile_view,
)

app_name = "accounts"


from . import seller_report_views
from . import seller_report_action_views

urlpatterns = [
    path(
        "appeals/",
        appeal_list_views.my_moderation_appeals,
        name="my_moderation_appeals",
    ),
    path(
        "appeals/<int:pk>/add-evidence/",
        extra_evidence_views.moderation_appeal_add_extra_evidence,
        name="moderation_appeal_add_extra_evidence",
    ),
    path(
        "appeals/<int:pk>/",
        appeal_views.moderation_appeal_detail,
        name="moderation_appeal_detail",
    ),
    path(
        "trust-safety/appeals/attachments/<int:pk>/stage/",
        evidence_stage_views.moderation_appeal_attachment_update_stage,
        name="moderation_appeal_attachment_update_stage",
    ),
path("dashboard/", dashboard_view, name="dashboard"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", logout_view, name="logout"),
    path("profile/", profile_view, name="profile"),

    path("trust-safety/", trust_safety_dashboard_views.trust_safety_dashboard, name="trust_safety_dashboard"),
    path("trust-safety/listings/<int:pk>/restore/", trust_safety_dashboard_views.trust_safety_restore_listing, name="trust_safety_restore_listing"),
    path("trust-safety/sellers/<int:pk>/lift-suspension/", trust_safety_dashboard_views.trust_safety_lift_seller_suspension, name="trust_safety_lift_seller_suspension"),

    path("notices/", notice_views.moderation_notices, name="moderation_notices"),
    path("notices/<int:pk>/read/", notice_views.moderation_notice_mark_read, name="moderation_notice_mark_read"),
    path("notices/read-all/", notice_views.moderation_notices_mark_all_read, name="moderation_notices_mark_all_read"),

    path("verification/", verification_views.verification_request_view, name="verification_request"),
    path("verification/queue/", verification_views.verification_queue_view, name="verification_queue"),
    path("verification/<int:pk>/approve/", verification_views.verification_approve_view, name="verification_approve"),
    path("verification/<int:pk>/reject/", verification_views.verification_reject_view, name="verification_reject"),

    path("users/<int:pk>/report/", seller_report_action_views.user_report_create, name="user_report"),
    path("seller-reports/my/", seller_report_views.my_seller_reports, name="my_user_reports"),
    path("seller-reports/admin/", seller_report_views.seller_report_admin_list, name="user_report_queue"),
    path("seller-reports/admin/<int:pk>/review/", seller_report_action_views.user_report_review, name="user_report_review"),
    path("seller-reports/admin/<int:pk>/dismiss/", seller_report_action_views.user_report_dismiss, name="user_report_dismiss"),
    path("seller-reports/admin/<int:pk>/warn/", seller_report_action_views.user_report_warn_seller, name="user_report_warn"),
    path("seller-reports/admin/<int:pk>/suspend/", seller_report_action_views.user_report_suspend_seller, name="user_report_suspend"),
    path("seller-reports/admin/<int:pk>/remove-verification/", seller_report_action_views.user_report_remove_verification, name="user_report_remove_verification"),
    path("seller-reports/admin/<int:pk>/archive-listings/", seller_report_action_views.user_report_archive_seller_listings, name="user_report_archive_listings"),
    path("seller-reports/admin/<int:pk>/block-messaging/", seller_report_action_views.user_report_block_messaging, name="user_report_block_messaging"),

    path("my-listings/", MyListingsView.as_view(), name="my_listings"),
    path("saved-listings/", SavedListingsView.as_view(), name="saved_listings"),
]

# TRUST_SAFETY_AUDIT_UI_V1
from . import trust_safety_views
from . import private_media_views

urlpatterns += [
    path("trust-safety/audit/", trust_safety_dashboard_views.trust_safety_audit, name="trust_safety_audit"),
    path("trust-safety/audit/fix-active-suspended-sellers/", trust_safety_dashboard_views.trust_safety_fix_active_suspended_sellers, name="trust_safety_fix_active_suspended_sellers"),
    path("trust-safety/audit/restore-lifted-seller-hidden-listings/", trust_safety_dashboard_views.trust_safety_restore_lifted_seller_hidden_listings, name="trust_safety_restore_lifted_seller_hidden_listings"),
]

# TRUST_SAFETY_ACTION_LOG_UI_V1
urlpatterns += [
    path("trust-safety/actions/", trust_safety_views.trust_safety_action_log, name="trust_safety_action_log"),
]

# TRUST_SAFETY_ACTION_LOG_EXPORT_V1

urlpatterns += [
    path("trust-safety/actions/export/", trust_safety_views.trust_safety_action_log_export, name="trust_safety_action_log_export"),
]

# TRUST_SAFETY_REPORT_DETAIL_UI_V1
urlpatterns += [
    path("trust-safety/listing-reports/<int:pk>/", trust_safety_report_views.trust_safety_listing_report_detail, name="trust_safety_listing_report_detail"),
    path("trust-safety/seller-reports/<int:pk>/", trust_safety_report_views.trust_safety_seller_report_detail, name="trust_safety_seller_report_detail"),
]

# TRUST_SAFETY_DETAIL_ACTIONS_V1
urlpatterns += [
    path("trust-safety/listing-reports/<int:pk>/review/", trust_safety_report_views.trust_safety_listing_report_review, name="trust_safety_listing_report_review"),
    path("trust-safety/listing-reports/<int:pk>/dismiss/", trust_safety_report_views.trust_safety_listing_report_dismiss, name="trust_safety_listing_report_dismiss"),
    path("trust-safety/listing-reports/<int:pk>/suspend/", trust_safety_report_views.trust_safety_listing_report_suspend, name="trust_safety_listing_report_suspend"),
    path("trust-safety/listing-reports/<int:pk>/archive/", trust_safety_report_views.trust_safety_listing_report_archive, name="trust_safety_listing_report_archive"),
]

# MODERATION_APPEALS_V1
urlpatterns += [
    path("notices/<int:notice_pk>/appeal/", appeal_views.moderation_appeal_create, name="moderation_appeal_create"),

    path("trust-safety/appeals/", appeal_views.moderation_appeal_queue, name="moderation_appeal_queue"),
    path("trust-safety/appeals/<int:pk>/", appeal_views.moderation_appeal_admin_detail, name="moderation_appeal_admin_detail"),
    path("trust-safety/appeals/<int:pk>/evidence.zip/", appeal_views.moderation_appeal_evidence_zip, name="moderation_appeal_evidence_zip"),
    path("trust-safety/appeals/<int:pk>/request-evidence/", appeal_views.moderation_appeal_request_extra_evidence, name="moderation_appeal_request_extra_evidence"),
    path("trust-safety/appeals/<int:pk>/<str:decision>/", appeal_views.moderation_appeal_decide, name="moderation_appeal_decide"),
]

# MODERATION_APPEALS_EXPORT_CSV_V1
urlpatterns += [
    path("trust-safety/appeals/export/", appeal_views.moderation_appeal_export_csv, name="moderation_appeal_export_csv"),
]

# MODERATION_APPEAL_EVIDENCE_ZIP_EXPORT_V1
urlpatterns += [
]

# MODERATION_APPEALS_BULK_EVIDENCE_ZIP_EXPORT_V1
urlpatterns += [
    path("trust-safety/appeals/evidence.zip/", appeal_views.moderation_appeal_bulk_evidence_zip, name="moderation_appeal_bulk_evidence_zip"),
]


# TRUST_SAFETY_EVENT_LOG_URLS_V1
urlpatterns += [
    path("trust-safety/events/", trust_safety_views.trust_safety_event_log, name="trust_safety_event_log"),
    path("trust-safety/events/export/", trust_safety_views.trust_safety_event_log_export, name="trust_safety_event_log_export"),
]

# PRIVATE_APPEAL_EVIDENCE_DOWNLOADS_V1
urlpatterns += [
    path("appeals/attachments/<int:pk>/download/", appeal_views.moderation_appeal_attachment_download, name="moderation_appeal_attachment_download"),
]

# PRIVATE_MEDIA_DOWNLOAD_URLS_V1
urlpatterns += [
    path("private-files/<str:app_label>/<str:model_name>/<int:pk>/<str:field_name>/download/", private_media_views.private_file_download, name="private_file_download"),
]


# VERIFICATION_ADMIN_ALIAS_V1
urlpatterns += [
    path("verification/admin/", verification_views.verification_queue_view, name="verification_admin"),
]
