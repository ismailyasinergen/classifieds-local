# APPEAL_VIEWS_REFACTOR_PART_3_FINAL_V1
import csv
import datetime
import hashlib
import io
import zipfile
from pathlib import Path

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from config.csv_safety_v323 import write_csv_row_v323
from listings.models import Listing

from .models import (
    ModerationAppeal,
    ModerationAppealAttachment,
    ModerationNotice,
    UserProfile,
)


def _record_event_safely(**kwargs):
    try:
        from .models import TrustSafetyEvent
        from .services.trust_safety_events import record_trust_safety_event

        return record_trust_safety_event(**kwargs)
    except Exception:
        return None


def _uploaded_file_hash(uploaded):
    digest = hashlib.sha256()

    try:
        uploaded.seek(0)
    except Exception:
        pass

    for chunk in uploaded.chunks():
        digest.update(chunk)

    try:
        uploaded.seek(0)
    except Exception:
        pass

    return digest.hexdigest()


def _safe_filename(name):
    name = Path(name or "evidence").name
    name = name.replace("/", "_").replace("\\", "_")
    return name or "evidence"


def _moderation_appeals_filtered_queryset(request, include_status=True):
    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    evidence_filter = (request.GET.get("evidence") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(selected_date_from)
    date_to = parse_date(selected_date_to)

    qs = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
    ).prefetch_related("attachments")

    if q:
        qs = qs.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    if date_from:
        qs = qs.filter(
            created_at__gte=timezone.make_aware(
                datetime.datetime.combine(date_from, datetime.time.min)
            )
        )

    if date_to:
        qs = qs.filter(
            created_at__lt=timezone.make_aware(
                datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min)
            )
        )

    if evidence_filter == "has_evidence":
        qs = qs.filter(attachments__isnull=False).distinct()
    elif evidence_filter == "no_evidence":
        qs = qs.filter(attachments__isnull=True)

    if include_status and status:
        qs = qs.filter(status=status)

    return qs, {
        "status": status,
        "q": q,
        "evidence": evidence_filter,
        "date_from": selected_date_from,
        "date_to": selected_date_to,
    }


@staff_member_required
def moderation_appeal_queue(request):
    filtered_qs, filters = _moderation_appeals_filtered_queryset(request, include_status=True)
    count_qs, _ = _moderation_appeals_filtered_queryset(request, include_status=False)

    all_matching_appeals = list(count_qs)

    total_appeals = len(all_matching_appeals)
    pending_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.PENDING)
    approved_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.APPROVED)
    rejected_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.REJECTED)

    total_evidence_files = 0
    total_evidence_size = 0

    for appeal in all_matching_appeals:
        attachments = list(appeal.attachments.all())
        total_evidence_files += len(attachments)
        total_evidence_size += sum(item.size or 0 for item in attachments)

    paginator = Paginator(filtered_qs.order_by("-created_at"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    appeals = list(page_obj.object_list)

    for appeal in appeals:
        attachments = list(appeal.attachments.all())
        evidence_total_size = sum(item.size or 0 for item in attachments)
        appeal.evidence_file_count = len(attachments)
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_status": filters["status"],
            "selected_q": filters["q"],
            "selected_evidence": filters["evidence"],
            "selected_date_from": filters["date_from"],
            "selected_date_to": filters["date_to"],
            "status_choices": ModerationAppeal.Status.choices,
            "evidence_choices": [
                ("", "All evidence statuses"),
                ("has_evidence", "Has evidence"),
                ("no_evidence", "No evidence"),
            ],
            "total_appeals": total_appeals,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "total_evidence_files": total_evidence_files,
            "total_evidence_mb": round(total_evidence_size / 1024 / 1024, 2),
            "quick_today": today.isoformat(),
            "quick_last_7_days": (today - datetime.timedelta(days=6)).isoformat(),
            "quick_last_30_days": (today - datetime.timedelta(days=29)).isoformat(),
            "page_title": "Moderation Appeals",
        },
    )


@login_required
def my_moderation_appeals(request):
    appeals = (
        ModerationAppeal.objects.select_related(
            "moderation_notice",
            "listing",
            "reviewed_by",
        )
        .prefetch_related("attachments")
        .filter(appellant=request.user)
        .order_by("-created_at")
    )

    return render(
        request,
        "accounts/my_moderation_appeals.html",
        {
            "appeals": appeals,
            "page_title": "My Appeals",
        },
    )


@login_required
def moderation_appeal_detail(request, pk):
    appeal = (
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "reviewed_by",
        )
        .prefetch_related("attachments")
        .filter(pk=pk)
        .first()
    )

    if not appeal:
        messages.error(request, "That appeal does not exist.")
        return redirect("accounts:my_moderation_appeals")

    if request.user.is_staff:
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if appeal.appellant_id != request.user.id:
        messages.error(request, "That appeal does not belong to your account.")
        return redirect("accounts:my_moderation_appeals")

    evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())

    return render(
        request,
        "accounts/moderation_appeal_detail.html",
        {
            "appeal": appeal,
            "evidence_file_count": appeal.attachments.count(),
            "evidence_total_mb": round(evidence_total_size / 1024 / 1024, 2),
            "page_title": "Appeal Detail",
        },
    )


@login_required
def moderation_appeal_create(request, notice_pk):
    notice = (
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        )
        .filter(pk=notice_pk, recipient=request.user)
        .first()
    )

    if not notice:
        messages.error(
            request,
            "That moderation notice was not found for your account. Please use the current Notices page.",
        )
        return redirect("accounts:moderation_notices")

    existing_appeal = (
        ModerationAppeal.objects.filter(
            appellant=request.user,
            moderation_notice=notice,
        )
        .order_by("-created_at")
        .first()
    )

    if existing_appeal:
        messages.info(request, "You already submitted an appeal for this notice.")
        return redirect("accounts:moderation_appeal_detail", pk=existing_appeal.pk)

    if notice.notice_type not in [
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    ]:
        messages.error(request, "This notice is an update, not an appealable moderation action.")
        return redirect("accounts:moderation_notices")

    title_lower = (notice.title or "").lower()
    body_lower = (notice.body or "").lower()
    non_appealable_words = ["lifted", "restored", "appeal was approved", "appeal was rejected"]

    if any(word in title_lower or word in body_lower for word in non_appealable_words):
        messages.error(request, "This notice does not need an appeal because it is not an active restriction.")
        return redirect("accounts:moderation_notices")

    appeal_type = (
        ModerationAppeal.AppealType.LISTING_ACTION
        if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION
        else ModerationAppeal.AppealType.SELLER_ACTION
    )

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        files = request.FILES.getlist("attachments")

        if not message:
            messages.error(request, "Please write an appeal message before submitting.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        max_files = 15
        max_total_size = 200 * 1024 * 1024

        if len(files) > max_files:
            messages.error(request, "You can upload up to 15 files per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        total_size = sum(uploaded.size or 0 for uploaded in files)

        if total_size > max_total_size:
            messages.error(request, "Total upload size is too large. Maximum total size is 200 MB per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_pdf_exts = {".pdf"}
        allowed_video_exts = {".mp4"}

        allowed_image_types = {"image/jpeg", "image/png", "image/webp"}
        allowed_pdf_types = {"application/pdf"}
        allowed_video_types = {"video/mp4"}

        validation_errors = []
        seen_hashes = {}

        for uploaded in files:
            ext = Path(uploaded.name).suffix.lower()
            content_type = (uploaded.content_type or "").lower()

            is_valid_image = ext in allowed_image_exts and content_type in allowed_image_types
            is_valid_pdf = ext in allowed_pdf_exts and content_type in allowed_pdf_types
            is_valid_video = ext in allowed_video_exts and content_type in allowed_video_types

            if not (is_valid_image or is_valid_pdf or is_valid_video):
                validation_errors.append(
                    f"{uploaded.name}: invalid type. Allowed: .jpg, .jpeg, .png, .webp, .pdf, .mp4 only."
                )
                continue

            file_hash = _uploaded_file_hash(uploaded)

            if file_hash in seen_hashes:
                validation_errors.append(
                    f"{uploaded.name}: duplicate file. It matches {seen_hashes[file_hash]}."
                )
            else:
                seen_hashes[file_hash] = uploaded.name

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            status=ModerationAppeal.Status.PENDING,
            message=message,
        )

        for uploaded in files:
            ModerationAppealAttachment.objects.create(
                appeal=appeal,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
                size=uploaded.size or 0,
            )

        User = get_user_model()
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        for staff_user in staff_users:
            ModerationNotice.objects.create(
                recipient=staff_user,
                title="New moderation appeal submitted",
                body=(
                    f"{request.user.username} submitted appeal #{appeal.pk}. "
                    "Review it from the Trust & Safety appeals queue."
                ),
                notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                listing=appeal.listing,
                listing_report=appeal.listing_report,
                user_report=appeal.user_report,
            )

        _record_event_safely(
            event_type="appeal_submitted",
            title=f"Appeal #{appeal.pk} submitted",
            actor=request.user,
            target_user=request.user,
            listing=appeal.listing,
            listing_report=appeal.listing_report,
            user_report=appeal.user_report,
            appeal=appeal,
            public_note=appeal.message,
            metadata={"appeal_status": appeal.status},
        )

        messages.success(
            request,
            "Your appeal was submitted for admin review. No restriction has been changed automatically.",
        )
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "max_upload_files": 15,
            "max_total_upload_mb": 200,
            "page_title": "Submit Appeal",
        },
    )


@staff_member_required
def moderation_appeal_admin_detail(request, pk):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "user_report__reported_user",
            "reviewed_by",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    seller_to_lift = None

    if appeal.user_report and appeal.user_report.reported_user:
        seller_to_lift = appeal.user_report.reported_user
    elif appeal.appeal_type == ModerationAppeal.AppealType.SELLER_ACTION:
        seller_to_lift = appeal.appellant

    seller_profile = None
    seller_is_suspended = False

    if seller_to_lift:
        seller_profile = UserProfile.objects.filter(user=seller_to_lift).first()
        seller_is_suspended = bool(seller_profile and seller_profile.is_seller_suspended)

    can_restore_listing = (
        appeal.status == ModerationAppeal.Status.APPROVED
        and appeal.listing
        and appeal.listing.status == Listing.Status.SUSPENDED
        and not appeal.listing.suspended_due_to_seller
    )

    listing_restore_blocked_by_seller_suspension = (
        appeal.status == ModerationAppeal.Status.APPROVED
        and appeal.listing
        and appeal.listing.status == Listing.Status.SUSPENDED
        and appeal.listing.suspended_due_to_seller
    )

    evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())

    return render(
        request,
        "accounts/moderation_appeal_admin_detail.html",
        {
            "appeal": appeal,
            "seller_to_lift": seller_to_lift,
            "seller_profile": seller_profile,
            "seller_is_suspended": seller_is_suspended,
            "can_restore_listing": can_restore_listing,
            "listing_restore_blocked_by_seller_suspension": listing_restore_blocked_by_seller_suspension,
            "evidence_file_count": appeal.attachments.count(),
            "evidence_total_mb": round(evidence_total_size / 1024 / 1024, 2),
            "page_title": "Appeal Admin Detail",
        },
    )


@staff_member_required
@require_POST
def moderation_appeal_decide(request, pk, decision):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing_report",
            "user_report",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    if appeal.status != ModerationAppeal.Status.PENDING:
        messages.warning(request, "This appeal has already been decided.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    evidence_reviewed = request.POST.get("evidence_reviewed") == "yes"
    decision_note = (request.POST.get("decision_note") or "").strip()
    admin_note = (request.POST.get("admin_note") or "").strip()

    if not evidence_reviewed:
        messages.error(request, "You must confirm that you reviewed the appeal evidence before deciding.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if not decision_note:
        messages.error(request, "Decision note is required and will be shown to the user.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if decision == "approve":
        appeal.status = ModerationAppeal.Status.APPROVED
        notice_title = "Your appeal was approved"
        event_type = "appeal_approved"
    elif decision == "reject":
        appeal.status = ModerationAppeal.Status.REJECTED
        notice_title = "Your appeal was rejected"
        event_type = "appeal_rejected"
    else:
        messages.error(request, "Invalid appeal decision.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    appeal.decision_note = decision_note
    appeal.admin_note = admin_note or appeal.admin_note or ""
    appeal.reviewed_by = request.user
    appeal.reviewed_at = timezone.now()
    appeal.save(
        update_fields=[
            "status",
            "decision_note",
            "admin_note",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    ModerationNotice.objects.create(
        recipient=appeal.appellant,
        title=notice_title,
        body=decision_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
    )

    _record_event_safely(
        event_type=event_type,
        title=f"Appeal #{appeal.pk} {appeal.status}",
        actor=request.user,
        target_user=appeal.appellant,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
        appeal=appeal,
        public_note=appeal.decision_note,
        internal_note=appeal.admin_note,
        metadata={"appeal_status": appeal.status},
    )

    messages.success(
        request,
        "Appeal decision saved and user notified. No listing or seller restriction was changed automatically.",
    )
    return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)


@login_required
@require_POST
def moderation_appeal_attachment_delete(request, pk):
    messages.error(request, "Evidence files are locked after appeal submission and cannot be deleted.")
    return redirect("accounts:my_moderation_appeals")


@staff_member_required
def moderation_appeal_export_csv(request):
    appeals, _filters = _moderation_appeals_filtered_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="moderation_appeals.csv"'

    writer = csv.writer(response)

    write_csv_row_v323(writer, [
        "appeal_id",
        "status",
        "appeal_type",
        "created_at",
        "appellant_username",
        "appellant_email",
        "listing_title",
        "evidence_file_count",
        "evidence_total_mb",
        "evidence_filenames",
        "message",
        "decision_note",
        "internal_admin_note",
        "reviewed_by",
        "reviewed_at",
    ])

    for appeal in appeals.order_by("-created_at"):
        attachments = list(appeal.attachments.all())
        total_size = sum(item.size or 0 for item in attachments)
        total_mb = round(total_size / 1024 / 1024, 2)
        filenames = "; ".join(item.original_name for item in attachments)

        write_csv_row_v323(writer, [
            appeal.pk,
            appeal.get_status_display(),
            appeal.get_appeal_type_display(),
            appeal.created_at.isoformat() if appeal.created_at else "",
            appeal.appellant.username if appeal.appellant else "",
            appeal.appellant.email if appeal.appellant else "",
            appeal.listing.title if appeal.listing else "",
            len(attachments),
            total_mb,
            filenames,
            appeal.message or "",
            appeal.decision_note or "",
            appeal.admin_note or "",
            appeal.reviewed_by.username if appeal.reviewed_by else "",
            appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
        ])

    return response


@staff_member_required
def moderation_appeal_evidence_zip(request, pk):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "reviewed_by",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        readme = [
            f"Appeal ID: {appeal.pk}",
            f"Status: {appeal.get_status_display()}",
            f"Type: {appeal.get_appeal_type_display()}",
            f"Appellant: {appeal.appellant.username} / {appeal.appellant.email}",
            f"Created: {appeal.created_at}",
            "",
            "Appeal message:",
            appeal.message or "",
            "",
            "Decision note:",
            appeal.decision_note or "",
            "",
            "Internal admin note:",
            appeal.admin_note or "",
            "",
        ]

        if appeal.listing:
            readme.extend([
                f"Related listing: {appeal.listing.title}",
                f"Listing status: {appeal.listing.get_status_display()}",
                "",
            ])

        archive.writestr("APPEAL_SUMMARY.txt", "\n".join(readme))

        attachments = list(appeal.attachments.all())

        if not attachments:
            archive.writestr("NO_EVIDENCE_FILES.txt", "No evidence files were uploaded with this appeal.")
        else:
            used_names = set()

            for index, attachment in enumerate(attachments, start=1):
                original_name = _safe_filename(attachment.original_name or attachment.file.name)
                zip_name = f"{index:02d}_{original_name}"

                counter = 2
                while zip_name in used_names:
                    stem = Path(original_name).stem
                    suffix = Path(original_name).suffix
                    zip_name = f"{index:02d}_{stem}_{counter}{suffix}"
                    counter += 1

                used_names.add(zip_name)

                attachment.file.open("rb")
                try:
                    archive.writestr(zip_name, attachment.file.read())
                finally:
                    attachment.file.close()

    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="appeal_{appeal.pk}_evidence.zip"'
    return response


@staff_member_required
def moderation_appeal_bulk_evidence_zip(request):
    appeals, _filters = _moderation_appeals_filtered_queryset(request)
    appeals = list(appeals.order_by("-created_at"))

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        summary_buffer = io.StringIO()
        writer = csv.writer(summary_buffer)

        write_csv_row_v323(writer, [
            "appeal_id",
            "status",
            "appeal_type",
            "created_at",
            "appellant_username",
            "appellant_email",
            "listing_title",
            "evidence_file_count",
            "evidence_total_mb",
            "decision_note",
            "reviewed_by",
            "reviewed_at",
        ])

        if not appeals:
            archive.writestr("NO_MATCHING_APPEALS.txt", "No appeals matched this filter.")
        else:
            for appeal in appeals:
                attachments = list(appeal.attachments.all())
                total_size = sum(item.size or 0 for item in attachments)
                total_mb = round(total_size / 1024 / 1024, 2)

                write_csv_row_v323(writer, [
                    appeal.pk,
                    appeal.get_status_display(),
                    appeal.get_appeal_type_display(),
                    appeal.created_at.isoformat() if appeal.created_at else "",
                    appeal.appellant.username if appeal.appellant else "",
                    appeal.appellant.email if appeal.appellant else "",
                    appeal.listing.title if appeal.listing else "",
                    len(attachments),
                    total_mb,
                    appeal.decision_note or "",
                    appeal.reviewed_by.username if appeal.reviewed_by else "",
                    appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
                ])

                folder = f"appeal_{appeal.pk:04d}"

                archive.writestr(
                    f"{folder}/APPEAL_SUMMARY.txt",
                    "\n".join([
                        f"Appeal ID: {appeal.pk}",
                        f"Status: {appeal.get_status_display()}",
                        f"Type: {appeal.get_appeal_type_display()}",
                        f"Appellant: {appeal.appellant.username if appeal.appellant else ''} / {appeal.appellant.email if appeal.appellant else ''}",
                        f"Created: {appeal.created_at}",
                        "",
                        "Appeal message:",
                        appeal.message or "",
                        "",
                        "Decision note:",
                        appeal.decision_note or "",
                        "",
                        "Internal admin note:",
                        appeal.admin_note or "",
                    ]),
                )

                if not attachments:
                    archive.writestr(f"{folder}/NO_EVIDENCE_FILES.txt", "No evidence files were uploaded with this appeal.")
                else:
                    used_names = set()

                    for index, attachment in enumerate(attachments, start=1):
                        original_name = _safe_filename(attachment.original_name or attachment.file.name)
                        zip_name = f"{folder}/{index:02d}_{original_name}"

                        counter = 2
                        while zip_name in used_names:
                            stem = Path(original_name).stem
                            suffix = Path(original_name).suffix
                            zip_name = f"{folder}/{index:02d}_{stem}_{counter}{suffix}"
                            counter += 1

                        used_names.add(zip_name)

                        attachment.file.open("rb")
                        try:
                            archive.writestr(zip_name, attachment.file.read())
                        finally:
                            attachment.file.close()

        archive.writestr("ALL_APPEALS_SUMMARY.csv", summary_buffer.getvalue())

    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="filtered_appeals_evidence.zip"'
    return response


# PRIVATE_APPEAL_EVIDENCE_DOWNLOADS_V1
@login_required
def moderation_appeal_attachment_download(request, pk):
    from django.http import FileResponse, Http404

    attachment = get_object_or_404(
        ModerationAppealAttachment.objects.select_related(
            "appeal",
            "appeal__appellant",
        ),
        pk=pk,
    )

    if not request.user.is_staff and attachment.appeal.appellant_id != request.user.id:
        raise Http404("Evidence file not found.")

    if not attachment.file:
        raise Http404("Evidence file not found.")

    try:
        file_handle = attachment.file.open("rb")
    except FileNotFoundError:
        raise Http404("Evidence file not found.")

    filename = _safe_filename(attachment.original_name or attachment.file.name)
    as_attachment = request.GET.get("download") == "1"

    response = FileResponse(
        file_handle,
        content_type=attachment.content_type or "application/octet-stream",
        as_attachment=as_attachment,
        filename=filename,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


# APPEAL_REOPEN_FLOW_V1
@staff_member_required
@require_POST
def moderation_appeal_reopen(request, pk):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing_report",
            "user_report",
            "reviewed_by",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    if appeal.status == ModerationAppeal.Status.PENDING:
        messages.info(request, "This appeal is already pending.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    reopen_note = (request.POST.get("reopen_note") or "").strip()

    if not reopen_note:
        messages.error(request, "A reopen note is required.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    previous_status = appeal.status

    appeal.status = ModerationAppeal.Status.PENDING
    appeal.admin_note = (
        (appeal.admin_note or "").rstrip()
        + "\n\n"
        + f"Appeal reopened by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}: {reopen_note}"
    ).strip()
    appeal.decision_note = appeal.decision_note or ""
    appeal.reviewed_by = None
    appeal.reviewed_at = None
    appeal.save(
        update_fields=[
            "status",
            "admin_note",
            "decision_note",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    ModerationNotice.objects.create(
        recipient=appeal.appellant,
        title="Your appeal was reopened",
        body=(
            "Your moderation appeal has been reopened for another Trust & Safety review. "
            "Your uploaded evidence remains locked and unchanged. "
            f"Admin note: {reopen_note}"
        ),
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
    )

    _record_event_safely(
        event_type="appeal_reopened",
        title=f"Appeal #{appeal.pk} reopened",
        actor=request.user,
        target_user=appeal.appellant,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
        appeal=appeal,
        public_note="Appeal reopened for another Trust & Safety review.",
        internal_note=reopen_note,
        metadata={
            "previous_status": previous_status,
            "new_status": appeal.status,
        },
    )

    messages.success(
        request,
        "Appeal reopened. Status is pending again. No restriction or listing status was changed.",
    )
    return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)



# APPEAL_FINAL_DECISION_EXTRA_EVIDENCE_FLOW_V1
def _validate_extra_evidence_files(appeal, files):
    from pathlib import Path

    max_files = 15
    max_total_size = 200 * 1024 * 1024

    errors = []

    existing_attachments = list(appeal.attachments.all())
    existing_count = len(existing_attachments)
    existing_total_size = sum(item.size or 0 for item in existing_attachments)

    if not files:
        errors.append("Please select at least one evidence file.")
        return errors

    if existing_count + len(files) > max_files:
        errors.append("This appeal can have up to 15 total evidence files.")
        return errors

    uploaded_total_size = sum(uploaded.size or 0 for uploaded in files)

    if existing_total_size + uploaded_total_size > max_total_size:
        errors.append("Total evidence size cannot exceed 200 MB.")
        return errors

    allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    allowed_pdf_exts = {".pdf"}
    allowed_video_exts = {".mp4"}

    allowed_image_types = {"image/jpeg", "image/png", "image/webp"}
    allowed_pdf_types = {"application/pdf"}
    allowed_video_types = {"video/mp4"}

    seen_hashes = {}

    for attachment in existing_attachments:
        if not attachment.file:
            continue

        try:
            attachment.file.open("rb")
            digest = hashlib.sha256()
            for chunk in iter(lambda: attachment.file.read(1024 * 1024), b""):
                digest.update(chunk)
            seen_hashes[digest.hexdigest()] = attachment.original_name or attachment.file.name
        except Exception:
            pass
        finally:
            try:
                attachment.file.close()
            except Exception:
                pass

    for uploaded in files:
        ext = Path(uploaded.name).suffix.lower()
        content_type = (uploaded.content_type or "").lower()

        is_valid_image = ext in allowed_image_exts and content_type in allowed_image_types
        is_valid_pdf = ext in allowed_pdf_exts and content_type in allowed_pdf_types
        is_valid_video = ext in allowed_video_exts and content_type in allowed_video_types

        if not (is_valid_image or is_valid_pdf or is_valid_video):
            errors.append(
                f"{uploaded.name}: invalid type. Allowed: .jpg, .jpeg, .png, .webp, .pdf, .mp4 only."
            )
            continue

        file_hash = _uploaded_file_hash(uploaded)

        if file_hash in seen_hashes:
            errors.append(f"{uploaded.name}: duplicate file. It matches {seen_hashes[file_hash]}.")
        else:
            seen_hashes[file_hash] = uploaded.name

    return errors


@staff_member_required
@require_POST
def moderation_appeal_request_extra_evidence(request, pk):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing_report",
            "user_report",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    if appeal.status != ModerationAppeal.Status.PENDING:
        messages.error(request, "Extra evidence can only be requested before a final decision.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    note = (request.POST.get("extra_evidence_request_note") or "").strip()

    if not note:
        messages.error(request, "Please write what extra evidence is needed.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    appeal.extra_evidence_requested_at = timezone.now()
    appeal.extra_evidence_request_note = note
    appeal.extra_evidence_requested_by = request.user
    appeal.extra_evidence_fulfilled_at = None
    appeal.save(
        update_fields=[
            "extra_evidence_requested_at",
            "extra_evidence_request_note",
            "extra_evidence_requested_by",
            "extra_evidence_fulfilled_at",
        ]
    )

    ModerationNotice.objects.create(
        recipient=appeal.appellant,
        title="Extra evidence requested for your appeal",
        body=(
            "Trust & Safety needs more evidence before making a final decision. "
            f"Request: {note}"
        ),
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
    )

    _record_event_safely(
        event_type="notice_sent",
        title=f"Extra evidence requested for appeal #{appeal.pk}",
        actor=request.user,
        target_user=appeal.appellant,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
        appeal=appeal,
        public_note="Extra evidence requested before final decision.",
        internal_note=note,
        metadata={"appeal_status": appeal.status},
    )

    messages.success(request, "Extra evidence request sent to the seller.")
    return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)


@login_required
@require_POST
def moderation_appeal_add_extra_evidence(request, pk):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing_report",
            "user_report",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    if appeal.appellant_id != request.user.id:
        messages.error(request, "That appeal does not belong to your account.")
        return redirect("accounts:my_moderation_appeals")

    if appeal.status != ModerationAppeal.Status.PENDING:
        messages.error(request, "This appeal already has a final decision, so no more evidence can be added.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    if not appeal.extra_evidence_requested_at or appeal.extra_evidence_fulfilled_at:
        messages.error(request, "You can only add evidence when Trust & Safety has requested extra evidence.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    files = request.FILES.getlist("attachments")

    validation_errors = _validate_extra_evidence_files(appeal, files)

    if validation_errors:
        for error in validation_errors:
            messages.error(request, error)
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    for uploaded in files:
        ModerationAppealAttachment.objects.create(
            appeal=appeal,
            file=uploaded,
            original_name=uploaded.name,
            content_type=uploaded.content_type or "",
            size=uploaded.size or 0,
        )

    appeal.extra_evidence_fulfilled_at = timezone.now()
    appeal.save(update_fields=["extra_evidence_fulfilled_at"])

    User = get_user_model()
    staff_users = User.objects.filter(is_staff=True, is_active=True)

    for staff_user in staff_users:
        ModerationNotice.objects.create(
            recipient=staff_user,
            title="Extra appeal evidence uploaded",
            body=f"{request.user.username} uploaded extra evidence for appeal #{appeal.pk}.",
            notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
            listing=appeal.listing,
            listing_report=appeal.listing_report,
            user_report=appeal.user_report,
        )

    _record_event_safely(
        event_type="appeal_submitted",
        title=f"Extra evidence added to appeal #{appeal.pk}",
        actor=request.user,
        target_user=request.user,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
        appeal=appeal,
        public_note="Extra evidence uploaded after Trust & Safety request.",
        metadata={"extra_file_count": len(files), "appeal_status": appeal.status},
    )

    messages.success(request, "Extra evidence uploaded. Trust & Safety can now make a final decision.")
    return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)


# APPEAL_EXTRA_EVIDENCE_QUEUE_FILTER_V1
def _appeal_extra_evidence_state(appeal):
    if appeal.status != ModerationAppeal.Status.PENDING:
        return "final_decision"

    if getattr(appeal, "extra_evidence_requested_at", None):
        if getattr(appeal, "extra_evidence_fulfilled_at", None):
            return "fulfilled"
        return "waiting"

    return "not_requested"


def _appeal_extra_evidence_label(state):
    labels = {
        "not_requested": "No extra evidence requested",
        "waiting": "Waiting for seller",
        "fulfilled": "Extra evidence uploaded",
        "final_decision": "Final decision locked",
    }
    return labels.get(state, "Unknown")


def _moderation_appeals_filtered_queryset(request, include_status=True):
    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    evidence_filter = (request.GET.get("evidence") or "").strip()
    extra_evidence_filter = (request.GET.get("extra_evidence") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(selected_date_from)
    date_to = parse_date(selected_date_to)

    qs = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
        "extra_evidence_requested_by",
    ).prefetch_related("attachments")

    if q:
        qs = qs.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(extra_evidence_request_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    if date_from:
        qs = qs.filter(
            created_at__gte=timezone.make_aware(
                datetime.datetime.combine(date_from, datetime.time.min)
            )
        )

    if date_to:
        qs = qs.filter(
            created_at__lt=timezone.make_aware(
                datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min)
            )
        )

    if evidence_filter == "has_evidence":
        qs = qs.filter(attachments__isnull=False).distinct()
    elif evidence_filter == "no_evidence":
        qs = qs.filter(attachments__isnull=True)

    if extra_evidence_filter == "not_requested":
        qs = qs.filter(
            status=ModerationAppeal.Status.PENDING,
            extra_evidence_requested_at__isnull=True,
        )
    elif extra_evidence_filter == "waiting":
        qs = qs.filter(
            status=ModerationAppeal.Status.PENDING,
            extra_evidence_requested_at__isnull=False,
            extra_evidence_fulfilled_at__isnull=True,
        )
    elif extra_evidence_filter == "fulfilled":
        qs = qs.filter(
            status=ModerationAppeal.Status.PENDING,
            extra_evidence_requested_at__isnull=False,
            extra_evidence_fulfilled_at__isnull=False,
        )
    elif extra_evidence_filter == "final_decision":
        qs = qs.exclude(status=ModerationAppeal.Status.PENDING)

    if include_status and status:
        qs = qs.filter(status=status)

    return qs, {
        "status": status,
        "q": q,
        "evidence": evidence_filter,
        "extra_evidence": extra_evidence_filter,
        "date_from": selected_date_from,
        "date_to": selected_date_to,
    }


@staff_member_required
def moderation_appeal_queue(request):
    filtered_qs, filters = _moderation_appeals_filtered_queryset(request, include_status=True)
    count_qs, _ = _moderation_appeals_filtered_queryset(request, include_status=False)

    all_matching_appeals = list(count_qs)

    total_appeals = len(all_matching_appeals)
    pending_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.PENDING)
    approved_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.APPROVED)
    rejected_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.REJECTED)

    waiting_extra_evidence_count = sum(
        1 for appeal in all_matching_appeals
        if _appeal_extra_evidence_state(appeal) == "waiting"
    )
    fulfilled_extra_evidence_count = sum(
        1 for appeal in all_matching_appeals
        if _appeal_extra_evidence_state(appeal) == "fulfilled"
    )

    total_evidence_files = 0
    total_evidence_size = 0

    for appeal in all_matching_appeals:
        attachments = list(appeal.attachments.all())
        total_evidence_files += len(attachments)
        total_evidence_size += sum(item.size or 0 for item in attachments)

    paginator = Paginator(filtered_qs.order_by("-created_at"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    appeals = list(page_obj.object_list)

    for appeal in appeals:
        attachments = list(appeal.attachments.all())
        evidence_total_size = sum(item.size or 0 for item in attachments)
        appeal.evidence_file_count = len(attachments)
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)
        appeal.extra_evidence_state = _appeal_extra_evidence_state(appeal)
        appeal.extra_evidence_label = _appeal_extra_evidence_label(appeal.extra_evidence_state)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_status": filters["status"],
            "selected_q": filters["q"],
            "selected_evidence": filters["evidence"],
            "selected_extra_evidence": filters["extra_evidence"],
            "selected_date_from": filters["date_from"],
            "selected_date_to": filters["date_to"],
            "status_choices": ModerationAppeal.Status.choices,
            "evidence_choices": [
                ("", "All evidence statuses"),
                ("has_evidence", "Has evidence"),
                ("no_evidence", "No evidence"),
            ],
            "extra_evidence_choices": [
                ("", "All extra-evidence states"),
                ("not_requested", "No extra evidence requested"),
                ("waiting", "Waiting for seller"),
                ("fulfilled", "Extra evidence uploaded"),
                ("final_decision", "Final decision locked"),
            ],
            "total_appeals": total_appeals,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "waiting_extra_evidence_count": waiting_extra_evidence_count,
            "fulfilled_extra_evidence_count": fulfilled_extra_evidence_count,
            "total_evidence_files": total_evidence_files,
            "total_evidence_mb": round(total_evidence_size / 1024 / 1024, 2),
            "quick_today": today.isoformat(),
            "quick_last_7_days": (today - datetime.timedelta(days=6)).isoformat(),
            "quick_last_30_days": (today - datetime.timedelta(days=29)).isoformat(),
            "page_title": "Moderation Appeals",
        },
    )


@staff_member_required
def moderation_appeal_export_csv(request):
    appeals, _filters = _moderation_appeals_filtered_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="moderation_appeals.csv"'

    writer = csv.writer(response)

    write_csv_row_v323(writer, [
        "appeal_id",
        "status",
        "appeal_type",
        "created_at",
        "appellant_username",
        "appellant_email",
        "listing_title",
        "evidence_file_count",
        "evidence_total_mb",
        "evidence_filenames",
        "extra_evidence_state",
        "extra_evidence_request_note",
        "extra_evidence_requested_at",
        "extra_evidence_fulfilled_at",
        "message",
        "decision_note",
        "internal_admin_note",
        "reviewed_by",
        "reviewed_at",
    ])

    for appeal in appeals.order_by("-created_at"):
        attachments = list(appeal.attachments.all())
        total_size = sum(item.size or 0 for item in attachments)
        total_mb = round(total_size / 1024 / 1024, 2)
        filenames = "; ".join(item.original_name for item in attachments)
        extra_state = _appeal_extra_evidence_state(appeal)

        write_csv_row_v323(writer, [
            appeal.pk,
            appeal.get_status_display(),
            appeal.get_appeal_type_display(),
            appeal.created_at.isoformat() if appeal.created_at else "",
            appeal.appellant.username if appeal.appellant else "",
            appeal.appellant.email if appeal.appellant else "",
            appeal.listing.title if appeal.listing else "",
            len(attachments),
            total_mb,
            filenames,
            _appeal_extra_evidence_label(extra_state),
            appeal.extra_evidence_request_note or "",
            appeal.extra_evidence_requested_at.isoformat() if appeal.extra_evidence_requested_at else "",
            appeal.extra_evidence_fulfilled_at.isoformat() if appeal.extra_evidence_fulfilled_at else "",
            appeal.message or "",
            appeal.decision_note or "",
            appeal.admin_note or "",
            appeal.reviewed_by.username if appeal.reviewed_by else "",
            appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
        ])

    return response



# APPEAL_EXTRA_EVIDENCE_DEADLINE_FLOW_V1
def _parse_admin_deadline(value):
    from django.utils.dateparse import parse_datetime

    value = (value or "").strip()

    if not value:
        return None

    parsed = parse_datetime(value)

    if parsed is None:
        return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed


def _appeal_extra_evidence_deadline_status(appeal):
    if appeal.status != ModerationAppeal.Status.PENDING:
        return "final_decision"

    if not getattr(appeal, "extra_evidence_requested_at", None):
        return "not_requested"

    if getattr(appeal, "extra_evidence_fulfilled_at", None):
        return "fulfilled"

    due_at = getattr(appeal, "extra_evidence_due_at", None)

    if due_at and due_at <= timezone.now():
        return "overdue"

    return "waiting"


def _appeal_extra_evidence_deadline_label(appeal):
    labels = {
        "not_requested": "No extra evidence requested",
        "waiting": "Waiting for seller before deadline",
        "overdue": "Deadline passed, final decision can start",
        "fulfilled": "Extra evidence uploaded before deadline",
        "final_decision": "Final decision locked",
    }
    return labels.get(_appeal_extra_evidence_deadline_status(appeal), "Unknown")


@staff_member_required
@require_POST
def moderation_appeal_request_extra_evidence(request, pk):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing_report",
            "user_report",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    if appeal.status != ModerationAppeal.Status.PENDING:
        messages.error(request, "Extra evidence can only be requested before a final decision.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    note = (request.POST.get("extra_evidence_request_note") or "").strip()
    due_at = _parse_admin_deadline(request.POST.get("extra_evidence_due_at"))

    if not note:
        messages.error(request, "Please write what extra evidence is needed.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if not due_at:
        messages.error(request, "Please choose a valid deadline for the seller.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if due_at <= timezone.now():
        messages.error(request, "The extra evidence deadline must be in the future.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    appeal.extra_evidence_requested_at = timezone.now()
    appeal.extra_evidence_due_at = due_at
    appeal.extra_evidence_request_note = note
    appeal.extra_evidence_requested_by = request.user
    appeal.extra_evidence_fulfilled_at = None
    appeal.save(
        update_fields=[
            "extra_evidence_requested_at",
            "extra_evidence_due_at",
            "extra_evidence_request_note",
            "extra_evidence_requested_by",
            "extra_evidence_fulfilled_at",
        ]
    )

    ModerationNotice.objects.create(
        recipient=appeal.appellant,
        title="Extra evidence requested for your appeal",
        body=(
            "Trust & Safety needs more evidence before making a final decision.\n\n"
            f"Request: {note}\n\n"
            f"Deadline: {timezone.localtime(due_at).strftime('%Y-%m-%d %H:%M')}\n\n"
            "If you do not upload the requested evidence before the deadline, "
            "admin may continue with the final decision based on the existing information."
        ),
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
    )

    _record_event_safely(
        event_type="notice_sent",
        title=f"Extra evidence requested for appeal #{appeal.pk}",
        actor=request.user,
        target_user=appeal.appellant,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
        appeal=appeal,
        public_note="Extra evidence requested before final decision.",
        internal_note=note,
        metadata={
            "appeal_status": appeal.status,
            "extra_evidence_due_at": due_at.isoformat(),
        },
    )

    messages.success(request, "Extra evidence request sent with a deadline.")
    return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)


@login_required
@require_POST
def moderation_appeal_add_extra_evidence(request, pk):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing_report",
            "user_report",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    if appeal.appellant_id != request.user.id:
        messages.error(request, "That appeal does not belong to your account.")
        return redirect("accounts:my_moderation_appeals")

    if appeal.status != ModerationAppeal.Status.PENDING:
        messages.error(request, "This appeal already has a final decision, so no more evidence can be added.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    if not appeal.extra_evidence_requested_at or appeal.extra_evidence_fulfilled_at:
        messages.error(request, "You can only add evidence when Trust & Safety has requested extra evidence.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    if appeal.extra_evidence_due_at and appeal.extra_evidence_due_at <= timezone.now():
        messages.error(request, "The deadline for uploading extra evidence has passed. Admin may now make a final decision.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    files = request.FILES.getlist("attachments")

    validation_errors = _validate_extra_evidence_files(appeal, files)

    if validation_errors:
        for error in validation_errors:
            messages.error(request, error)
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    for uploaded in files:
        ModerationAppealAttachment.objects.create(
            appeal=appeal,
            file=uploaded,
            original_name=uploaded.name,
            content_type=uploaded.content_type or "",
            size=uploaded.size or 0,
        )

    appeal.extra_evidence_fulfilled_at = timezone.now()
    appeal.save(update_fields=["extra_evidence_fulfilled_at"])

    User = get_user_model()
    staff_users = User.objects.filter(is_staff=True, is_active=True)

    for staff_user in staff_users:
        ModerationNotice.objects.create(
            recipient=staff_user,
            title="Extra appeal evidence uploaded",
            body=f"{request.user.username} uploaded extra evidence for appeal #{appeal.pk}. Admin can now continue the final decision process.",
            notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
            listing=appeal.listing,
            listing_report=appeal.listing_report,
            user_report=appeal.user_report,
        )

    _record_event_safely(
        event_type="appeal_submitted",
        title=f"Extra evidence added to appeal #{appeal.pk}",
        actor=request.user,
        target_user=request.user,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
        appeal=appeal,
        public_note="Extra evidence uploaded before the deadline.",
        metadata={
            "extra_file_count": len(files),
            "appeal_status": appeal.status,
        },
    )

    messages.success(request, "Extra evidence uploaded. Trust & Safety can now make a final decision.")
    return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)


@staff_member_required
@require_POST
def moderation_appeal_decide(request, pk, decision):
    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing_report",
            "user_report",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    if appeal.status != ModerationAppeal.Status.PENDING:
        messages.warning(request, "This appeal has already been decided. Final decisions cannot be changed.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    deadline_state = _appeal_extra_evidence_deadline_status(appeal)

    if deadline_state == "waiting":
        messages.error(
            request,
            "You requested extra evidence and the seller's deadline has not passed yet. "
            "Wait for the seller to upload evidence or wait until the deadline expires."
        )
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    evidence_reviewed = request.POST.get("evidence_reviewed") == "yes"
    decision_note = (request.POST.get("decision_note") or "").strip()
    admin_note = (request.POST.get("admin_note") or "").strip()

    if not evidence_reviewed:
        messages.error(request, "You must confirm that you reviewed the appeal evidence before deciding.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if not decision_note:
        messages.error(request, "Decision note is required and will be shown to the user.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if decision == "approve":
        appeal.status = ModerationAppeal.Status.APPROVED
        notice_title = "Your appeal was approved"
        event_type = "appeal_approved"
    elif decision == "reject":
        appeal.status = ModerationAppeal.Status.REJECTED
        notice_title = "Your appeal was rejected"
        event_type = "appeal_rejected"
    else:
        messages.error(request, "Invalid appeal decision.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    appeal.decision_note = decision_note
    appeal.admin_note = admin_note or appeal.admin_note or ""
    appeal.reviewed_by = request.user
    appeal.reviewed_at = timezone.now()
    appeal.save(
        update_fields=[
            "status",
            "decision_note",
            "admin_note",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    ModerationNotice.objects.create(
        recipient=appeal.appellant,
        title=notice_title,
        body=decision_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
    )

    _record_event_safely(
        event_type=event_type,
        title=f"Appeal #{appeal.pk} {appeal.status}",
        actor=request.user,
        target_user=appeal.appellant,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
        appeal=appeal,
        public_note=appeal.decision_note,
        internal_note=appeal.admin_note,
        metadata={
            "appeal_status": appeal.status,
            "extra_evidence_deadline_state": deadline_state,
        },
    )

    messages.success(
        request,
        "Final appeal decision saved and user notified. No listing or seller restriction was changed automatically.",
    )
    return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)


def _appeal_extra_evidence_state(appeal):
    return _appeal_extra_evidence_deadline_status(appeal)


def _appeal_extra_evidence_label(state):
    labels = {
        "not_requested": "No extra evidence requested",
        "waiting": "Waiting for seller before deadline",
        "overdue": "Deadline passed, final decision can start",
        "fulfilled": "Extra evidence uploaded before deadline",
        "final_decision": "Final decision locked",
    }
    return labels.get(state, "Unknown")


# APPEAL_DEADLINE_QUEUE_V2
def _appeal_deadline_queue_state(appeal):
    import datetime as _dt

    if appeal.status != ModerationAppeal.Status.PENDING:
        return "final_decision"

    if not getattr(appeal, "extra_evidence_requested_at", None):
        return "not_requested"

    if getattr(appeal, "extra_evidence_fulfilled_at", None):
        return "fulfilled"

    due_at = getattr(appeal, "extra_evidence_due_at", None)

    if not due_at:
        return "waiting"

    now = timezone.now()

    if due_at <= now:
        return "overdue"

    if due_at <= now + _dt.timedelta(days=15):
        return "due_soon"

    return "waiting"


def _appeal_deadline_queue_label(state):
    labels = {
        "not_requested": "No extra evidence requested",
        "waiting": "Waiting before deadline",
        "due_soon": "Due within 15 days",
        "overdue": "Deadline passed",
        "fulfilled": "Extra evidence uploaded",
        "final_decision": "Final decision locked",
    }
    return labels.get(state, "Unknown")


def _appeal_extra_evidence_state(appeal):
    return _appeal_deadline_queue_state(appeal)


def _appeal_extra_evidence_label(state):
    return _appeal_deadline_queue_label(state)


# APPEAL_QUEUE_DATE_FILTER_SAFETY_V93
def _parse_appeal_queue_date_filter(value):
    import datetime as _dt

    raw_value = (value or "").strip()
    if not raw_value:
        return None, "", False

    try:
        parsed_date = _dt.date.fromisoformat(raw_value)
    except ValueError:
        return None, raw_value, True

    return parsed_date, parsed_date.isoformat(), False


def _appeal_queue_start_of_day(value):
    import datetime as _dt

    return timezone.make_aware(
        _dt.datetime.combine(value, _dt.time.min),
        timezone.get_current_timezone(),
    )


def _appeal_queue_start_of_next_day(value):
    import datetime as _dt

    return _appeal_queue_start_of_day(value + _dt.timedelta(days=1))


def _moderation_appeals_filtered_queryset(request, include_status=True):
    import datetime as _dt

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    evidence_filter = (request.GET.get("evidence") or "").strip()
    extra_evidence_filter = (request.GET.get("extra_evidence") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()

    date_from, selected_date_from, invalid_date_from = _parse_appeal_queue_date_filter(selected_date_from)
    date_to, selected_date_to, invalid_date_to = _parse_appeal_queue_date_filter(selected_date_to)
    date_filter_error = ""

    if invalid_date_from or invalid_date_to:
        date_filter_error = "Enter valid appeal queue dates in YYYY-MM-DD format."
    elif date_from and date_to and date_from > date_to:
        date_filter_error = "From date cannot be after To date."

    qs = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
        "extra_evidence_requested_by",
    ).prefetch_related("attachments")

    if date_filter_error:
        return qs.none(), {
            "status": status,
            "q": q,
            "evidence": evidence_filter,
            "extra_evidence": extra_evidence_filter,
            "date_from": selected_date_from,
            "date_to": selected_date_to,
            "date_filter_error": date_filter_error,
        }

    if q:
        qs = qs.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(extra_evidence_request_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    if date_from:
        qs = qs.filter(created_at__gte=_appeal_queue_start_of_day(date_from))

    if date_to:
        qs = qs.filter(created_at__lt=_appeal_queue_start_of_next_day(date_to))

    if evidence_filter == "has_evidence":
        qs = qs.filter(attachments__isnull=False).distinct()
    elif evidence_filter == "no_evidence":
        qs = qs.filter(attachments__isnull=True)

    now = timezone.now()
    reminder_window = now + _dt.timedelta(days=15)

    if extra_evidence_filter == "not_requested":
        qs = qs.filter(
            status=ModerationAppeal.Status.PENDING,
            extra_evidence_requested_at__isnull=True,
        )
    elif extra_evidence_filter == "waiting":
        qs = qs.filter(
            status=ModerationAppeal.Status.PENDING,
            extra_evidence_requested_at__isnull=False,
            extra_evidence_fulfilled_at__isnull=True,
            extra_evidence_due_at__gt=now,
        )
    elif extra_evidence_filter == "due_soon":
        qs = qs.filter(
            status=ModerationAppeal.Status.PENDING,
            extra_evidence_requested_at__isnull=False,
            extra_evidence_fulfilled_at__isnull=True,
            extra_evidence_due_at__gt=now,
            extra_evidence_due_at__lte=reminder_window,
        )
    elif extra_evidence_filter == "overdue":
        qs = qs.filter(
            status=ModerationAppeal.Status.PENDING,
            extra_evidence_requested_at__isnull=False,
            extra_evidence_fulfilled_at__isnull=True,
            extra_evidence_due_at__lte=now,
        )
    elif extra_evidence_filter == "fulfilled":
        qs = qs.filter(
            status=ModerationAppeal.Status.PENDING,
            extra_evidence_requested_at__isnull=False,
            extra_evidence_fulfilled_at__isnull=False,
        )
    elif extra_evidence_filter == "final_decision":
        qs = qs.exclude(status=ModerationAppeal.Status.PENDING)

    if include_status and status:
        qs = qs.filter(status=status)

    return qs, {
        "status": status,
        "q": q,
        "evidence": evidence_filter,
        "extra_evidence": extra_evidence_filter,
        "date_from": selected_date_from,
        "date_to": selected_date_to,
        "date_filter_error": date_filter_error,
    }


@staff_member_required
def moderation_appeal_queue(request):
    import datetime as _dt

    filtered_qs, filters = _moderation_appeals_filtered_queryset(request, include_status=True)
    count_qs, _ = _moderation_appeals_filtered_queryset(request, include_status=False)

    all_matching_appeals = list(count_qs)

    total_appeals = len(all_matching_appeals)
    pending_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.PENDING)
    approved_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.APPROVED)
    rejected_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.REJECTED)

    waiting_count = sum(1 for appeal in all_matching_appeals if _appeal_deadline_queue_state(appeal) == "waiting")
    due_soon_count = sum(1 for appeal in all_matching_appeals if _appeal_deadline_queue_state(appeal) == "due_soon")
    overdue_count = sum(1 for appeal in all_matching_appeals if _appeal_deadline_queue_state(appeal) == "overdue")
    fulfilled_extra_evidence_count = sum(1 for appeal in all_matching_appeals if _appeal_deadline_queue_state(appeal) == "fulfilled")

    total_evidence_files = 0
    total_evidence_size = 0

    for appeal in all_matching_appeals:
        attachments = list(appeal.attachments.all())
        total_evidence_files += len(attachments)
        total_evidence_size += sum(item.size or 0 for item in attachments)

    paginator = Paginator(filtered_qs.order_by("-created_at"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    appeals = list(page_obj.object_list)

    for appeal in appeals:
        attachments = list(appeal.attachments.all())
        evidence_total_size = sum(item.size or 0 for item in attachments)
        appeal.evidence_file_count = len(attachments)
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)
        appeal.extra_evidence_state = _appeal_deadline_queue_state(appeal)
        appeal.extra_evidence_label = _appeal_deadline_queue_label(appeal.extra_evidence_state)
        appeal.extra_evidence_due_iso = ""
        if getattr(appeal, "extra_evidence_due_at", None):
            appeal.extra_evidence_due_iso = timezone.localtime(appeal.extra_evidence_due_at).isoformat()

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_status": filters["status"],
            "selected_q": filters["q"],
            "selected_evidence": filters["evidence"],
            "selected_extra_evidence": filters["extra_evidence"],
            "selected_date_from": filters["date_from"],
            "selected_date_to": filters["date_to"],
            "date_filter_error": filters["date_filter_error"],
            "status_choices": ModerationAppeal.Status.choices,
            "evidence_choices": [
                ("", "All evidence statuses"),
                ("has_evidence", "Has evidence"),
                ("no_evidence", "No evidence"),
            ],
            "extra_evidence_choices": [
                ("", "All extra-evidence states"),
                ("not_requested", "No extra evidence requested"),
                ("waiting", "Waiting before deadline"),
                ("due_soon", "Due within 15 days"),
                ("overdue", "Deadline passed"),
                ("fulfilled", "Extra evidence uploaded"),
                ("final_decision", "Final decision locked"),
            ],
            "total_appeals": total_appeals,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "waiting_count": waiting_count,
            "due_soon_count": due_soon_count,
            "overdue_count": overdue_count,
            "fulfilled_extra_evidence_count": fulfilled_extra_evidence_count,
            "total_evidence_files": total_evidence_files,
            "total_evidence_mb": round(total_evidence_size / 1024 / 1024, 2),
            "quick_today": today.isoformat(),
            "quick_last_7_days": (today - _dt.timedelta(days=6)).isoformat(),
            "quick_last_30_days": (today - _dt.timedelta(days=29)).isoformat(),
            "page_title": "Moderation Appeals",
        },
    )


@staff_member_required
def moderation_appeal_export_csv(request):
    appeals, _filters = _moderation_appeals_filtered_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="moderation_appeals.csv"'

    writer = csv.writer(response)

    write_csv_row_v323(writer, [
        "appeal_id",
        "status",
        "appeal_type",
        "created_at",
        "appellant_username",
        "appellant_email",
        "listing_title",
        "evidence_file_count",
        "evidence_total_mb",
        "evidence_filenames",
        "extra_evidence_state",
        "extra_evidence_requested_at",
        "extra_evidence_due_at",
        "extra_evidence_fulfilled_at",
        "extra_evidence_reminder_sent_at",
        "extra_evidence_overdue_notice_sent_at",
        "extra_evidence_request_note",
        "message",
        "decision_note",
        "internal_admin_note",
        "reviewed_by",
        "reviewed_at",
    ])

    for appeal in appeals.order_by("-created_at"):
        attachments = list(appeal.attachments.all())
        total_size = sum(item.size or 0 for item in attachments)
        total_mb = round(total_size / 1024 / 1024, 2)
        filenames = "; ".join(item.original_name for item in attachments)
        extra_state = _appeal_deadline_queue_state(appeal)

        write_csv_row_v323(writer, [
            appeal.pk,
            appeal.get_status_display(),
            appeal.get_appeal_type_display(),
            appeal.created_at.isoformat() if appeal.created_at else "",
            appeal.appellant.username if appeal.appellant else "",
            appeal.appellant.email if appeal.appellant else "",
            appeal.listing.title if appeal.listing else "",
            len(attachments),
            total_mb,
            filenames,
            _appeal_deadline_queue_label(extra_state),
            appeal.extra_evidence_requested_at.isoformat() if appeal.extra_evidence_requested_at else "",
            appeal.extra_evidence_due_at.isoformat() if appeal.extra_evidence_due_at else "",
            appeal.extra_evidence_fulfilled_at.isoformat() if appeal.extra_evidence_fulfilled_at else "",
            appeal.extra_evidence_reminder_sent_at.isoformat() if appeal.extra_evidence_reminder_sent_at else "",
            appeal.extra_evidence_overdue_notice_sent_at.isoformat() if appeal.extra_evidence_overdue_notice_sent_at else "",
            appeal.extra_evidence_request_note or "",
            appeal.message or "",
            appeal.decision_note or "",
            appeal.admin_note or "",
            appeal.reviewed_by.username if appeal.reviewed_by else "",
            appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
        ])

    return response
