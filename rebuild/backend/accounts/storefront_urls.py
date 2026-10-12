from django.urls import path
from . import storefront_views as views

app_name = "storefronts"
urlpatterns = [
    path("vitrinim/", views.manage, name="manage"),
    path("vitrinim/olustur/", views.create, name="create"),
    path("vitrinim/<uuid:storefront_id>/duzenle/", views.change, {"action": "save"}, name="save"),
    path("vitrinim/<uuid:storefront_id>/yayinla/", views.change, {"action": "publish"}, name="publish"),
    path("vitrinim/<uuid:storefront_id>/kaldir/", views.change, {"action": "unpublish"}, name="unpublish"),
    path("vitrinim/<uuid:storefront_id>/onizleme/", views.preview, name="preview"),
    path("vitrin/<uuid:storefront_id>/", views.public, name="public"),
]
