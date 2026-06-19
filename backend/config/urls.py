from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from config.health_views import healthz


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("messages/", include("conversations.urls")),
    path("promotions/", include("promotions.urls")),
    path("", include("pages.urls")),
    path("", include("listings.urls")),
    path("", include("categories.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# CUSTOM_ERROR_HANDLERS_V1
handler404 = "config.error_views.page_not_found"
handler403 = "config.error_views.permission_denied"
handler500 = "config.error_views.server_error"
