from django.urls import path
from . import views
app_name = "promotions"
urlpatterns = [
    path("<uuid:listing_id>/", views.choose, name="choose"),
    path("islem/<uuid:purchase_id>/", views.status, name="status"),
    path("islem/<uuid:purchase_id>/tamamla/", views.complete, name="complete"),
]