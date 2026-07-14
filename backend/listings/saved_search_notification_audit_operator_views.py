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

V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_UX_ACCESSIBILITY = (
    "V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_UX_ACCESSIBILITY"
)

FILTER_DISPLAY_ORDER = (
    "event_id",
    "saved_search_id",
    "owner_id_snapshot",
    "event_type",
    "outcome",
    "actor_type",
    "source",
    "reason_code",
    "batch_id",
    "correlation_id",
    "delivery_attempt_id",
    "idempotency_key",
    "notification_fingerprint",
    "rollback_linked",
    "occurred_from",
    "occurred_to",
    "page_size",
)

FILTER_LABELS = {
    "event_id": "Event ID",
    "saved_search_id": "Saved-search ID",
    "owner_id_snapshot": "Owner ID snapshot",
    "event_type": "Event type",
    "outcome": "Outcome",
    "actor_type": "Actor type",
    "source": "Source",
    "reason_code": "Reason code",
    "batch_id": "Batch ID",
    "correlation_id": "Correlation ID",
    "delivery_attempt_id": "Delivery-attempt ID",
    "idempotency_key": "Idempotency key",
    "notification_fingerprint": "Notification fingerprint",
    "rollback_linked": "Rollback linkage",
    "occurred_from": "Occurred from",
    "occurred_to": "Occurred to",
    "page_size": "Page size",
}


def _choice_label(
    raw_value: str,
    choices,
) -> str:
    return dict(choices).get(
        raw_value,
        raw_value,
    )


def _display_filter_value(
    name: str,
    raw_value: str,
) -> str:
    if name == "event_type":
        return _choice_label(
            raw_value,
            SavedSearchNotificationAuditEvent
            .EventType
            .choices,
        )

    if name == "outcome":
        return _choice_label(
            raw_value,
            SavedSearchNotificationAuditEvent
            .Outcome
            .choices,
        )

    if name == "actor_type":
        return _choice_label(
            raw_value,
            SavedSearchNotificationAuditEvent
            .ActorType
            .choices,
        )

    if name == "rollback_linked":
        return {
            "true": "Linked rollback events",
            "1": "Linked rollback events",
            "false": "Events without rollback links",
            "0": "Events without rollback links",
        }.get(
            raw_value.casefold(),
            raw_value,
        )

    return raw_value


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

    def _url_from_query(
        self,
        query_string: str,
    ) -> str:
        if not query_string:
            return self.request.path

        return (
            self.request.path
            + "?"
            + query_string
        )

    def _active_filter_items(
        self,
        filter_values: dict[str, str],
    ) -> tuple[dict[str, str], ...]:
        active_filters = []

        for name in FILTER_DISPLAY_ORDER:
            raw_value = str(
                filter_values.get(name, "")
                or ""
            ).strip()

            if not raw_value:
                continue

            if (
                name == "page_size"
                and raw_value == "50"
            ):
                continue

            remove_query = self.request.GET.copy()
            remove_query.pop(name, None)
            remove_query.pop("page", None)
            remove_query.pop("format", None)

            active_filters.append(
                {
                    "name": name,
                    "label": FILTER_LABELS[name],
                    "value": _display_filter_value(
                        name,
                        raw_value,
                    ),
                    "remove_url": self._url_from_query(
                        remove_query.urlencode()
                    ),
                }
            )

        return tuple(active_filters)

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

        active_filters = self._active_filter_items(
            filter_values
        )

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

        previous_page_url = ""

        if page.has_previous:
            previous_page_url = self._url_from_query(
                self._query_without(
                    "page",
                    "format",
                    overrides={
                        "page": page.previous_page_number,
                    },
                )
            )

        next_page_url = ""

        if page.has_next:
            next_page_url = self._url_from_query(
                self._query_without(
                    "page",
                    "format",
                    overrides={
                        "page": page.next_page_number,
                    },
                )
            )

        event_word = (
            "event"
            if page.total_count == 1
            else "events"
        )

        result_summary = (
            f"{page.total_count} audit {event_word} found. "
            f"Page {page.number} of {page.total_pages}."
        )

        context = {
            "marker": (
                V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_VIEW
            ),
            "ux_marker": (
                V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_UX_ACCESSIBILITY
            ),
            "events": page.items,
            "page_result": page,
            "filter_values": filter_values,
            "active_filters": active_filters,
            "active_filter_count": len(active_filters),
            "has_active_filters": bool(active_filters),
            "pagination_query": pagination_query,
            "csv_query": csv_query,
            "csv_url": self._url_from_query(
                csv_query
            ),
            "previous_page_url": previous_page_url,
            "next_page_url": next_page_url,
            "clear_filters_url": request.path,
            "operator_path": request.path,
            "result_summary": result_summary,
            "csv_result_limit": MAXIMUM_CSV_ROWS,
            "csv_will_be_truncated": (
                page.total_count > MAXIMUM_CSV_ROWS
            ),
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
    "FILTER_DISPLAY_ORDER",
    "FILTER_LABELS",
    "SavedSearchNotificationAuditEventListView",
    "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_VIEW",
    "V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_UX_ACCESSIBILITY",
]
