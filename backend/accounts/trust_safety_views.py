# TRUST_SAFETY_VIEWS_REFACTOR_PART_2_V1
import csv
import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from listings.models import ListingReport

from .models import ModerationAppeal, TrustSafetyEvent, UserReport


def _ts_label(value):
    if not value:
        return ""
    return str(value).replace("_", " ").replace("-", " ").capitalize()


def _ts_status_label(obj):
    method = getattr(obj, "get_status_display", None)
    if callable(method):
        try:
            return method()
        except Exception:
            pass
    return _ts_label(getattr(obj, "status", ""))


def _ts_action_label(obj, fallback):
    value = getattr(obj, "action_taken", "")
    if not value:
        return fallback

    method = getattr(obj, "get_action_taken_display", None)
    if callable(method):
        try:
            return method()
        except Exception:
            pass

    return _ts_label(value)


# ACTION_LOG_DATE_FILTER_SAFETY_V94
def _parse_action_log_date_filter(value):
    raw_value = (value or "").strip()
    if not raw_value:
        return None, "", False

    try:
        parsed_date = datetime.date.fromisoformat(raw_value)
    except ValueError:
        return None, raw_value, True

    return parsed_date, parsed_date.isoformat(), False


def _action_log_start_of_day(value):
    return timezone.make_aware(
        datetime.datetime.combine(value, datetime.time.min),
        timezone.get_current_timezone(),
    )


def _action_log_start_of_next_day(value):
    return _action_log_start_of_day(value + datetime.timedelta(days=1))


def _trust_safety_action_log_data(request):
    selected_type = (request.GET.get("type") or "all").strip()
    selected_action = (request.GET.get("action") or "").strip()
    selected_status = (request.GET.get("status") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()
    q = (request.GET.get("q") or "").strip()

    date_from, selected_date_from, invalid_date_from = _parse_action_log_date_filter(
        selected_date_from
    )
    date_to, selected_date_to, invalid_date_to = _parse_action_log_date_filter(
        selected_date_to
    )
    date_filter_error = ""

    if invalid_date_from or invalid_date_to:
        date_filter_error = "Enter valid action log dates in YYYY-MM-DD format."
    elif date_from and date_to and date_from > date_to:
        date_filter_error = "From date cannot be after To date."

    date_from_dt = None
    date_to_dt = None

    if not date_filter_error:
        if date_from:
            date_from_dt = _action_log_start_of_day(date_from)

        if date_to:
            date_to_dt = _action_log_start_of_next_day(date_to)

    listing_reports = (
        ListingReport.objects.select_related(
            "listing",
            "listing__owner",
            "reporter",
        )
        .exclude(status="pending")
        .annotate(action_date=Coalesce("reviewed_at", "created_at"))
    )

    seller_reports = (
        UserReport.objects.select_related(
            "reported_user",
            "reporter",
            "source_listing",
        )
        .exclude(status="pending")
        .annotate(action_date=Coalesce("action_taken_at", "created_at"))
    )

    appeal_actions = (
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing__owner",
            "reviewed_by",
        )
        .prefetch_related("attachments")
        .exclude(status="pending")
        .annotate(action_date=Coalesce("reviewed_at", "created_at"))
    )

    if date_filter_error:
        listing_reports = listing_reports.none()
        seller_reports = seller_reports.none()
        appeal_actions = appeal_actions.none()

    if selected_type == "listing":
        seller_reports = seller_reports.none()
        appeal_actions = appeal_actions.none()
    elif selected_type == "seller":
        listing_reports = listing_reports.none()
        appeal_actions = appeal_actions.none()
    elif selected_type == "appeal":
        listing_reports = listing_reports.none()
        seller_reports = seller_reports.none()

    if selected_status:
        listing_reports = listing_reports.filter(status=selected_status)
        seller_reports = seller_reports.filter(status=selected_status)
        appeal_actions = appeal_actions.filter(status=selected_status)

    if selected_action:
        listing_reports = listing_reports.filter(action_taken=selected_action)
        seller_reports = seller_reports.filter(action_taken=selected_action)

        appeal_status_by_action = {
            "appeal_approved": "approved",
            "appeal_rejected": "rejected",
        }

        if selected_action in appeal_status_by_action:
            appeal_actions = appeal_actions.filter(status=appeal_status_by_action[selected_action])
        else:
            appeal_actions = appeal_actions.none()

    if date_from_dt:
        listing_reports = listing_reports.filter(action_date__gte=date_from_dt)
        seller_reports = seller_reports.filter(action_date__gte=date_from_dt)
        appeal_actions = appeal_actions.filter(action_date__gte=date_from_dt)

    if date_to_dt:
        listing_reports = listing_reports.filter(action_date__lt=date_to_dt)
        seller_reports = seller_reports.filter(action_date__lt=date_to_dt)
        appeal_actions = appeal_actions.filter(action_date__lt=date_to_dt)

    if q:
        listing_reports = listing_reports.filter(
            Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        ).distinct()

        seller_reports = seller_reports.filter(
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

        appeal_actions = appeal_actions.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reviewed_by__username__icontains=q)
            | Q(reviewed_by__email__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    listing_reports = list(listing_reports.order_by("-action_date", "-created_at"))
    seller_reports = list(seller_reports.order_by("-action_date", "-created_at"))
    appeal_actions = list(appeal_actions.order_by("-action_date", "-created_at"))

    listing_action_values = set(
        ListingReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
    )
    seller_action_values = set(
        UserReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
    )

    action_values = set(value for value in listing_action_values | seller_action_values if value)
    action_values.update(["appeal_approved", "appeal_rejected"])

    action_choices = [(value, _ts_label(value)) for value in sorted(action_values)]

    status_choices = [
        ("reviewed", "Reviewed"),
        ("actioned", "Actioned"),
        ("dismissed", "Dismissed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    today = timezone.localdate()

    return {
        "listing_reports": listing_reports,
        "seller_reports": seller_reports,
        "appeal_actions": appeal_actions,
        "selected_type": selected_type,
        "selected_action": selected_action,
        "selected_status": selected_status,
        "selected_date_from": selected_date_from,
        "selected_date_to": selected_date_to,
        "date_filter_error": date_filter_error,
        "selected_q": q,
        "action_choices": action_choices,
        "status_choices": status_choices,
        "quick_today": today.isoformat(),
        "quick_last_7_days": (today - datetime.timedelta(days=6)).isoformat(),
        "quick_last_30_days": (today - datetime.timedelta(days=29)).isoformat(),
        "page_title": "Trust & Safety Action Log",
    }


@staff_member_required
def trust_safety_action_log(request):
    data = _trust_safety_action_log_data(request)

    action_rows = []

    for appeal in data["appeal_actions"]:
        date_value = appeal.reviewed_at or appeal.created_at
        action_rows.append({
            "kind": "appeal",
            "object": appeal,
            "title": f"Appeal #{appeal.pk}",
            "action_label": "Appeal approved" if appeal.status == "approved" else "Appeal rejected",
            "status_label": _ts_status_label(appeal),
            "date": date_value,
            "actor_line": (
                f"Appellant: {appeal.appellant.username} / {appeal.appellant.email}"
                if appeal.appellant else "Appellant unavailable"
            ),
            "subject_line": (
                f"Listing: {appeal.listing.title}"
                if appeal.listing else "No related listing"
            ),
            "public_note": appeal.decision_note or "",
            "admin_note": appeal.admin_note or "",
        })

    for report in data["listing_reports"]:
        date_value = report.reviewed_at or report.created_at
        action_rows.append({
            "kind": "listing",
            "object": report,
            "title": f"Listing report #{report.pk}",
            "action_label": _ts_action_label(report, "Listing report reviewed"),
            "status_label": _ts_status_label(report),
            "date": date_value,
            "actor_line": (
                f"Reporter: {report.reporter.username} / {report.reporter.email}"
                if report.reporter else "Reporter unavailable"
            ),
            "subject_line": (
                f"Listing: {report.listing.title} by {report.listing.owner.username} / {report.listing.owner.email}"
                if report.listing and report.listing.owner else "Listing unavailable"
            ),
            "public_note": report.reporter_note or "",
            "admin_note": report.admin_note or "",
        })

    for report in data["seller_reports"]:
        date_value = getattr(report, "action_taken_at", None) or report.created_at
        action_rows.append({
            "kind": "seller",
            "object": report,
            "title": f"Seller report #{report.pk}",
            "action_label": _ts_action_label(report, "Seller report reviewed"),
            "status_label": _ts_status_label(report),
            "date": date_value,
            "actor_line": (
                f"Reporter: {report.reporter.username} / {report.reporter.email}"
                if report.reporter else "Reporter unavailable"
            ),
            "subject_line": (
                f"Reported seller: {report.reported_user.username} / {report.reported_user.email}"
                if report.reported_user else "Reported seller unavailable"
            ),
            "public_note": report.reporter_note or "",
            "admin_note": report.admin_note or "",
        })

    fallback_date = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    action_rows.sort(key=lambda row: row["date"] or fallback_date, reverse=True)

    paginator = Paginator(action_rows, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    data.update({
        "action_rows": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "querystring_without_page": query_params.urlencode(),
        "total_action_rows": len(action_rows),
    })

    return render(request, "accounts/trust_safety_action_log.html", data)


@staff_member_required
def trust_safety_action_log_export(request):
    data = _trust_safety_action_log_data(request)

    rows = []

    for report in data["listing_reports"]:
        date_value = report.reviewed_at or report.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "listing_report",
            "record_id": report.pk,
            "status": _ts_status_label(report),
            "action": _ts_action_label(report, "Listing report reviewed"),
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": report.reporter.username if report.reporter else "",
            "reporter_or_appellant_email": report.reporter.email if report.reporter else "",
            "subject_username": report.listing.owner.username if report.listing and report.listing.owner else "",
            "subject_email": report.listing.owner.email if report.listing and report.listing.owner else "",
            "listing_title": report.listing.title if report.listing else "",
            "details_or_message": report.details or "",
            "public_note_or_decision_note": report.reporter_note or "",
            "internal_admin_note": report.admin_note or "",
        })

    for report in data["seller_reports"]:
        date_value = getattr(report, "action_taken_at", None) or report.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "seller_report",
            "record_id": report.pk,
            "status": _ts_status_label(report),
            "action": _ts_action_label(report, "Seller report reviewed"),
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": report.reporter.username if report.reporter else "",
            "reporter_or_appellant_email": report.reporter.email if report.reporter else "",
            "subject_username": report.reported_user.username if report.reported_user else "",
            "subject_email": report.reported_user.email if report.reported_user else "",
            "listing_title": report.source_listing.title if report.source_listing else "",
            "details_or_message": report.details or "",
            "public_note_or_decision_note": report.reporter_note or "",
            "internal_admin_note": report.admin_note or "",
        })

    for appeal in data["appeal_actions"]:
        date_value = appeal.reviewed_at or appeal.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "appeal",
            "record_id": appeal.pk,
            "status": _ts_status_label(appeal),
            "action": "Appeal approved" if appeal.status == "approved" else "Appeal rejected",
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": appeal.appellant.username if appeal.appellant else "",
            "reporter_or_appellant_email": appeal.appellant.email if appeal.appellant else "",
            "subject_username": appeal.listing.owner.username if appeal.listing and appeal.listing.owner else "",
            "subject_email": appeal.listing.owner.email if appeal.listing and appeal.listing.owner else "",
            "listing_title": appeal.listing.title if appeal.listing else "",
            "details_or_message": appeal.message or "",
            "public_note_or_decision_note": appeal.decision_note or "",
            "internal_admin_note": appeal.admin_note or "",
        })

    rows.sort(key=lambda row: row["sort_date"] or "", reverse=True)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="trust_safety_action_log.csv"'

    writer = csv.DictWriter(
        response,
        fieldnames=[
            "record_type",
            "record_id",
            "status",
            "action",
            "date",
            "reporter_or_appellant_username",
            "reporter_or_appellant_email",
            "subject_username",
            "subject_email",
            "listing_title",
            "details_or_message",
            "public_note_or_decision_note",
            "internal_admin_note",
        ],
    )
    writer.writeheader()

    for row in rows:
        row.pop("sort_date", None)
        writer.writerow(row)

    return response


def _event_log_filtered_queryset(request):
    q = (request.GET.get("q") or "").strip()
    event_type = (request.GET.get("event_type") or "").strip()
    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()

    events = TrustSafetyEvent.objects.select_related(
        "actor",
        "target_user",
        "listing",
        "listing_report",
        "user_report",
        "appeal",
    ).order_by("-created_at")

    if event_type:
        events = events.filter(event_type=event_type)

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(date_from_raw)
    date_to = parse_date(date_to_raw)

    if date_from:
        events = events.filter(
            created_at__gte=timezone.make_aware(
                datetime.datetime.combine(date_from, datetime.time.min)
            )
        )

    if date_to:
        events = events.filter(
            created_at__lt=timezone.make_aware(
                datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min)
            )
        )

    if q:
        events = events.filter(
            Q(title__icontains=q)
            | Q(public_note__icontains=q)
            | Q(internal_note__icontains=q)
            | Q(actor__username__icontains=q)
            | Q(actor__email__icontains=q)
            | Q(target_user__username__icontains=q)
            | Q(target_user__email__icontains=q)
            | Q(listing__title__icontains=q)
        ).distinct()

    return events, {
        "q": q,
        "event_type": event_type,
        "date_from": date_from_raw,
        "date_to": date_to_raw,
    }


@staff_member_required
def trust_safety_event_log(request):
    events, filters = _event_log_filtered_queryset(request)

    paginator = Paginator(events, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()

    return render(
        request,
        "accounts/trust_safety_event_log.html",
        {
            "events": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_q": filters["q"],
            "selected_event_type": filters["event_type"],
            "selected_date_from": filters["date_from"],
            "selected_date_to": filters["date_to"],
            "event_type_choices": TrustSafetyEvent.EventType.choices,
            "quick_today": today.isoformat(),
            "quick_last_7_days": (today - datetime.timedelta(days=6)).isoformat(),
            "quick_last_30_days": (today - datetime.timedelta(days=29)).isoformat(),
            "page_title": "Trust & Safety Events",
        },
    )


@staff_member_required
def trust_safety_event_log_export(request):
    events, _filters = _event_log_filtered_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="trust_safety_events.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "event_id",
        "event_type",
        "created_at",
        "title",
        "actor_username",
        "actor_email",
        "target_username",
        "target_email",
        "listing_title",
        "listing_report_id",
        "seller_report_id",
        "appeal_id",
        "public_note",
        "internal_note",
    ])

    for event in events:
        writer.writerow([
            event.pk,
            event.get_event_type_display(),
            event.created_at.isoformat() if event.created_at else "",
            event.title,
            event.actor.username if event.actor else "",
            event.actor.email if event.actor else "",
            event.target_user.username if event.target_user else "",
            event.target_user.email if event.target_user else "",
            event.listing.title if event.listing else "",
            event.listing_report_id or "",
            event.user_report_id or "",
            event.appeal_id or "",
            event.public_note,
            event.internal_note,
        ])

    return response
