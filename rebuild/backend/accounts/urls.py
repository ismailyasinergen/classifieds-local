from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("security/", views.security, name="security"),
    path("security/verify-email/", views.verify_email, name="verify_email"),
]
