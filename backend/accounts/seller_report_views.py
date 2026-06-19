# SELLER_REPORT_VIEWS_PAGINATION_FINAL_V1
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import UserReport


@staff_member_required
def seller_report_admin_list(request):
    selected_status = (request.GET.get("status") or "pending").strip()
    q = (request.GET.get("q") or "").strip()

    reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).order_by("-created_at")

    if selected_status:
        reports = reports.filter(status=selected_status)

    if q:
        reports = reports.filter(
            Q(reported_user__username__icontains=q)
            | Q(reported_user__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(source_listing__title__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        ).distinct()

    paginator = Paginator(reports, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "accounts/seller_report_admin_list.html",
        {
            "reports": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_status": selected_status,
            "selected_q": q,
            "status_choices": UserReport.Status.choices,
            "page_title": "Seller Reports",
        },
    )


@login_required
def my_seller_reports(request):
    selected_status = (request.GET.get("status") or "").strip()

    reports = UserReport.objects.select_related(
        "reported_user",
        "source_listing",
    ).filter(
        reporter=request.user,
    ).order_by("-created_at")

    if selected_status:
        reports = reports.filter(status=selected_status)

    paginator = Paginator(reports, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "accounts/my_seller_reports.html",
        {
            "reports": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_status": selected_status,
            "status_choices": UserReport.Status.choices,
            "page_title": "My Seller Reports",
        },
    )


# Backward-compatible names used by older URL configs.
user_report_queue = seller_report_admin_list
my_user_reports = my_seller_reports
