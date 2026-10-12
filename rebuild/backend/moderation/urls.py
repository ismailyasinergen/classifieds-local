from django.urls import path
from . import views
from . import report_views, appeal_views, case_media
app_name = "moderation"
urlpatterns = [
    path("", views.queue, name="queue"), path("<int:revision_id>/", views.review, name="review"),
    path("bildir/ilan/<int:revision_id>/", report_views.report_listing, name="report_listing"),
    path("bildir/mesaj/<int:message_id>/", report_views.report_message, name="report_message"),
    path("bildirimlerim/", report_views.my_reports, name="my_reports"),
    path("bildirimlerim/<uuid:report_id>/", report_views.report_detail, name="report_detail"),
    path("kararlarim/", report_views.my_decisions, name="my_decisions"),
    path("kararlarim/<uuid:decision_id>/", report_views.decision_detail, name="decision_detail"),
    path("kararlarim/<uuid:decision_id>/itiraz/", appeal_views.submit_appeal, name="submit_appeal"),
    path("itirazlarim/<uuid:appeal_id>/", appeal_views.appeal_detail, name="appeal_detail"),
    path("bildirimler/", report_views.report_queue, name="report_queue"),
    path("bildirimler/<uuid:report_id>/", report_views.review_report, name="review_report"),
    path("itirazlar/", appeal_views.appeal_queue, name="appeal_queue"),
    path("itirazlar/<uuid:appeal_id>/", appeal_views.review_appeal, name="review_appeal"),
    path("bildirimler/<uuid:report_id>/gorsel/<int:asset_id>/", case_media.case_media, name="report_evidence_media"),
    path("itirazlar/<uuid:appeal_id>/gorsel/<int:asset_id>/", case_media.appeal_case_media, name="appeal_evidence_media"),
]
