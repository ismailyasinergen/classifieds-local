from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse

from listings.models import SavedSearchNotificationAuditEvent


V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION = (
    "V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION"
)

NAVIGATION_TEMPLATE_PATH = (
    "templates/base.html"
)

OPERATOR_URL_NAME = (
    "listings:saved-search-notification-audit-events"
)

OPERATOR_URL_PATH = (
    "/staff/saved-search-notification-audit/"
)

OPERATOR_LABEL = (
    "Notification audit"
)

OPERATOR_ARIA_LABEL = (
    "Inspect saved-search notification audit events"
)

NEXT_CHECKPOINT = (
    "v238: saved-search notification persistent audit operator shared-shell integration contract"
)


class _AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.anchors = []
        self._active_anchor = None

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        if tag.casefold() != "a":
            return

        self._active_anchor = {
            "attrs": dict(attrs),
            "text": [],
        }

    def handle_data(self, data):
        if self._active_anchor is None:
            return

        self._active_anchor["text"].append(data)

    def handle_endtag(self, tag):
        if (
            tag.casefold() != "a"
            or self._active_anchor is None
        ):
            return

        self._active_anchor["text"] = " ".join(
            "".join(
                self._active_anchor["text"]
            ).split()
        )

        self.anchors.append(
            self._active_anchor
        )

        self._active_anchor = None


class SavedSearchNotificationPersistentAuditOperatorNavigationIntegrationV237Tests(
    TestCase
):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.staff = user_model.objects.create_user(
            username="v237-staff",
            email="v237-staff@example.com",
            password="v237-password",
            is_staff=True,
        )

        cls.superuser = user_model.objects.create_superuser(
            username="v237-superuser",
            email="v237-superuser@example.com",
            password="v237-password",
        )

        cls.non_staff = user_model.objects.create_user(
            username="v237-non-staff",
            email="v237-non-staff@example.com",
            password="v237-password",
        )

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _navigation_source(self) -> str:
        return (
            self._backend_root()
            / NAVIGATION_TEMPLATE_PATH
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def _operator_url(self) -> str:
        return reverse(
            OPERATOR_URL_NAME
        )

    def _collect_anchors(
        self,
        html_source: str,
    ):
        parser = _AnchorCollector()
        parser.feed(html_source)
        return parser.anchors

    def _operator_anchors(
        self,
        html_source: str,
    ):
        expected_href = self._operator_url()

        return [
            anchor
            for anchor in self._collect_anchors(
                html_source
            )
            if anchor["attrs"].get("href")
            == expected_href
        ]

    def _render_base(
        self,
        *,
        user,
        path: str,
    ) -> str:
        request = RequestFactory().get(path)
        request.user = user
        request.resolver_match = resolve(
            path.split("?", 1)[0]
        )

        return render_to_string(
            "base.html",
            {
                "request": request,
                "user": user,
                "messages": (),
            },
        )

    def test_v237_marker_is_stable(self):
        self.assertEqual(
            V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION,
            (
                "V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
                "AUDIT_OPERATOR_NAVIGATION_INTEGRATION"
            ),
        )

    def test_v237_named_route_is_stable(self):
        self.assertEqual(
            self._operator_url(),
            OPERATOR_URL_PATH,
        )

    def test_v237_source_contains_one_named_link(self):
        source = self._navigation_source()

        self.assertEqual(
            source.count(
                V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION
            ),
            1,
        )

        self.assertEqual(
            source.count(
                (
                    "{% url "
                    "'listings:saved-search-notification-audit-events' "
                    "%}"
                )
            ),
            1,
        )

        self.assertEqual(
            source.count(
                ">Notification audit</a>"
            ),
            1,
        )

    def test_v237_source_does_not_hardcode_path(self):
        self.assertNotIn(
            OPERATOR_URL_PATH,
            self._navigation_source(),
        )

    def test_v237_link_follows_audit_tracking(self):
        source = self._navigation_source()

        tracking_position = source.index(
            '<a href="{{ nav_audit_url }}">'
            "Audit Tracking"
            "</a>"
        )

        notification_position = source.index(
            ">Notification audit</a>"
        )

        self.assertLess(
            tracking_position,
            notification_position,
        )

    def test_v237_link_is_after_admin_tools_staff_guard(self):
        source = self._navigation_source()

        link_position = source.index(
            ">Notification audit</a>"
        )

        marker_position = source.index(
            "ADMIN_NAV_GROUPED_TOOLBAR_V99"
        )

        admin_positions = [
            marker_position + match.start()
            for match in re.finditer(
                re.escape("Admin tools"),
                source[
                    marker_position:
                    link_position
                ],
            )
        ]

        self.assertTrue(
            admin_positions
        )

        admin_position = admin_positions[-1]

        staff_position = source.rfind(
            "is_staff",
            0,
            admin_position,
        )

        self.assertGreaterEqual(
            staff_position,
            0,
        )

        self.assertLess(
            staff_position,
            admin_position,
        )

        self.assertLess(
            admin_position,
            link_position,
        )

    def test_v237_staff_sees_one_link(self):
        self.client.force_login(
            self.staff
        )

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        anchors = self._operator_anchors(
            response.content.decode("utf-8")
        )

        self.assertEqual(
            len(anchors),
            1,
        )

        self.assertEqual(
            anchors[0]["text"],
            OPERATOR_LABEL,
        )

        self.assertEqual(
            anchors[0]["attrs"].get("aria-label"),
            OPERATOR_ARIA_LABEL,
        )

    def test_v237_superuser_sees_one_link(self):
        self.client.force_login(
            self.superuser
        )

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(
                self._operator_anchors(
                    response.content.decode("utf-8")
                )
            ),
            1,
        )

    def test_v237_non_staff_does_not_see_link(self):
        self.client.force_login(
            self.non_staff
        )

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            self._operator_anchors(
                response.content.decode("utf-8")
            ),
            [],
        )

    def test_v237_anonymous_does_not_see_link(self):
        response = self.client.get(
            reverse("pages:home")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            self._operator_anchors(
                response.content.decode("utf-8")
            ),
            [],
        )

    def test_v237_inactive_state_has_no_aria_current(self):
        html_source = self._render_base(
            user=self.staff,
            path=reverse(
                "accounts:dashboard"
            ),
        )

        anchors = self._operator_anchors(
            html_source
        )

        self.assertEqual(
            len(anchors),
            1,
        )

        self.assertNotEqual(
            anchors[0]["attrs"].get(
                "aria-current"
            ),
            "page",
        )

        self.assertNotIn(
            "active",
            (
                anchors[0]["attrs"].get(
                    "class"
                )
                or ""
            ).split(),
        )

    def test_v237_active_state_has_class_and_aria_current(self):
        html_source = self._render_base(
            user=self.staff,
            path=self._operator_url(),
        )

        anchors = self._operator_anchors(
            html_source
        )

        self.assertEqual(
            len(anchors),
            1,
        )

        self.assertEqual(
            anchors[0]["attrs"].get(
                "aria-current"
            ),
            "page",
        )

        self.assertIn(
            "active",
            (
                anchors[0]["attrs"].get(
                    "class"
                )
                or ""
            ).split(),
        )

    def test_v237_active_state_ignores_querystring(self):
        html_source = self._render_base(
            user=self.staff,
            path=(
                self._operator_url()
                + "?event_type=delivery_failed&page=2"
            ),
        )

        anchors = self._operator_anchors(
            html_source
        )

        self.assertEqual(
            len(anchors),
            1,
        )

        self.assertEqual(
            anchors[0]["attrs"].get(
                "aria-current"
            ),
            "page",
        )

    def test_v237_link_fragment_contains_no_counts_or_private_data(
        self,
    ):
        source = self._navigation_source()

        marker_position = source.index(
            V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION
        )

        link_end = source.index(
            "</a>",
            marker_position,
        ) + len("</a>")

        fragment = source[
            marker_position:
            link_end
        ].casefold()

        forbidden = (
            "event_count",
            "failure_count",
            "pending_count",
            "badge",
            "recipient",
            "owner_id",
            "correlation_id",
            "metadata",
            "notification content",
        )

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(
                    term,
                    fragment,
                )

    def test_v237_link_fragment_contains_no_mutation_action(
        self,
    ):
        source = self._navigation_source()

        marker_position = source.index(
            V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION
        )

        link_end = source.index(
            "</a>",
            marker_position,
        ) + len("</a>")

        fragment = source[
            marker_position:
            link_end
        ].casefold()

        forbidden = (
            'method="post"',
            "csrf_token",
            "execute_send",
            "retry",
            "rollback",
            "delete",
            "update",
        )

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(
                    term,
                    fragment,
                )

    def test_v237_target_authorization_is_unchanged(self):
        anonymous = self.client.get(
            self._operator_url()
        )

        self.assertEqual(
            anonymous.status_code,
            302,
        )

        self.client.force_login(
            self.non_staff
        )

        forbidden = self.client.get(
            self._operator_url()
        )

        self.assertEqual(
            forbidden.status_code,
            403,
        )

        self.client.force_login(
            self.staff
        )

        allowed = self.client.get(
            self._operator_url()
        )

        self.assertEqual(
            allowed.status_code,
            200,
        )

    def test_v237_target_remains_get_head_only(self):
        self.client.force_login(
            self.staff
        )

        for method_name in (
            "post",
            "put",
            "patch",
            "delete",
        ):
            with self.subTest(
                method_name=method_name
            ):
                response = getattr(
                    self.client,
                    method_name,
                )(
                    self._operator_url(),
                    data="{}",
                    content_type="application/json",
                )

                self.assertEqual(
                    response.status_code,
                    405,
                )

    def test_v237_existing_navigation_labels_remain(self):
        source = self._navigation_source()

        self.assertIn(
            "ADMIN_NAV_GROUPED_TOOLBAR_V99",
            source,
        )

        self.client.force_login(
            self.staff
        )

        response = self.client.get(
            reverse("accounts:dashboard")
        )

        for term in (
            "Admin tools",
            "Overview",
            "Appeals",
            "Listing Reports",
            "Seller Reports",
            "Action Log",
            "Event Log",
            "Audit Tracking",
            "Notification audit",
        ):
            with self.subTest(term=term):
                self.assertContains(
                    response,
                    term,
                )

    def test_v237_protected_surfaces_do_not_receive_marker(
        self,
    ):
        marker = (
            "V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
            "AUDIT_OPERATOR_NAVIGATION_INTEGRATION"
        )

        protected = (
            "listings/saved_search_notification_audit_operator.py",
            "listings/saved_search_notification_audit_operator_views.py",
            (
                "listings/templates/listings/"
                "saved_search_notification_audit_events.html"
            ),
            "listings/urls.py",
            "listings/models.py",
            "listings/admin.py",
            "listings/saved_search_notification_audit_persistence.py",
            "listings/saved_search_notification_audit_runtime.py",
            "listings/saved_search_notification_email_renderer.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/saved_search_notification_email_sender.py",
            "listings/saved_search_notification_audit.py",
            (
                "listings/management/commands/"
                "process_saved_search_notifications.py"
            ),
        )

        for relative_path in protected:
            source = (
                self._backend_root()
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

    def test_v237_model_remains_admin_unregistered(self):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

    def test_v237_no_migration_0017_exists(self):
        migration_directory = (
            self._backend_root()
            / "listings"
            / "migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "0017*"
                )
            ),
            [],
        )

    def test_v237_next_checkpoint_is_shared_shell_contract(
        self,
    ):
        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v238: saved-search notification persistent audit operator shared-shell integration contract"
            ),
        )
