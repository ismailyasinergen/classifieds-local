"""Read-only staff interface for v294 pricing-integrity evidence."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views import View

from .models import Listing
from .pricing_integrity_moderation_queue_v294 import (
    GUARDRAIL_CHOICES_V294,
    STATE_CHOICES_V294,
    build_pricing_integrity_queue_queryset_v294,
    paginate_pricing_integrity_queue_v294,
    parse_pricing_integrity_queue_filters_v294,
)


class PricingIntegrityModerationQueueViewV294(
    LoginRequiredMixin,
    UserPassesTestMixin,
    View,
):
    http_method_names = ["get", "head"]
    template_name = "listings/pricing_integrity_moderation_queue_v294.html"

    def test_func(self):
        return bool(
            self.request.user.is_authenticated
            and self.request.user.is_staff
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()

    @staticmethod
    def _page_url(request, page_number):
        query = request.GET.copy()
        query["page"] = page_number
        return f"{request.path}?{query.urlencode()}"

    def get(self, request, *args, **kwargs):
        filters = parse_pricing_integrity_queue_filters_v294(request.GET)
        queryset = build_pricing_integrity_queue_queryset_v294(filters)
        page = paginate_pricing_integrity_queue_v294(
            queryset,
            request.GET.get("page"),
        )

        return render(
            request,
            self.template_name,
            {
                "page_title": "Pricing Integrity",
                "events": page.object_list,
                "page_obj": page,
                "filters": filters,
                "guardrail_choices": GUARDRAIL_CHOICES_V294,
                "listing_status_choices": Listing.Status.choices,
                "state_choices": STATE_CHOICES_V294,
                "previous_page_url": (
                    self._page_url(request, page.previous_page_number())
                    if page.has_previous()
                    else ""
                ),
                "next_page_url": (
                    self._page_url(request, page.next_page_number())
                    if page.has_next()
                    else ""
                ),
            },
        )


__all__ = ["PricingIntegrityModerationQueueViewV294"]
