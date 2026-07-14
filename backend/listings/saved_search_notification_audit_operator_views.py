from __future__ import annotations

import csv
from typing import Any

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.core.exceptions import PermissionDenied
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import render
from django.views import View

from .models import SavedSearchNotificationAuditEvent
from .saved_search_notification_audit_operator import (
    CSV_HEADERS,
    MAXIMUM_CSV_ROWS,
    SUPPORTED_FILTER_NAMES,
    SavedSearchNotificationAuditOperatorFilterError,
    build_saved_search_notification_audit_operator_queryset,
    iter_saved_search_notification_audit_csv_rows,
    paginate_saved_search_notification_audit_operator_events,
    parse_saved_search_notification_audit_operator_filters,
)


V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_VIEW = (
    "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_VIEW"
)


class SavedSearchNotificationAuditEventListView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    View,
):
    http_method_names = [
        "get",
        "head",
    ]

    template_name = (
        "listings/"
        "saved_search_notification_audit_events.html"
    )

    def test_func(self) -> bool:
        return bool(
            self.request.user.is_authenticated
            and self.request.user.is_staff
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied

        return super().handle_no_permission()

    def _bad_request(self) -> HttpResponseBadRequest:
        return HttpResponseBadRequest(
            "Invalid saved-search notification audit filter."
        )

    def _query_without(
        self,
        *excluded_names: str,
        overrides: dict[str, Any] | None = None,
    ) -> str:
        query = self.request.GET.copy()

        for name in excluded_names:
            query.pop(name, None)

        for name, value in (overrides or {}).items():
            if value in (
                None,
                "",
            ):
                query.pop(name, None)
            else:
                query[name] = str(value)

        return query.urlencode()

    def _csv_response(
        self,
        queryset,
    ) -> HttpResponse:
        response = HttpResponse(
            content_type="text/csv; charset=utf-8"
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; filename="
            '"saved-search-notification-audit.csv"'
        )

        response["X-Result-Limit"] = str(
            MAXIMUM_CSV_ROWS
        )

        if queryset[MAXIMUM_CSV_ROWS:MAXIMUM_CSV_ROWS + 1].exists():
            response["X-Result-Truncated"] = "1"
        else:
            response["X-Result-Truncated"] = "0"

        writer = csv.writer(response)
        writer.writerow(CSV_HEADERS)

        for row in (
            iter_saved_search_notification_audit_csv_rows(
                queryset
            )
        ):
            writer.writerow(row)

        return response

    def get(self, request, *args, **kwargs):
        try:
            filters = (
                parse_saved_search_notification_audit_operator_filters(
                    request.GET
                )
            )

            queryset = (
                build_saved_search_notification_audit_operator_queryset(
                    filters
                )
            )

            if filters.output_format == "csv":
                return self._csv_response(queryset)

            page = (
                paginate_saved_search_notification_audit_operator_events(
                    queryset,
                    page_number=filters.page,
                    page_size=filters.page_size,
                )
            )
        except SavedSearchNotificationAuditOperatorFilterError:
            return self._bad_request()

        filter_values = {
            name: request.GET.get(name, "")
            for name in SUPPORTED_FILTER_NAMES
        }

        pagination_query = self._query_without(
            "page",
            "format",
        )

        csv_query = self._query_without(
            "page",
            "format",
            overrides={
                "format": "csv",
            },
        )

        context = {
            "marker": (
                V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_VIEW
            ),
            "events": page.items,
            "page_result": page,
            "filter_values": filter_values,
            "pagination_query": pagination_query,
            "csv_query": csv_query,
            "operator_path": request.path,
            "event_type_choices": (
                SavedSearchNotificationAuditEvent
                .EventType
                .choices
            ),
            "outcome_choices": (
                SavedSearchNotificationAuditEvent
                .Outcome
                .choices
            ),
            "actor_type_choices": (
                SavedSearchNotificationAuditEvent
                .ActorType
                .choices
            ),
        }

        return render(
            request,
            self.template_name,
            context,
        )


__all__ = [
    "SavedSearchNotificationAuditEventListView",
    "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_VIEW",
]
