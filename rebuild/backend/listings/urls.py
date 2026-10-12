from django.urls import path
from . import views
from . import favorite_views

app_name = "listings"
urlpatterns = [
    path("", views.index, name="index"),
    path("favorilerim/", favorite_views.index, name="favorites"),
    path("favorilerim/<uuid:listing_id>/ekle/", favorite_views.add, name="favorite_add"),
    path("favorilerim/<uuid:listing_id>/kaldir/", favorite_views.remove, name="favorite_remove"),
    path("ilanlar/<uuid:listing_id>/", views.detail, name="detail"),
    path("ilanlar/<uuid:listing_id>/fotograflar/<int:revision_id>/<int:asset_id>/", views.public_image, name="public_image"),
    path("ilanlarim/", views.dashboard, name="dashboard"),
    path("ilan-ver/", views.create, name="create"),
    path("ilanlarim/<uuid:listing_id>/duzenleme-baslat/", views.restart, name="start_revision"),
    path("taslaklar/<int:revision_id>/duzenle/", views.edit, name="edit"),
    path("taslaklar/<int:revision_id>/onizleme/", views.preview, name="preview"),
    path("taslaklar/<int:revision_id>/gonder/", views.submit, name="submit"),
    path("taslaklar/<int:revision_id>/geri-cek/", views.withdraw, name="withdraw"),
    path("taslaklar/<int:revision_id>/fotograflar/ekle/", views.image_attach, name="image_attach"),
    path("taslaklar/<int:revision_id>/fotograflar/<int:asset_id>/kaldir/", views.image_remove, name="image_remove"),
    path("taslaklar/<int:revision_id>/fotograflar/<int:asset_id>/yeniden-dene/", views.image_retry, name="image_retry"),
    path("taslaklar/<int:revision_id>/fotograflar/durum/", views.photo_status, name="photo_status"),
]
