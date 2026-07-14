from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearchNotificationAuditEvent


V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION = "V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION"

OPERATOR_TEMPLATE_PATH = (
    "listings/templates/listings/"
    "saved_search_notification_audit_events.html"
)

BASE_TEMPLATE_PATH = (
    "templates/base.html"
)

OPERATOR_URL_NAME = (
    "listings:saved-search-notification-audit-events"
)

OPERATOR_URL_PATH = (
    "/staff/saved-search-notification-audit/"
)

PAGE_SCOPE = (
    "saved-search-audit-page"
)

NEXT_CHECKPOINT = "v240: saved-search notification persistent audit operator shared-shell integration closeout audit"


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
        if self._active_anchor is not None:
            self._active_anchor["text"].append(
                data
            )

    def handle_endtag(self, tag):
        if (
            tag.casefold() == "a"
            and self._active_anchor is not None
        ):
            self._active_anchor["text"] = " ".join(
                "".join(
                    self._active_anchor["text"]
                ).split()
            )

            self.anchors.append(
                self._active_anchor
            )

            self._active_anchor = None


class SavedSearchNotificationPersistentAuditOperatorSharedShellIntegrationV239Tests(
    TestCase
):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.staff = user_model.objects.create_user(
            username="v239-staff",
            email="v239-staff@example.com",
            password="v239-password",
            is_staff=True,
        )

        cls.superuser = user_model.objects.create_superuser(
            username="v239-superuser",
            email="v239-superuser@example.com",
            password="v239-password",
        )

        cls.non_staff = user_model.objects.create_user(
            username="v239-non-staff",
            email="v239-non-staff@example.com",
            password="v239-password",
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

    def _operator_source(self) -> str:
        return self._read_backend_path(
            OPERATOR_TEMPLATE_PATH
        )

    def _base_source(self) -> str:
        return self._read_backend_path(
            BASE_TEMPLATE_PATH
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
        parser.feed(html_source)
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

    def test_v239_marker_is_stable(self):
        self.assertEqual(
            V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION,
            (
                "V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
                "AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION"
            ),
        )

    def test_v239_operator_route_remains_stable(self):
        self.assertEqual(
            self._url(),
            OPERATOR_URL_PATH,
        )

    def test_v239_template_extends_base_and_uses_content_block(self):
        source = self._operator_source()

        self.assertTrue(
            source.lstrip().startswith(
                '{% extends "base.html" %}'
            )
        )

        self.assertEqual(
            len(
                re.findall(
                    r"{%\s*extends\s+[\"']base\.html[\"']\s*%}",
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
            len(
                re.findall(
                    r"{%\s*endblock\s*%}",
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

    def test_v239_child_owns_no_document_or_main_shell(self):
        folded = self._operator_source().casefold()

        for forbidden in (
            "<!doctype html",
            "<html",
            "</html",
            "<head",
            "</head",
            "<body",
            "</body",
            "<main",
            "</main",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    folded,
                )

    def test_v239_main_content_uses_scoped_non_main_wrapper(self):
        source = self._operator_source()

        wrapper = re.search(
            (
                r"<div\b"
                r"(?=[^>]*\bid=[\"']main-content[\"'])"
                r"(?=[^>]*\bclass=[\"'][^\"']*"
                r"saved-search-audit-page[^\"']*[\"'])"
                r"[^>]*>"
            ),
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )

        self.assertIsNotNone(
            wrapper
        )

    def test_v239_page_header_uses_non_document_region(self):
        source = self._operator_source()

        self.assertIn(
            'data-v239-region="page-header"',
            source,
        )

        self.assertEqual(
            source.count(
                'data-v239-region="page-header"'
            ),
            1,
        )

        self.assertIn(
            'class="event-heading"',
            source,
        )

        self.assertIsNone(
            re.search(
                r"<header\b",
                source,
                flags=re.IGNORECASE,
            )
        )

        response = self._staff_response()

        self.assertEqual(
            response.status_code,
            200,
        )

        parser = self._parse(
            response.content.decode("utf-8")
        )

        regions = [
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

        self.assertEqual(
            len(regions),
            1,
        )

    def test_v239_css_and_script_are_preserved_and_scoped(self):
        source = self._operator_source()

        self.assertEqual(
            len(
                re.findall(
                    r"<style\b",
                    source,
                    flags=re.IGNORECASE,
                )
            ),
            1,
        )

        self.assertEqual(
            len(
                re.findall(
                    r"<script\b",
                    source,
                    flags=re.IGNORECASE,
                )
            ),
            1,
        )

        required = (
            ".saved-search-audit-page",
            ":focus-visible",
            "prefers-reduced-motion",
            "forced-colors: active",
            ".visually-hidden",
            ".skip-link",
            "navigator.clipboard",
            "copy-status",
            "Fingerprint could not be copied.",
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

        for unscoped_root in (
            r"(?m)^\s*:root\s*\{",
            r"(?m)^\s*body\s*\{",
            r"(?m)^\s*main\s*\{",
        ):
            with self.subTest(
                unscoped_root=unscoped_root
            ):
                self.assertNotRegex(
                    source,
                    unscoped_root,
                )

    def test_v239_base_template_remains_unchanged_by_marker(self):
        source = self._base_source()

        self.assertNotIn(
            V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION,
            source,
        )

        self.assertIn(
            "V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION",
            source,
        )

    def test_v239_staff_page_has_one_document_shell_and_one_main(self):
        response = self._staff_response()

        self.assertEqual(
            response.status_code,
            200,
        )

        parser = self._parse(
            response.content.decode("utf-8")
        )

        self.assertEqual(
            parser.declarations.count("doctype html"),
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
                    sum(
                        1
                        for parsed_tag, _
                        in parser.start_tags
                        if parsed_tag == tag
                    ),
                    1,
                )

    def test_v239_staff_page_renders_shared_admin_navigation(self):
        response = self._staff_response()
        html_source = response.content.decode(
            "utf-8"
        )

        for term in (
            "Admin tools",
            "Audit Tracking",
            "Notification audit",
        ):
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    html_source,
                )

    def test_v239_notification_audit_navigation_is_active(self):
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

    def test_v239_navigation_active_state_ignores_querystring(self):
        response = self._staff_response(
            {
                "event_type": "delivery_failed",
                "page_size": "25",
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

    def test_v239_accessibility_targets_are_preserved(self):
        response = self._staff_response()
        parser = self._parse(
            response.content.decode("utf-8")
        )

        main_content_elements = [
            (
                tag,
                attrs,
            )
            for tag, attrs in parser.start_tags
            if attrs.get("id") == "main-content"
        ]

        audit_event_elements = [
            (
                tag,
                attrs,
            )
            for tag, attrs in parser.start_tags
            if attrs.get("id") == "audit-events"
        ]

        self.assertEqual(
            len(main_content_elements),
            1,
        )

        self.assertNotEqual(
            main_content_elements[0][0],
            "main",
        )

        self.assertEqual(
            len(audit_event_elements),
            1,
        )

        self.assertEqual(
            audit_event_elements[0][1].get(
                "tabindex"
            ),
            "-1",
        )

        skip_links = [
            anchor
            for anchor in parser.anchors
            if (
                anchor["attrs"].get("href")
                == "#audit-events"
            )
        ]

        self.assertEqual(
            len(skip_links),
            1,
        )

    def test_v239_existing_filter_and_copy_ux_remains_rendered(self):
        response = self._staff_response()
        html_source = response.content.decode(
            "utf-8"
        )

        required = (
            "Read-only staff interface",
            'method="get"',
            "Apply filters",
            "Download bounded CSV",
            'id="copy-status"',
            'aria-live="polite"',
            "No filters are active",
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    html_source,
                )

    def test_v239_template_remains_read_only(self):
        source = self._operator_source()

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

        folded = source.casefold()

        forbidden = (
            "csrf_token",
            "execute_send",
            "execute_rollback",
            "retry_delivery",
            "delete_event",
            "save_event",
        )

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(
                    term,
                    folded,
                )

    def test_v239_access_control_is_unchanged(self):
        anonymous = self.client.get(
            self._url()
        )

        self.assertEqual(
            anonymous.status_code,
            302,
        )

        self.client.force_login(
            self.non_staff
        )

        forbidden = self.client.get(
            self._url()
        )

        self.assertEqual(
            forbidden.status_code,
            403,
        )

        self.client.force_login(
            self.superuser
        )

        allowed = self.client.get(
            self._url()
        )

        self.assertEqual(
            allowed.status_code,
            200,
        )

    def test_v239_mutation_methods_remain_disallowed(self):
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

    def test_v239_private_saved_search_details_are_not_exposed(self):
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

    def test_v239_protected_surfaces_do_not_receive_marker(self):
        protected = (
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

        for relative_path in protected:
            source = self._read_backend_path(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION,
                    source,
                )

    def test_v239_model_admin_and_migration_boundary_is_unchanged(
        self,
    ):
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

    def test_v239_v238_transition_contract_is_satisfied(self):
        source = self._operator_source()

        self.assertIn(
            V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION,
            source,
        )

        self.assertRegex(
            source,
            r"{%\s*extends\s+[\"']base\.html[\"']\s*%}",
        )

        self.assertRegex(
            source,
            r"{%\s*block\s+content\s*%}",
        )

    def test_v239_next_lane_is_shared_shell_closeout_audit(self):
        self.assertEqual(
            NEXT_CHECKPOINT,
            "v240: saved-search notification persistent audit operator shared-shell integration closeout audit",
        )
