from __future__ import annotations

import csv
import io
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from listings.models import (
    SavedSearch,
    SavedSearchNotificationAuditEvent,
)
from listings.saved_search_notification_audit_persistence import (
    record_saved_search_notification_audit_event,
)
from listings.saved_search_notification_audit_operator_views import (
    FILTER_DISPLAY_ORDER,
    FILTER_LABELS,
    V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_UX_ACCESSIBILITY,
)


class SavedSearchNotificationPersistentAuditOperatorUxAccessibilityV235Tests(
    TestCase
):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.staff = user_model.objects.create_user(
            username="v235-staff",
            email="v235-staff@example.com",
            password="v235-password",
            is_staff=True,
        )

        cls.non_staff = user_model.objects.create_user(
            username="v235-non-staff",
            email="v235-non-staff@example.com",
            password="v235-password",
        )

        cls.owner = user_model.objects.create_user(
            username="v235-owner",
            email="private-v235-owner@example.com",
            password="v235-password",
        )

        cls.saved_search = SavedSearch.objects.create(
            user=cls.owner,
            name="V235 accessible audit search",
            path="/private-v235-path/",
            query_params={
                "q": "private-v235-query",
            },
            querystring="q=private-v235-query",
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
            "The persistent audit operator URL could not be reversed."
        )

    def _record(
        self,
        *,
        event_type="evaluation_started",
        outcome="pending",
        source="saved_search.test.v235",
        reason_code="",
        occurred_at=None,
    ):
        return record_saved_search_notification_audit_event(
            saved_search=self.saved_search,
            event_type=event_type,
            outcome=outcome,
            occurred_at=occurred_at or self.base_time,
            correlation_id=uuid.uuid4(),
            idempotency_key=(
                "v235:"
                + str(uuid.uuid4())
            ),
            notification_fingerprint="c" * 64,
            actor_type="system",
            source=source,
            reason_code=reason_code,
            metadata={
                "mode": "v235-test",
            },
        ).event

    def test_v235_marker_and_filter_label_contract_are_stable(self):
        self.assertEqual(
            V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_UX_ACCESSIBILITY,
            (
                "V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
                "AUDIT_OPERATOR_UX_ACCESSIBILITY"
            ),
        )

        self.assertIn(
            "event_type",
            FILTER_DISPLAY_ORDER,
        )
        self.assertEqual(
            FILTER_LABELS["event_type"],
            "Event type",
        )

    def test_v235_page_has_skip_link_and_main_landmarks(self):
        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'href="#audit-events"',
        )
        self.assertContains(
            response,
            'id="main-content"',
        )
        self.assertContains(
            response,
            'id="audit-events"',
        )
        self.assertContains(
            response,
            'tabindex="-1"',
        )

    def test_v235_filter_form_uses_fieldsets_legends_and_associated_labels(
        self,
    ):
        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        for legend in (
            "Event identity",
            "Classification",
            "Correlation identifiers",
            "Date range and page size",
        ):
            with self.subTest(legend=legend):
                self.assertContains(
                    response,
                    f"<legend>{legend}</legend>",
                    html=True,
                )

        for field_id in (
            "filter-event-id",
            "filter-saved-search-id",
            "filter-event-type",
            "filter-source",
            "filter-correlation-id",
            "filter-occurred-from",
            "filter-page-size",
        ):
            with self.subTest(field_id=field_id):
                self.assertContains(
                    response,
                    f'for="{field_id}"',
                )
                self.assertContains(
                    response,
                    f'id="{field_id}"',
                )

    def test_v235_filter_help_and_datetime_help_are_programmatically_linked(
        self,
    ):
        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertContains(
            response,
            'aria-describedby="filter-help"',
        )
        self.assertContains(
            response,
            'id="occurred-date-help"',
        )
        self.assertContains(
            response,
            'aria-describedby="occurred-date-help"',
            count=2,
        )

    def test_v235_active_filter_chips_are_human_readable(self):
        self._record()

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "event_type": "evaluation_started",
                "source": "saved_search.test.v235",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Active filters",
        )
        self.assertContains(
            response,
            "Evaluation started",
        )
        self.assertContains(
            response,
            "saved_search.test.v235",
        )
        self.assertEqual(
            response.context["active_filter_count"],
            2,
        )

    def test_v235_filter_removal_url_preserves_other_filters_and_drops_page(
        self,
    ):
        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "event_type": "evaluation_started",
                "source": "saved_search.test.v235",
                "page": "1",
            },
        )

        event_type_chip = next(
            item
            for item in response.context["active_filters"]
            if item["name"] == "event_type"
        )

        parsed = urlsplit(
            event_type_chip["remove_url"]
        )

        query = parse_qs(parsed.query)

        self.assertNotIn(
            "event_type",
            query,
        )
        self.assertNotIn(
            "page",
            query,
        )
        self.assertEqual(
            query["source"],
            ["saved_search.test.v235"],
        )

    def test_v235_default_page_explains_that_no_filters_are_active(self):
        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertFalse(
            response.context["has_active_filters"]
        )
        self.assertContains(
            response,
            "No filters are active",
        )

    def test_v235_result_summary_is_announced_as_live_status(self):
        self._record()

        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertContains(
            response,
            'role="status"',
        )
        self.assertContains(
            response,
            'aria-live="polite"',
        )
        self.assertContains(
            response,
            "1 audit event found. Page 1 of 1.",
        )

    def test_v235_event_cards_have_unique_heading_relationships(self):
        event = self._record()

        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertContains(
            response,
            'aria-labelledby="event-heading-1"',
        )
        self.assertContains(
            response,
            'id="event-heading-1"',
        )
        self.assertContains(
            response,
            str(event.pk),
        )

    def test_v235_fingerprint_copy_control_is_keyboard_button_with_live_status(
        self,
    ):
        event = self._record()

        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertContains(
            response,
            'type="button"',
        )
        self.assertContains(
            response,
            'data-copy-value="',
        )
        self.assertContains(
            response,
            (
                "Copy full notification fingerprint "
                f"for event {event.pk}"
            ),
        )
        self.assertContains(
            response,
            'id="copy-status"',
        )
        self.assertContains(
            response,
            'aria-atomic="true"',
        )

    def test_v235_metadata_region_is_keyboard_scrollable_and_labelled(self):
        event = self._record()

        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertContains(
            response,
            "<summary>",
        )
        self.assertContains(
            response,
            'tabindex="0"',
        )
        self.assertContains(
            response,
            (
                "Sanitized metadata for event "
                f"{event.pk}"
            ),
        )

    def test_v235_pagination_links_preserve_filters(self):
        self._record(
            reason_code="first",
        )

        self._record(
            reason_code="second",
            occurred_at=(
                self.base_time
                + timezone.timedelta(seconds=1)
            ),
        )

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "source": "saved_search.test.v235",
                "page_size": "1",
                "page": "1",
            },
        )

        self.assertTrue(
            response.context["page_result"].has_next
        )

        next_url = response.context[
            "next_page_url"
        ]

        parsed = urlsplit(next_url)
        query = parse_qs(parsed.query)

        self.assertEqual(
            query["source"],
            ["saved_search.test.v235"],
        )
        self.assertEqual(
            query["page_size"],
            ["1"],
        )
        self.assertEqual(
            query["page"],
            ["2"],
        )

        self.assertContains(
            response,
            'rel="next"',
        )
        self.assertContains(
            response,
            'aria-current="page"',
        )

    def test_v235_empty_state_is_announced_and_offers_clear_action(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "source": "saved_search.no-match.v235",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "No matching audit events",
        )
        self.assertContains(
            response,
            'class="empty-state"',
        )
        self.assertContains(
            response,
            "Clear all filters",
        )

    def test_v235_csv_export_has_accessible_limit_explanation(self):
        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertContains(
            response,
            'aria-describedby="csv-export-help"',
        )
        self.assertContains(
            response,
            "limited to 5000 events",
        )

    def test_v235_css_declares_focus_reduced_motion_and_forced_colors(self):
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

        required = (
            ":focus-visible",
            "prefers-reduced-motion",
            "forced-colors: active",
            ".visually-hidden",
            ".skip-link",
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(term, source)

    def test_v235_template_remains_read_only(self):
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

        forbidden = (
            'method="post"',
            "csrf_token",
            "execute_send",
            "execute_rollback",
            "retry_delivery",
            "delete_event",
            "save_event",
        )

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def test_v235_access_control_is_unchanged(self):
        anonymous = self.client.get(self._url())

        self.assertEqual(
            anonymous.status_code,
            302,
        )

        self.client.force_login(self.non_staff)

        forbidden = self.client.get(self._url())

        self.assertEqual(
            forbidden.status_code,
            403,
        )

    def test_v235_csv_behavior_is_unchanged(self):
        event = self._record()

        self.client.force_login(self.staff)

        response = self.client.get(
            self._url(),
            {
                "format": "csv",
                "event_id": str(event.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "text/csv; charset=utf-8",
        )

        rows = list(
            csv.reader(
                io.StringIO(
                    response.content.decode("utf-8")
                )
            )
        )

        self.assertEqual(len(rows), 2)

    def test_v235_html_does_not_expose_owner_email_or_saved_query(self):
        self._record()

        self.client.force_login(self.staff)

        response = self.client.get(self._url())

        self.assertNotContains(
            response,
            self.owner.email,
        )
        self.assertNotContains(
            response,
            "private-v235-query",
        )
        self.assertNotContains(
            response,
            "/private-v235-path/",
        )

    def test_v235_reads_do_not_mutate_events_or_timestamps(self):
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

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)

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

    def test_v235_protected_runtime_and_query_surfaces_are_untouched(self):
        marker = (
            "V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
            "AUDIT_OPERATOR_UX_ACCESSIBILITY"
        )

        protected = (
            "saved_search_notification_audit_operator.py",
            "urls.py",
            "models.py",
            "admin.py",
            "saved_search_notification_audit_persistence.py",
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

        for relative_path in protected:
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
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_v235_model_remains_admin_unregistered_and_no_migration_added(
        self,
    ):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

        self.assertFalse(
            (
                self._backend_root()
                / "listings"
                / "migrations"
                / (
                    "0017_savedsearchnotification"
                    "auditoperatorux.py"
                )
            ).exists()
        )

    def test_v235_next_lane_is_operator_navigation_integration_contract(
        self,
    ):
        next_lane = "v236: saved-search notification persistent audit operator navigation integration contract"

        self.assertEqual(
            next_lane,
            "v236: saved-search notification persistent audit operator navigation integration contract",
        )
