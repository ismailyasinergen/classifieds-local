# HEALTH_CHECK_VIEW_V1
from django.db import connection
from django.http import JsonResponse


def healthz(request):
    checks = {
        "app": "ok",
        "database": "unknown",
    }

    status_code = 200

    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = "error"
        checks["database_error"] = exc.__class__.__name__
        status_code = 503

    return JsonResponse(
        {
            "status": "ok" if status_code == 200 else "error",
            "checks": checks,
        },
        status=status_code,
    )
