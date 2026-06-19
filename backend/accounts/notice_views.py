# NOTICE_VIEWS_PAGINATION_FINAL_V1
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import ModerationAppeal, ModerationNotice


@login_required
def moderation_notices(request):
    read_filter = (request.GET.get("read") or "").strip()

    notices_qs = (
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        )
        .filter(recipient=request.user)
        .order_by("-created_at")
    )

    if read_filter == "unread":
        notices_qs = notices_qs.filter(is_read=False)
    elif read_filter == "read":
        notices_qs = notices_qs.filter(is_read=True)

    paginator = Paginator(notices_qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    notices = list(page_obj.object_list)

    appealable_types = {
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    }
    non_appealable_words = [
        "lifted",
        "restored",
        "appeal was approved",
        "appeal was rejected",
    ]

    for notice in notices:
        title_lower = (notice.title or "").lower()
        body_lower = (notice.body or "").lower()

        notice.can_show_appeal_link = (
            notice.notice_type in appealable_types
            and not any(word in title_lower or word in body_lower for word in non_appealable_words)
        )

        notice.existing_appeal = (
            ModerationAppeal.objects.filter(
                appellant=request.user,
                moderation_notice=notice,
            )
            .order_by("-created_at")
            .first()
        )

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "accounts/moderation_notices.html",
        {
            "notices": notices,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_read": read_filter,
            "unread_count": ModerationNotice.objects.filter(
                recipient=request.user,
                is_read=False,
            ).count(),
            "page_title": "Notices",
        },
    )


@login_required
@require_POST
def moderation_notice_mark_read(request, pk):
    notice = get_object_or_404(
        ModerationNotice,
        pk=pk,
        recipient=request.user,
    )

    if not notice.is_read:
        notice.is_read = True
        notice.save(update_fields=["is_read"])

    next_url = request.POST.get("next") or request.GET.get("next")

    if next_url:
        return redirect(next_url)

    return redirect("accounts:moderation_notices")


@login_required
@require_POST
def moderation_notices_mark_all_read(request):
    updated = ModerationNotice.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    if updated:
        messages.success(request, f"Marked {updated} notice(s) as read.")
    else:
        messages.info(request, "You do not have any unread notices.")

    return redirect("accounts:moderation_notices")
