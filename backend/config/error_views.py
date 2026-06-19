# CUSTOM_ERROR_VIEWS_V1
from django.shortcuts import render


def page_not_found(request, exception=None):
    return render(
        request,
        "404.html",
        {
            "page_title": "Page not found",
        },
        status=404,
    )


def permission_denied(request, exception=None):
    return render(
        request,
        "403.html",
        {
            "page_title": "Permission denied",
        },
        status=403,
    )


def server_error(request):
    return render(
        request,
        "500.html",
        {
            "page_title": "Server error",
        },
        status=500,
    )
