from django.urls import path
from . import views

app_name = "media"
urlpatterns = [
    path("<int:asset_id>/original/", views.original, name="original"),
    path("<int:asset_id>/preview/", views.derivative, name="derivative"),
    path("<int:asset_id>/status/", views.status, name="status"),
]
