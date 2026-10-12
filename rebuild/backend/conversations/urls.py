from django.urls import path

from . import views

app_name = "conversations"
urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("ilan/<uuid:listing_id>/", views.start, name="start"),
    path("ilan/<uuid:listing_id>/iletisim/", views.contact, name="contact"),
    path("<uuid:conversation_id>/", views.detail, name="detail"),
    path("<uuid:conversation_id>/mesajlar/", views.history, name="history"),
    path("<uuid:conversation_id>/gonder/", views.send, name="send"),
    path("<uuid:conversation_id>/okundu/", views.mark_read, name="mark_read"),
    path("<uuid:conversation_id>/arsivle/", views.archive, name="archive"),
    path("<uuid:conversation_id>/arsivden-cikar/", views.unarchive, name="unarchive"),
    path("<uuid:conversation_id>/engelle/", views.block, name="block"),
    path("<uuid:conversation_id>/engeli-kaldir/", views.unblock, name="unblock"),
]
