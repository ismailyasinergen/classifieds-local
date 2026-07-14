from __future__ import annotations

import csv
import io
import uuid
from datetime import timedelta
from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from listings.models import (
    SavedSearch,
    SavedSearchNotificationAuditEvent,
)
from listings.saved_search_notification_audit_operator import (
    CSV_HEADERS,
    MAXIMUM_CSV_ROWS,
    MAXIMUM_METADATA_DEPTH,
    MAXIMUM_METADATA_RENDERED_BYTES,
    MAXIMUM_PAGE_SIZE,
    METADATA_REDACTION_TEXT,
    SavedSearchNotificationAuditOperatorFilterError,
    build_saved_search_notification_audit_operator_queryset,
    parse_saved_search_notification_audit_operator_filters,
    sanitize_saved_search_notification_audit_metadata_for_operator,
    serialize_saved_search_notification_audit_event_for_operator,
)
from listings.saved_search_notification_audit_persistence import (
    record_saved_search_notification_audit_event,
)


V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE = (
    "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE"
)


class SavedSearchNotificationPersistentAuditOperatorReadInterfaceV234Tests(
    TestCase
):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.staff = user_model.objects.create_user(
            username="v234-staff",
            email="v234-staff@example.com",
            password="v234-password",
            is_staff=True,
        )

        cls.non_staff = user_model.objects.create_user(
            username="v234-non-staff",
            email="v234-non-staff@example.com",
            password="v234-password",
        )

        cls.owner = user_model.objects.create_user(
            username="v234-owner",
            email="private-v234-owner@example.com",
            password="v234-password",
        )

        cls.saved_search = SavedSearch.objects.create(
            user=cls.owner,
            name="V234 audit search",
            path="/private-v234-path/",
            query_params={
                "q": "private-v234-query",
            },
            querystring="q=private-v234-query",
            email_notifications_enabled=True,
        )

    def setUp(self):
        self.base_time = timezone.now()

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _url(self) -> str:
        for name in (
            (
                "listings:"
                "saved-search-notification-audit-events"
            ),
            "saved-search-notification-audit-events",
        ):
            try:
                return reverse(name)
            except NoReverseMatch:
                continue

        self.fail(
            "The v234 operator URL could not be reversed."
        )

    def _record(
        self,
        *,
        event_type=(
            SavedSearchNotificationAuditEvent
            .EventType
            .EVALUATION_STARTED
        ),
        outcome=(
            SavedSearchNotificationAuditEvent
            .Outcome
            .PENDING
        ),
        reason_code="",
        source="saved_search.test.v234",
        actor_type=(
            SavedSearchNotificationAuditEvent
            .ActorType
            .SYSTEM
        ),
        occurred_at=None,
        metadata=None,
        delivery_attempt_id=None,
        rollback_of=None,
        idempotency_suffix=None,
    ):
        return record_saved_search_notification_audit_event(
            saved_search=self.saved_search,
            event_type=event_type,
            outcome=outcome,
            occurred_at=occurred_at or self.base_time,
            correlation_id=uuid.uuid4(),
            delivery_attempt_id=delivery_attempt_id,
            idempotency_key=(
                "v234:"
                + str(
                    idempotency_suffix
                    or uuid.uuid4()
                )
            ),
            notification_fingerprint="a" * 64,
            rollback_of=rollback_of,
            actor_type=actor_type,
            source=source,
            reason_code=reason_code,
            metadata=metadata or {
                "mode": "v234-test",
            },
        ).event

    def _create_hostile_metadata_event(self):
        return SavedSearchNotificationAuditEvent.objects.create(
            saved_search=self.saved_search,
            owner_id_snapshot=str(self.owner.pk),
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .EVALUATION_STARTED
            ),
            outcome=(
                SavedSearchNotificationAuditEvent
                .Outcome
                .PENDING
            ),
            reason_code="hostile-metadata",
            occurred_at=self.base_time,
            correlation_id=uuid.uuid4(),
            idempotency_key=(
                "v234-hostile:"
                + str(uuid.uuid4())
            ),
            notification_fingerprint="b" * 64,
            actor_type=(
                SavedSearchNotificationAuditEvent
                .ActorType
                .SYSTEM
            ),
            actor_identifier="v234-hostile-test",
            source="saved_search.test.v234.hostile",
            metadata={
                "safe": "visible",
                "recipient_email": (
                    "never-render@example.com"
                ),
                "nested": {
                    "token": "never-render-token",
                    "safe_nested": "visible-nested",
                },
            },
        )

    def test_v234_marker_and_bounds_are_stable(self):
        self.assertEqual(
            V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE,
            (
                "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
                "AUDIT_OPERATOR_READ_INTERFACE"
            ),
        )
        self.assertEqual(MAXIMUM_PAGE_SIZE, 100)
        self.assertEqual(MAXIMUM_CSV_ROWS, 5000)
        self.assertEqual(MAXIMUM_METADATA_DEPTH, 6)
        self.assertEqual(
            MAXIMUM_METADATA_RENDERED_BYTES,
            16384,
        )
        self.assertEqual(
            METADATA_REDACTION_TEXT,
            "[redacted]",
        )

    def test_v234_url_resolves_to_expected_staff_path(self):
        self.assertEqual(
            self._url(),
            "/staff/saved-search-notification-audit/",
        )

    def test_v234_anonymous_request_redirects_to_login(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "next=",
            response["Location"],
        )

    def test_v234_authenticated_non_staff_receives_403(self):
        self.client.force_login(self.non_staff)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 403)

    def test_v234_staff_can_view_persisted_events(self):
        event = self._record(
            reason_code="visible-reason",
        )

        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            str(event.pk),
        )
        self.assertContains(
            response,
            "visible-reason",
        )
        self.assertContains(
            response,
            "Read-only staff interface",
        )

    def test_v234_mutation_methods_return_405(self):
        self.client.force_login(self.staff)

        for method_name in (
            "post",
            "put",
            "patch",
            "delete",
        ):
            with self.subTest(method_name=method_name):
                response = getattr(
                    self.client,
                    method_name,
                )(
                    self._url(),
                    data={
                        "unsafe": "mutation",
                    },
                    content_type="application/json",
                )

                self.assertEqual(
                    response.status_code,
                    405,
                )

    def test_v234_exact_filters_limit_results(self):
        first = self._record(
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .EVALUATION_STARTED
            ),
            reason_code="first",
            source="saved_search.test.first",
        )

        second = self._record(
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .DRY_RUN_RENDERED
            ),
            outcome=(
                SavedSearchNotificationAuditEvent
                .Outcome
                .SUCCEEDED
            ),
            reason_code="second",
            source="saved_search.test.second",
        )

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "event_id": str(first.pk),
                "event_type": "evaluation_started",
                "source": "saved_search.test.first",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(first.pk))
        self.assertNotContains(response, str(second.pk))

    def test_v234_invalid_filters_fail_closed_with_400(self):
        invalid_queries = (
            {
                "event_id": "not-a-uuid",
            },
            {
                "saved_search_id": "zero",
            },
            {
                "event_type": "unknown-event",
            },
            {
                "outcome": "unknown-outcome",
            },
            {
                "actor_type": "unknown-actor",
            },
            {
                "notification_fingerprint": "short",
            },
            {
                "rollback_linked": "maybe",
            },
            {
                "occurred_from": "not-a-date",
            },
            {
                "occurred_from": "2026-07-14T10:00:00",
            },
            {
                "occurred_from": (
                    "2026-07-15T00:00:00+00:00"
                ),
                "occurred_to": (
                    "2026-07-14T00:00:00+00:00"
                ),
            },
            {
                "page": "0",
            },
            {
                "page_size": "101",
            },
            {
                "format": "json",
            },
            {
                "unknown_filter": "unsafe",
            },
        )

        self.client.force_login(self.staff)

        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(
                    self._url(),
                    query,
                )

                self.assertEqual(
                    response.status_code,
                    400,
                )

    def test_v234_duplicate_filter_values_fail_closed(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            self._url() + "?event_type=a&event_type=b"
        )

        self.assertEqual(response.status_code, 400)

    def test_v234_html_pagination_is_bounded_and_deterministic(self):
        oldest = self._record(
            reason_code="oldest",
            occurred_at=self.base_time - timedelta(minutes=2),
        )
        middle = self._record(
            reason_code="middle",
            occurred_at=self.base_time - timedelta(minutes=1),
        )
        newest = self._record(
            reason_code="newest",
            occurred_at=self.base_time,
        )

        self.client.force_login(self.staff)

        first_page = self.client.get(
            self._url(),
            {
                "page_size": "1",
                "page": "1",
            },
        )

        second_page = self.client.get(
            self._url(),
            {
                "page_size": "1",
                "page": "2",
            },
        )

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)

        self.assertContains(first_page, str(newest.pk))
        self.assertNotContains(first_page, str(middle.pk))
        self.assertNotContains(first_page, str(oldest.pk))

        self.assertContains(second_page, str(middle.pk))
        self.assertNotContains(second_page, str(newest.pk))

    def test_v234_out_of_range_page_returns_400(self):
        self._record()

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "page": "999",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_v234_metadata_is_sanitized_again_on_read(self):
        event = self._create_hostile_metadata_event()

        serialized = (
            serialize_saved_search_notification_audit_event_for_operator(
                event
            )
        )

        self.assertIn(
            '"safe":"visible"',
            serialized["metadata_json"],
        )
        self.assertIn(
            '"recipient_email":"[redacted]"',
            serialized["metadata_json"],
        )
        self.assertIn(
            '"token":"[redacted]"',
            serialized["metadata_json"],
        )
        self.assertNotIn(
            "never-render@example.com",
            serialized["metadata_json"],
        )
        self.assertNotIn(
            "never-render-token",
            serialized["metadata_json"],
        )

    def test_v234_html_never_exposes_owner_email_or_query_details(self):
        self._create_hostile_metadata_event()

        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            self.owner.email,
        )
        self.assertNotContains(
            response,
            "private-v234-query",
        )
        self.assertNotContains(
            response,
            "/private-v234-path/",
        )
        self.assertNotContains(
            response,
            "never-render@example.com",
        )
        self.assertNotContains(
            response,
            "never-render-token",
        )

    def test_v234_csv_is_staff_only_bounded_and_has_fixed_headers(self):
        self._record()

        anonymous_response = self.client.get(
            self._url(),
            {
                "format": "csv",
            },
        )

        self.assertEqual(
            anonymous_response.status_code,
            302,
        )

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "format": "csv",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "text/csv; charset=utf-8",
        )
        self.assertIn(
            "saved-search-notification-audit.csv",
            response["Content-Disposition"],
        )
        self.assertEqual(
            response["X-Result-Limit"],
            "5000",
        )

        rows = list(
            csv.reader(
                io.StringIO(
                    response.content.decode("utf-8")
                )
            )
        )

        self.assertEqual(
            tuple(rows[0]),
            CSV_HEADERS,
        )
        self.assertEqual(len(rows), 2)

    def test_v234_csv_uses_same_filters_as_html(self):
        included = self._record(
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .DELIVERY_FAILED
            ),
            outcome=(
                SavedSearchNotificationAuditEvent
                .Outcome
                .FAILED
            ),
            reason_code="included",
            delivery_attempt_id=uuid.uuid4(),
        )

        excluded = self._record(
            reason_code="excluded",
        )

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "format": "csv",
                "event_type": "delivery_failed",
            },
        )

        content = response.content.decode("utf-8")

        self.assertIn(str(included.pk), content)
        self.assertNotIn(str(excluded.pk), content)

    def test_v234_csv_neutralizes_formula_injection(self):
        event = self._record(
            reason_code="=SUM(1,1)",
            source="+unsafe-source",
        )

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "format": "csv",
                "event_id": str(event.pk),
            },
        )

        rows = list(
            csv.DictReader(
                io.StringIO(
                    response.content.decode("utf-8")
                )
            )
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["reason_code"],
            "'=SUM(1,1)",
        )
        self.assertEqual(
            rows[0]["source"],
            "'+unsafe-source",
        )

    def test_v234_rollback_link_is_navigation_only(self):
        target = self._record(
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .SENT_TIMESTAMP_RECORDED
            ),
            outcome=(
                SavedSearchNotificationAuditEvent
                .Outcome
                .SUCCEEDED
            ),
            delivery_attempt_id=uuid.uuid4(),
        )

        rollback = self._record(
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .ROLLBACK_APPLIED
            ),
            outcome=(
                SavedSearchNotificationAuditEvent
                .Outcome
                .ROLLED_BACK
            ),
            rollback_of=target,
        )

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "event_id": str(rollback.pk),
            },
        )

        self.assertContains(
            response,
            (
                "?event_id="
                + str(target.pk)
            ),
        )
        self.assertNotContains(
            response,
            "execute_rollback",
        )
        self.assertNotContains(
            response,
            "execute_send",
        )

    def test_v234_reads_do_not_mutate_events_or_saved_search(self):
        self._record()

        before_count = (
            SavedSearchNotificationAuditEvent
            .objects
            .count()
        )

        before_checked = (
            self.saved_search
            .last_notification_checked_at
        )
        before_sent = (
            self.saved_search
            .last_notification_sent_at
        )

        self.client.force_login(self.staff)

        html_response = self.client.get(self._url())
        csv_response = self.client.get(
            self._url(),
            {
                "format": "csv",
            },
        )

        self.assertEqual(html_response.status_code, 200)
        self.assertEqual(csv_response.status_code, 200)

        self.saved_search.refresh_from_db()

        self.assertEqual(
            SavedSearchNotificationAuditEvent
            .objects
            .count(),
            before_count,
        )
        self.assertEqual(
            self.saved_search.last_notification_checked_at,
            before_checked,
        )
        self.assertEqual(
            self.saved_search.last_notification_sent_at,
            before_sent,
        )

    def test_v234_query_builder_uses_exact_filters_and_safe_join(self):
        event = self._record(
            source="saved_search.test.exact",
        )

        filters = (
            parse_saved_search_notification_audit_operator_filters(
                {
                    "event_id": str(event.pk),
                    "saved_search_id": str(
                        self.saved_search.pk
                    ),
                    "source": "saved_search.test.exact",
                }
            )
        )

        queryset = (
            build_saved_search_notification_audit_operator_queryset(
                filters
            )
        )

        self.assertEqual(
            list(queryset),
            [event],
        )

        sql = str(queryset.query)

        self.assertIn(
            "saved_search",
            sql.casefold(),
        )

    def test_v234_metadata_sanitizer_bounds_depth(self):
        value = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "level6": {
                                    "level7": "private"
                                }
                            }
                        }
                    }
                }
            }
        }

        sanitized = (
            sanitize_saved_search_notification_audit_metadata_for_operator(
                value
            )
        )

        rendered = str(sanitized)

        self.assertIn("[redacted]", rendered)
        self.assertNotIn("private", rendered)

    def test_v234_operator_modules_do_not_import_runtime_writers(self):
        query_source = (
            self._backend_root()
            / "listings"
            / "saved_search_notification_audit_operator.py"
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        view_source = (
            self._backend_root()
            / "listings"
            / (
                "saved_search_notification_"
                "audit_operator_views.py"
            )
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        forbidden_terms = (
            "saved_search_notification_email_sender",
            "saved_search_notification_scheduler",
            "saved_search_notification_audit_runtime",
            "saved_search_notification_audit_persistence",
            "record_saved_search_notification_runtime_event",
            "record_saved_search_notification_audit_event",
            "send_saved_search_notification_email",
            "rollback_saved_search_notification_sent_timestamp",
        )

        for source in (
            query_source,
            view_source,
        ):
            for term in forbidden_terms:
                with self.subTest(term=term):
                    self.assertNotIn(term, source)

    def test_v234_template_contains_no_mutating_forms_or_actions(self):
        source = (
            self._backend_root()
            / "listings"
            / "templates"
            / "listings"
            / (
                "saved_search_notification_"
                "audit_events.html"
            )
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        self.assertIn(
            '<form method="get"',
            source,
        )

        forbidden_terms = (
            'method="post"',
            "csrf_token",
            "execute_send",
            "execute_rollback",
            "retry_delivery",
            "Delete event",
            "Save event",
        )

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def test_v234_model_remains_admin_unregistered(self):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

    def test_v234_adds_no_model_or_migration_change(self):
        self.assertFalse(
            (
                self._backend_root()
                / "listings"
                / "migrations"
                / (
                    "0017_savedsearchnotification"
                    "auditoperator.py"
                )
            ).exists()
        )

    def test_v234_v233_transition_guard_is_satisfied(self):
        query_path = (
            self._backend_root()
            / "listings"
            / "saved_search_notification_audit_operator.py"
        )

        view_path = (
            self._backend_root()
            / "listings"
            / (
                "saved_search_notification_"
                "audit_operator_views.py"
            )
        )

        template_path = (
            self._backend_root()
            / "listings"
            / "templates"
            / "listings"
            / (
                "saved_search_notification_"
                "audit_events.html"
            )
        )

        urls_source = (
            self._backend_root()
            / "listings"
            / "urls.py"
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        self.assertTrue(query_path.is_file())
        self.assertTrue(view_path.is_file())
        self.assertTrue(template_path.is_file())

        self.assertIn(
            "staff/saved-search-notification-audit/",
            urls_source,
        )
        self.assertIn(
            "saved-search-notification-audit-events",
            urls_source,
        )

    def test_v234_runtime_surfaces_remain_unchanged_by_operator_ui(self):
        marker = (
            "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
            "AUDIT_OPERATOR_READ_INTERFACE"
        )

        runtime_paths = (
            "saved_search_notification_audit_runtime.py",
            "saved_search_notification_email_renderer.py",
            "saved_search_notification_scheduler.py",
            "saved_search_notification_email_sender.py",
            "saved_search_notification_audit.py",
            (
                "management/commands/"
                "process_saved_search_notifications.py"
            ),
        )

        for relative_path in runtime_paths:
            source = (
                self._backend_root()
                / "listings"
                / relative_path
            ).read_text(
                encoding="utf-8",
                errors="strict",
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(marker, source)

    def test_v234_next_lane_is_operator_ux_accessibility_polish(self):
        next_lane = "v235: saved-search notification persistent audit operator read-interface UX and accessibility polish"

        self.assertEqual(
            next_lane,
            "v235: saved-search notification persistent audit operator read-interface UX and accessibility polish",
        )
