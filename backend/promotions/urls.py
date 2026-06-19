from django.urls import path

from .views import (
    listing_promotion_packages,
    listing_promotion_request,
    my_promotions,
    promotion_admin_queue,
    promotion_approve,
    promotion_cancel,
    promotion_mark_paid,
    promotion_payment_page,
    promotion_receipt,
    promotion_reject,
)


app_name = "promotions"


urlpatterns = [
    path("my/", my_promotions, name="my_promotions"),
    path("payment/<int:pk>/", promotion_payment_page, name="payment"),
    path("receipt/<int:pk>/", promotion_receipt, name="receipt"),
    path("cancel/<int:pk>/", promotion_cancel, name="cancel"),
    path("admin/", promotion_admin_queue, name="admin_queue"),
    path("admin/<int:pk>/mark-paid/", promotion_mark_paid, name="mark_paid"),
    path("admin/<int:pk>/approve/", promotion_approve, name="approve"),
    path("admin/<int:pk>/reject/", promotion_reject, name="reject"),
    path("listings/<int:pk>/", listing_promotion_packages, name="listing_packages"),
    path(
        "listings/<int:pk>/packages/<int:package_id>/request/",
        listing_promotion_request,
        name="listing_package_request",
    ),
]
