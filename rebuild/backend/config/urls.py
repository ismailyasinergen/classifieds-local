from django.contrib import admin
from allauth.account.decorators import secure_admin_login
from django.db import connection
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import include, path

from accounts import mfa_recovery
from notifications.views import inbox as notification_inbox


def home(request):
    return render(request, "home.html")


def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})


def admin_login(request):
    # Every admin login method enters allauth, including a signed-in POST.
    from accounts.mfa_middleware import safe_return_path
    from django.utils.http import urlencode
    next_path = safe_return_path(request, request.GET.get("next") or request.POST.get("next") or "/admin/")
    return HttpResponseRedirect("/accounts/login/?" + urlencode({"next": next_path}))


admin.site.login = secure_admin_login(admin.site.login)


urlpatterns = [
    path("one-cikar/", include("promotions.urls")),
    path("", include("accounts.storefront_urls")),
    path("", include("listings.urls")),
    path("kayitli-aramalarim/", include("notifications.urls")),
    path("bildirimlerim/", notification_inbox, name='notification_inbox'),
    path("inceleme/", include("moderation.urls")),
    path("mesajlar/", include("conversations.urls")),
    path("health/", health, name="health"),
    path("admin/login/", admin_login, name="admin_login"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    # Preserve stock URL names and paths while coordinating first-view writes.
    path("accounts/2fa/recovery-codes/", mfa_recovery.view_recovery_codes,
         name="mfa_view_recovery_codes"),
    path("accounts/2fa/recovery-codes/download/", mfa_recovery.download_recovery_codes,
         name="mfa_download_recovery_codes"),
    path("accounts/", include("allauth.urls")),
    path("private-media/", include("media.urls")),
]

from django.conf import settings
from django.urls import re_path
from django.contrib.staticfiles.views import serve
if settings.DEBUG:
    urlpatterns += [re_path(r"^static/(?P<path>.*)$", serve)]
