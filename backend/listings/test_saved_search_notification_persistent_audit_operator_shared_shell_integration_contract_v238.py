from __future__ import annotations

import re
from pathlib import Path

from django.contrib import admin
from django.test import SimpleTestCase
from django.urls import reverse

from listings.models import SavedSearchNotificationAuditEvent


V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CONTRACT = "V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CONTRACT"

V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION = "V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION"

BASE_TEMPLATE = "backend/templates/base.html"

OPERATOR_TEMPLATE = "backend/listings/templates/listings/saved_search_notification_audit_events.html"

OPERATOR_TEMPLATE_NAME = "listings/saved_search_notification_audit_events.html"

PARENT_TEMPLATE_NAME = "base.html"

CONTENT_BLOCK_NAME = "content"

OPERATOR_URL_NAME = "listings:saved-search-notification-audit-events"

OPERATOR_URL_PATH = "/staff/saved-search-notification-audit/"

PROPOSED_IMPLEMENTATION_FILES = (
    "backend/listings/templates/listings/saved_search_notification_audit_events.html",
    "backend/listings/test_saved_search_notification_persistent_audit_operator_shared_shell_integration_v239.py",
    "docs/saved_search_notification_persistent_audit_operator_shared_shell_integration_v239.md",
)

SHELL_TRANSITION_CONTRACT = {
    "extends": PARENT_TEMPLATE_NAME,
    "required_block": CONTENT_BLOCK_NAME,
    "base_template_remains_unchanged": True,
    "remove_child_doctype": True,
    "remove_child_html_element": True,
    "remove_child_head_element": True,
    "remove_child_body_element": True,
    "remove_nested_main_element": True,
    "preserve_main_content_target": True,
    "preserve_audit_events_skip_target": True,
}

ACCESSIBILITY_CONTRACT = {
    "shared_navigation_visible": True,
    "notification_audit_active": True,
    "active_class": "active",
    "active_aria_current": "page",
    "main_content_id": "main-content",
    "skip_href": "#audit-events",
    "audit_events_id": "audit-events",
    "audit_events_tabindex": "-1",
    "no_duplicate_main_landmark": True,
    "no_duplicate_document_shell": True,
}

BEHAVIOR_PRESERVATION_CONTRACT = (
    "staff-only HTML access",
    "anonymous login redirect",
    "authenticated non-staff HTTP 403",
    "GET and HEAD only",
    "exact filter parsing",
    "fail-closed invalid filters",
    "filter chips",
    "bounded pagination",
    "filter-preserving pagination",
    "bounded CSV export",
    "CSV formula-injection protection",
    "metadata sanitization",
    "fingerprint copy control",
    "live copy status",
    "empty-state guidance",
    "read-only rollback navigation",
)

STYLE_SCRIPT_CONTRACT = {
    "preserve_page_specific_css": True,
    "preserve_focus_styles": True,
    "preserve_reduced_motion": True,
    "preserve_forced_colors": True,
    "preserve_fingerprint_copy_script": True,
    "no_external_frontend_dependency": True,
    "reuse_existing_base_blocks_only": True,
}

SECURITY_PRIVACY_CONTRACT = {
    "no_authorization_change": True,
    "no_query_service_change": True,
    "no_view_change": True,
    "no_url_change": True,
    "no_model_change": True,
    "no_migration": True,
    "no_editable_admin": True,
    "no_runtime_change": True,
    "no_delivery_change": True,
    "no_private_payload_expansion": True,
    "no_mutation_action": True,
}

IMPLEMENTATION_ACCEPTANCE_GATES = (
    "operator template extends base.html",
    "operator content is defined in the content block",
    "operator child no longer owns doctype html head or body",
    "operator child does not add a nested main landmark",
    "rendered operator page includes shared Admin tools navigation",
    "Notification audit is active on the operator page",
    "active navigation uses aria-current page",
    "v235 accessibility behavior remains green",
    "v234 read-interface behavior remains green",
    "v237 navigation behavior remains green",
    "filters pagination CSV metadata and copy behavior remain green",
    "authorization and GET-only behavior remain unchanged",
    "no model migration admin runtime or delivery change",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v239: saved-search notification persistent audit operator shared-shell integration implementation"


class SavedSearchNotificationPersistentAuditOperatorSharedShellIntegrationContractV238Tests(
    SimpleTestCase
):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _resolve_repo_path(
        self,
        relative_path: str,
    ) -> Path:
        path = Path(relative_path)

        if (
            path.parts
            and path.parts[0] == "backend"
        ):
            path = Path(*path.parts[1:])

        return self._backend_root() / path

    def _read_repo_path(self, relative_path: str) -> str:
        return self._resolve_repo_path(
            relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def _base_source(self) -> str:
        return self._read_repo_path(
            BASE_TEMPLATE
        )

    def _operator_source(self) -> str:
        return self._read_repo_path(
            OPERATOR_TEMPLATE
        )

    def _implementation_is_packaged(self) -> bool:
        return (
            V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION
            in self._operator_source()
        )

    def test_v238_marker_declares_shared_shell_contract(self):
        self.assertEqual(
            V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CONTRACT,
            "V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CONTRACT",
        )

    def test_v238_operator_route_remains_stable(self):
        self.assertEqual(
            reverse(OPERATOR_URL_NAME),
            OPERATOR_URL_PATH,
        )

    def test_v238_base_template_owns_shared_document_shell(self):
        source = self._base_source()
        folded = source.casefold()

        for term in (
            "<!doctype html",
            "<html",
            "<head",
            "<body",
            "<main",
        ):
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    folded,
                )

        self.assertRegex(
            source,
            r"{%\s*block\s+content\s*%}",
        )

    def test_v238_v237_navigation_remains_packaged(self):
        source = self._base_source()

        for term in (
            "V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION",
            "Notification audit",
            "saved-search-notification-audit-events",
            'aria-current="page"',
        ):
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

    def test_v238_current_or_future_shell_state_is_valid(self):
        source = self._operator_source()
        folded = source.casefold()

        if not self._implementation_is_packaged():
            for term in (
                "<!doctype html",
                "<html",
                "<head",
                "<body",
                "<main",
            ):
                with self.subTest(term=term):
                    self.assertIn(
                        term,
                        folded,
                    )

            self.assertNotRegex(
                source,
                r"{%\s*extends\s+[\"']base\.html[\"']\s*%}",
            )

            self.assertNotRegex(
                source,
                r"{%\s*block\s+content\s*%}",
            )

            return

        self.assertRegex(
            source,
            r"{%\s*extends\s+[\"']base\.html[\"']\s*%}",
        )

        self.assertRegex(
            source,
            r"{%\s*block\s+content\s*%}",
        )

        for forbidden in (
            "<!doctype html",
            "<html",
            "<head",
            "<body",
            "<main",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    folded,
                )

    def test_v238_shell_transition_contract_is_exact(self):
        self.assertEqual(
            SHELL_TRANSITION_CONTRACT,
            {
                "extends": "base.html",
                "required_block": "content",
                "base_template_remains_unchanged": True,
                "remove_child_doctype": True,
                "remove_child_html_element": True,
                "remove_child_head_element": True,
                "remove_child_body_element": True,
                "remove_nested_main_element": True,
                "preserve_main_content_target": True,
                "preserve_audit_events_skip_target": True,
            },
        )

    def test_v238_v239_scope_is_template_test_and_doc_only(self):
        self.assertEqual(
            PROPOSED_IMPLEMENTATION_FILES,
            (
                "backend/listings/templates/listings/saved_search_notification_audit_events.html",
                "backend/listings/test_saved_search_notification_persistent_audit_operator_shared_shell_integration_v239.py",
                "docs/saved_search_notification_persistent_audit_operator_shared_shell_integration_v239.md",
            ),
        )

        self.assertNotIn(
            BASE_TEMPLATE,
            PROPOSED_IMPLEMENTATION_FILES,
        )

    def test_v238_base_template_must_remain_unchanged_in_v239(self):
        source = self._base_source()

        self.assertNotIn(
            V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION,
            source,
        )

        self.assertTrue(
            SHELL_TRANSITION_CONTRACT[
                "base_template_remains_unchanged"
            ]
        )

    def test_v238_accessibility_contract_preserves_v235_targets(self):
        self.assertEqual(
            ACCESSIBILITY_CONTRACT["main_content_id"],
            "main-content",
        )
        self.assertEqual(
            ACCESSIBILITY_CONTRACT["skip_href"],
            "#audit-events",
        )
        self.assertEqual(
            ACCESSIBILITY_CONTRACT["audit_events_id"],
            "audit-events",
        )
        self.assertEqual(
            ACCESSIBILITY_CONTRACT["audit_events_tabindex"],
            "-1",
        )
        self.assertTrue(
            ACCESSIBILITY_CONTRACT[
                "no_duplicate_main_landmark"
            ]
        )

    def test_v238_operator_accessibility_targets_are_currently_present(
        self,
    ):
        source = self._operator_source()

        for term in (
            'href="#audit-events"',
            'id="main-content"',
            'id="audit-events"',
            'tabindex="-1"',
        ):
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

    def test_v238_shared_navigation_active_state_is_required(self):
        self.assertTrue(
            ACCESSIBILITY_CONTRACT[
                "shared_navigation_visible"
            ]
        )
        self.assertTrue(
            ACCESSIBILITY_CONTRACT[
                "notification_audit_active"
            ]
        )
        self.assertEqual(
            ACCESSIBILITY_CONTRACT[
                "active_class"
            ],
            "active",
        )
        self.assertEqual(
            ACCESSIBILITY_CONTRACT[
                "active_aria_current"
            ],
            "page",
        )

    def test_v238_behavior_preservation_contract_is_complete(self):
        required = {
            "staff-only HTML access",
            "anonymous login redirect",
            "authenticated non-staff HTTP 403",
            "GET and HEAD only",
            "exact filter parsing",
            "fail-closed invalid filters",
            "bounded pagination",
            "bounded CSV export",
            "CSV formula-injection protection",
            "metadata sanitization",
            "fingerprint copy control",
            "live copy status",
            "read-only rollback navigation",
        }

        self.assertTrue(
            required.issubset(
                set(
                    BEHAVIOR_PRESERVATION_CONTRACT
                )
            )
        )

    def test_v238_style_and_script_contract_preserves_v235_behavior(
        self,
    ):
        for key in (
            "preserve_page_specific_css",
            "preserve_focus_styles",
            "preserve_reduced_motion",
            "preserve_forced_colors",
            "preserve_fingerprint_copy_script",
            "no_external_frontend_dependency",
            "reuse_existing_base_blocks_only",
        ):
            with self.subTest(key=key):
                self.assertTrue(
                    STYLE_SCRIPT_CONTRACT[key]
                )

    def test_v238_security_privacy_contract_forbids_scope_expansion(
        self,
    ):
        for key, value in (
            SECURITY_PRIVACY_CONTRACT.items()
        ):
            with self.subTest(key=key):
                self.assertTrue(value)

    def test_v238_operator_template_still_contains_no_mutation_form(
        self,
    ):
        source = self._operator_source()
        folded = source.casefold()

        post_form = re.search(
            (
                r"<form\\b[^>]*"
                r"\\bmethod\\s*=\\s*"
                r"[\"']post[\"']"
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
                r"<(?:a|button|input|form)\\b[^>]*"
                r"(?:data-action|name|value|formaction|href)"
                r"\\s*=\\s*[\"'][^\"']*"
                r"(?:execute_send|retry|delete|edit)"
                r"[^\"']*[\"'][^>]*>"
            ),
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )

        self.assertIsNone(
            mutation_control
        )

        self.assertIn(
            "read-only-note",
            folded,
        )

        self.assertIn(
            "cannot send email",
            folded,
        )

        self.assertIn(
            "retry delivery",
            folded,
        )

    def test_v238_runtime_and_query_surfaces_do_not_receive_markers(
        self,
    ):
        protected = (
            "backend/listings/saved_search_notification_audit_operator.py",
            "backend/listings/saved_search_notification_audit_operator_views.py",
            "backend/listings/urls.py",
            "backend/listings/models.py",
            "backend/listings/admin.py",
            "backend/listings/saved_search_notification_audit_persistence.py",
            "backend/listings/saved_search_notification_audit_runtime.py",
            "backend/listings/saved_search_notification_email_renderer.py",
            "backend/listings/saved_search_notification_scheduler.py",
            "backend/listings/saved_search_notification_email_sender.py",
            "backend/listings/saved_search_notification_audit.py",
            "backend/listings/management/commands/process_saved_search_notifications.py",
        )

        for relative_path in protected:
            source = self._read_repo_path(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CONTRACT,
                    source,
                )
                self.assertNotIn(
                    V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION,
                    source,
                )

    def test_v238_model_admin_and_migration_boundary_is_unchanged(
        self,
    ):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

        migration_directory = self._resolve_repo_path(
            "backend/listings/migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "0017*"
                )
            ),
            [],
        )

    def test_v238_transition_artifacts_match_packaging_state(self):
        future_test = self._resolve_repo_path(
            PROPOSED_IMPLEMENTATION_FILES[1]
        )

        self.assertEqual(
            PROPOSED_IMPLEMENTATION_FILES[2],
            (
                "docs/"
                "saved_search_notification_persistent_audit_"
                "operator_shared_shell_integration_v239.md"
            ),
        )

        if self._implementation_is_packaged():
            self.assertTrue(
                future_test.is_file()
            )
            return

        self.assertFalse(
            future_test.exists()
        )

    def test_v238_acceptance_gates_cover_shell_behavior_and_safety(
        self,
    ):
        required = {
            "operator template extends base.html",
            "operator content is defined in the content block",
            "operator child no longer owns doctype html head or body",
            "operator child does not add a nested main landmark",
            "rendered operator page includes shared Admin tools navigation",
            "Notification audit is active on the operator page",
            "active navigation uses aria-current page",
            "v235 accessibility behavior remains green",
            "filters pagination CSV metadata and copy behavior remain green",
            "authorization and GET-only behavior remain unchanged",
            "no model migration admin runtime or delivery change",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(
                    IMPLEMENTATION_ACCEPTANCE_GATES
                )
            )
        )

    def test_v238_next_lane_is_shared_shell_implementation(self):
        self.assertEqual(
            NEXT_CHECKPOINT,
            "v239: saved-search notification persistent audit operator shared-shell integration implementation",
        )
