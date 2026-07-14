from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearchNotificationAuditEvent


V240_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CLOSEOUT_AUDIT = (
    "V240_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_"
    "SHARED_SHELL_INTEGRATION_CLOSEOUT_AUDIT"
)

V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION = (
    "V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_"
    "SHARED_SHELL_INTEGRATION"
)

V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CONTRACT = (
    "V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_"
    "SHARED_SHELL_INTEGRATION_CONTRACT"
)

BASE_TEMPLATE_PATH = "templates/base.html"

OPERATOR_TEMPLATE_PATH = (
    "listings/templates/listings/"
    "saved_search_notification_audit_events.html"
)

OPERATOR_URL_NAME = (
    "listings:saved-search-notification-audit-events"
)

OPERATOR_URL_PATH = (
    "/staff/saved-search-notification-audit/"
)

V239_TEST_PATH = (
    "listings/"
    "test_saved_search_notification_persistent_audit_operator_"
    "shared_shell_integration_v239.py"
)

HISTORICAL_TEST_PATHS = (
    "listings/test_saved_search_notification_persistent_audit_operator_read_interface_v234.py",
    "listings/test_saved_search_notification_persistent_audit_operator_read_interface_ux_accessibility_v235.py",
    "listings/test_saved_search_notification_persistent_audit_operator_navigation_integration_contract_v236.py",
    "listings/test_saved_search_notification_persistent_audit_operator_navigation_integration_v237.py",
    "listings/test_saved_search_notification_persistent_audit_operator_shared_shell_integration_contract_v238.py",
    V239_TEST_PATH,
)

PROTECTED_BACKEND_PATHS = (
    BASE_TEMPLATE_PATH,
    OPERATOR_TEMPLATE_PATH,
    "listings/saved_search_notification_audit_operator.py",
    "listings/saved_search_notification_audit_operator_views.py",
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

CLOSEOUT_GATES = (
    "v238 contract remains packaged",
    "v239 implementation remains packaged",
    "operator extends base.html",
    "operator uses the shared content block",
    "child owns no doctype html head body or main",
    "rendered page owns one document shell and one main landmark",
    "page-header region is unique",
    "main-content target is unique",
    "audit-events target is unique",
    "shared Notification audit navigation remains active",
    "query parameters do not change navigation active state",
    "staff-only authorization remains unchanged",
    "GET and HEAD remain allowed",
    "POST PUT PATCH and DELETE remain disallowed",
    "operator template remains read-only",
    "private saved-search payload remains absent",
    "v235 accessibility behavior remains packaged",
    "page-specific CSS remains scoped",
    "fingerprint copy JavaScript remains packaged",
    "model admin migration query runtime and delivery remain unchanged",
    "no migration 0017 exists",
    "full regression remains green",
)

NEXT_CHECKPOINT = (
    "v241: saved-search notification production delivery implementation contract"
)


class _RenderedShellParser(HTMLParser):
    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.declarations = []
        self.start_tags = []
        self.anchors = []
        self._active_anchor = None

    def handle_decl(self, decl):
        self.declarations.append(
            decl.casefold()
        )

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        normalized_tag = tag.casefold()
        normalized_attrs = dict(attrs)

        self.start_tags.append(
            (
                normalized_tag,
                normalized_attrs,
            )
        )

        if normalized_tag == "a":
            self._active_anchor = {
                "attrs": normalized_attrs,
                "text": [],
            }

    def handle_data(self, data):
        if self._active_anchor is None:
            return

        self._active_anchor["text"].append(
            data
        )

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


class SavedSearchNotificationPersistentAuditOperatorSharedShellIntegrationCloseoutAuditV240Tests(
    TestCase
):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.staff = user_model.objects.create_user(
            username="v240-staff",
            email="v240-staff@example.com",
            password="v240-password",
            is_staff=True,
        )

        cls.non_staff = user_model.objects.create_user(
            username="v240-non-staff",
            email="v240-non-staff@example.com",
            password="v240-password",
        )

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _read_backend_path(
        self,
        relative_path: str,
    ) -> str:
        return (
            self._backend_root()
            / relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def _base_source(self) -> str:
        return self._read_backend_path(
            BASE_TEMPLATE_PATH
        )

    def _operator_source(self) -> str:
        return self._read_backend_path(
            OPERATOR_TEMPLATE_PATH
        )

    def _url(self) -> str:
        return reverse(
            OPERATOR_URL_NAME
        )

    def _parse(
        self,
        html_source: str,
    ) -> _RenderedShellParser:
        parser = _RenderedShellParser()
        parser.feed(
            html_source
        )
        return parser

    def _staff_response(
        self,
        query: dict | None = None,
    ):
        self.client.force_login(
            self.staff
        )

        return self.client.get(
            self._url(),
            query or {},
        )

    def _tag_count(
        self,
        parser: _RenderedShellParser,
        tag: str,
    ) -> int:
        return sum(
            1
            for parsed_tag, _attrs in parser.start_tags
            if parsed_tag == tag
        )

    def _notification_audit_anchors(
        self,
        parser: _RenderedShellParser,
    ):
        expected_href = self._url()

        return [
            anchor
            for anchor in parser.anchors
            if (
                anchor["attrs"].get("href")
                == expected_href
                and anchor["text"]
                == "Notification audit"
            )
        ]

    def test_v240_marker_is_stable(self):
        self.assertEqual(
            V240_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CLOSEOUT_AUDIT,
            (
                "V240_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
                "AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_"
                "CLOSEOUT_AUDIT"
            ),
        )

    def test_v240_operator_named_route_is_stable(self):
        self.assertEqual(
            self._url(),
            OPERATOR_URL_PATH,
        )

    def test_v240_v238_and_v239_packages_remain_present(self):
        for relative_path in HISTORICAL_TEST_PATHS:
            with self.subTest(
                relative_path=relative_path
            ):
                self.assertTrue(
                    (
                        self._backend_root()
                        / relative_path
                    ).is_file()
                )

        v238_source = self._read_backend_path(
            HISTORICAL_TEST_PATHS[-2]
        )

        v239_source = self._read_backend_path(
            HISTORICAL_TEST_PATHS[-1]
        )

        self.assertIn(
            V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CONTRACT,
            v238_source,
        )

        self.assertIn(
            V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION,
            v239_source,
        )

    def test_v240_operator_source_keeps_shared_shell_contract(self):
        source = self._operator_source()

        self.assertTrue(
            source.lstrip().startswith(
                '{% extends "base.html" %}'
            )
        )

        self.assertEqual(
            len(
                re.findall(
                    (
                        r"{%\s*extends\s+"
                        r"[\"']base\.html[\"']\s*%}"
                    ),
                    source,
                )
            ),
            1,
        )

        self.assertEqual(
            len(
                re.findall(
                    r"{%\s*block\s+content\s*%}",
                    source,
                )
            ),
            1,
        )

        self.assertEqual(
            source.count(
                V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION
            ),
            1,
        )

    def test_v240_child_owns_no_document_or_landmark_shell(self):
        source = self._operator_source()

        self.assertNotIn(
            "<!doctype html",
            source.casefold(),
        )

        for tag in (
            "html",
            "head",
            "body",
            "main",
            "header",
        ):
            with self.subTest(tag=tag):
                self.assertIsNone(
                    re.search(
                        rf"<\s*/?\s*{tag}\b",
                        source,
                        flags=re.IGNORECASE,
                    )
                )

    def test_v240_source_targets_and_regions_are_unique(self):
        source = self._operator_source()

        for term in (
            'id="main-content"',
            'data-v239-region="page-header"',
            'href="#audit-events"',
            'id="audit-events"',
        ):
            with self.subTest(term=term):
                self.assertEqual(
                    source.count(term),
                    1,
                )

        self.assertIn(
            'tabindex="-1"',
            source,
        )

        self.assertIn(
            'class="event-heading"',
            source,
        )

    def test_v240_page_css_and_copy_script_remain_packaged(self):
        source = self._operator_source()

        required = (
            ".saved-search-audit-page",
            ":focus-visible",
            "prefers-reduced-motion",
            "forced-colors: active",
            "navigator.clipboard",
            "copy-status",
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

    def test_v240_operator_source_remains_read_only(self):
        source = self._operator_source()
        folded = source.casefold()

        get_form = re.search(
            (
                r"<form\b"
                r"(?=[^>]*\bmethod\s*=\s*[\"']get[\"'])"
                r"[^>]*>"
            ),
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )

        self.assertIsNotNone(
            get_form
        )

        post_form = re.search(
            (
                r"<form\b"
                r"(?=[^>]*\bmethod\s*=\s*[\"']post[\"'])"
                r"[^>]*>"
            ),
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )

        self.assertIsNone(
            post_form
        )

        self.assertNotIn(
            "{% csrf_token %}",
            folded,
        )

        mutation_control = re.search(
            (
                r"<(?:form|button|input|a)\b[^>]*"
                r"(?:data-action|name|value|formaction|href)"
                r"\s*=\s*[\"'][^\"']*"
                r"(?:execute_send|retry_delivery|"
                r"delete_event|save_event)"
                r"[^\"']*[\"'][^>]*>"
            ),
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )

        self.assertIsNone(
            mutation_control
        )

    def test_v240_base_navigation_contract_remains_packaged(self):
        source = self._base_source()

        required = (
            "V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION",
            (
                "{% url "
                "'listings:saved-search-notification-audit-events' "
                "%}"
            ),
            ">Notification audit</a>",
            "saved-search-notification-audit-events",
            'class="active"',
            'aria-current="page"',
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

        self.assertNotIn(
            OPERATOR_URL_PATH,
            source,
        )

    def test_v240_rendered_page_has_one_document_shell_and_main(self):
        response = self._staff_response()

        self.assertEqual(
            response.status_code,
            200,
        )

        parser = self._parse(
            response.content.decode("utf-8")
        )

        self.assertEqual(
            sum(
                1
                for decl in parser.declarations
                if decl == "doctype html"
            ),
            1,
        )

        for tag in (
            "html",
            "head",
            "body",
            "main",
        ):
            with self.subTest(tag=tag):
                self.assertEqual(
                    self._tag_count(
                        parser,
                        tag,
                    ),
                    1,
                )

    def test_v240_rendered_targets_and_page_header_are_unique(self):
        response = self._staff_response()

        parser = self._parse(
            response.content.decode("utf-8")
        )

        main_content = [
            attrs
            for tag, attrs in parser.start_tags
            if attrs.get("id") == "main-content"
        ]

        page_headers = [
            attrs
            for tag, attrs in parser.start_tags
            if (
                tag == "div"
                and attrs.get(
                    "data-v239-region"
                )
                == "page-header"
            )
        ]

        audit_targets = [
            attrs
            for tag, attrs in parser.start_tags
            if attrs.get("id") == "audit-events"
        ]

        self.assertEqual(
            len(main_content),
            1,
        )

        self.assertEqual(
            len(page_headers),
            1,
        )

        self.assertEqual(
            len(audit_targets),
            1,
        )

        self.assertEqual(
            audit_targets[0].get("tabindex"),
            "-1",
        )

    def test_v240_shared_navigation_is_active(self):
        response = self._staff_response()

        parser = self._parse(
            response.content.decode("utf-8")
        )

        anchors = self._notification_audit_anchors(
            parser
        )

        self.assertEqual(
            len(anchors),
            1,
        )

        classes = (
            anchors[0]["attrs"]
            .get("class", "")
            .split()
        )

        self.assertIn(
            "active",
            classes,
        )

        self.assertEqual(
            anchors[0]["attrs"].get(
                "aria-current"
            ),
            "page",
        )

    def test_v240_navigation_active_state_ignores_querystring(self):
        response = self._staff_response(
            {
                "event_type": "delivery_failed",
                "page": "1",
            }
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        parser = self._parse(
            response.content.decode("utf-8")
        )

        anchors = self._notification_audit_anchors(
            parser
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

    def test_v240_access_control_and_safe_methods_are_unchanged(self):
        anonymous_response = self.client.get(
            self._url()
        )

        self.assertEqual(
            anonymous_response.status_code,
            302,
        )

        self.client.force_login(
            self.non_staff
        )

        non_staff_response = self.client.get(
            self._url()
        )

        self.assertEqual(
            non_staff_response.status_code,
            403,
        )

        self.client.force_login(
            self.staff
        )

        self.assertEqual(
            self.client.get(
                self._url()
            ).status_code,
            200,
        )

        self.assertEqual(
            self.client.head(
                self._url()
            ).status_code,
            200,
        )

    def test_v240_mutation_methods_remain_disallowed(self):
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
                    self._url(),
                    data="{}",
                    content_type="application/json",
                )

                self.assertEqual(
                    response.status_code,
                    405,
                )

    def test_v240_private_saved_search_payload_is_not_rendered(self):
        response = self._staff_response()

        html_source = response.content.decode(
            "utf-8"
        )

        forbidden = (
            "owner_email",
            "recipient_email",
            "saved_search_query",
            "query_params",
            "email_body",
            "email_subject",
        )

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(
                    term,
                    html_source,
                )

    def test_v240_accessibility_controls_remain_rendered(self):
        response = self._staff_response()

        html_source = response.content.decode(
            "utf-8"
        )

        required = (
            'href="#audit-events"',
            'id="audit-events"',
            'tabindex="-1"',
            'id="copy-status"',
            'aria-live="polite"',
            "Download bounded CSV",
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    html_source,
                )

    def test_v240_model_admin_and_migration_boundary_is_closed(self):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

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

    def test_v240_marker_does_not_leak_into_protected_surfaces(self):
        for relative_path in PROTECTED_BACKEND_PATHS:
            source = self._read_backend_path(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    V240_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CLOSEOUT_AUDIT,
                    source,
                )

    def test_v240_closeout_gate_matrix_is_complete(self):
        required = {
            "v238 contract remains packaged",
            "v239 implementation remains packaged",
            "operator extends base.html",
            "child owns no doctype html head body or main",
            "rendered page owns one document shell and one main landmark",
            "shared Notification audit navigation remains active",
            "staff-only authorization remains unchanged",
            "GET and HEAD remain allowed",
            "POST PUT PATCH and DELETE remain disallowed",
            "operator template remains read-only",
            "private saved-search payload remains absent",
            "model admin migration query runtime and delivery remain unchanged",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(
                    CLOSEOUT_GATES
                )
            )
        )

    def test_v240_next_lane_is_production_delivery_contract(self):
        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v241: saved-search notification production "
                "delivery implementation contract"
            ),
        )
