from django.urls import path
from django.views.generic import RedirectView

from .views import (
    InboxView,
    ListingMessageCreateView,
    SentMessagesView,
    message_reply_view,
    message_thread_view,
)


app_name = "conversations"


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="conversations:inbox", permanent=False), name="messages_home"),
    path("inbox/", InboxView.as_view(), name="inbox"),
    path("sent/", SentMessagesView.as_view(), name="sent"),
    path("listings/<int:pk>/contact/", ListingMessageCreateView.as_view(), name="listing_contact"),
    path("<int:pk>/", message_thread_view, name="thread"),
    path("<int:pk>/reply/", message_reply_view, name="reply"),
]
