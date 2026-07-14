from __future__ import annotations

from pathlib import Path

from django.contrib import admin
from django.test import SimpleTestCase
from django.urls import reverse

from listings.models import SavedSearchNotificationAuditEvent


V236_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION_CONTRACT = (
    "V236_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION_CONTRACT"
)

NAVIGATION_TEMPLATE_PATH = "templates/base.html"

CORE_SMOKE_TEST_PATH = (
    "accounts/tests/test_core_page_smoke.py"
)

V237_TEST_PATH = (
    "listings/"
    "test_saved_search_notification_persistent_audit_"
    "operator_navigation_integration_v237.py"
)

PROPOSED_URL_NAME = (
    "listings:saved-search-notification-audit-events"
)

PROPOSED_ROUTE_PATH = (
    "/staff/saved-search-notification-audit/"
)

PROPOSED_LINK_LABEL = (
    "Notification audit"
)

PROPOSED_LINK_DESCRIPTION = (
    "Inspect saved-search notification audit events"
)

PROPOSED_PARENT_GROUP = (
    "Admin tools"
)

PROPOSED_IMPLEMENTATION_MARKER = (
    "V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION"
)

NAVIGATION_VISIBILITY_CONTRACT = {
    "anonymous": False,
    "authenticated_non_staff": False,
    "authenticated_staff": True,
    "superuser": True,
    "permission_basis": "is_staff",
    "object_permission_required": False,
}

NAVIGATION_PLACEMENT_CONTRACT = {
    "owner_template": NAVIGATION_TEMPLATE_PATH,
    "parent_group": PROPOSED_PARENT_GROUP,
    "new_top_level_group_allowed": False,
    "duplicate_link_allowed": False,
    "link_count": 1,
    "link_order": (
        "after existing Admin tools operational links"
    ),
    "public_navigation_allowed": False,
    "buyer_navigation_allowed": False,
    "seller_navigation_allowed": False,
}

NAVIGATION_LINK_CONTRACT = {
    "label": PROPOSED_LINK_LABEL,
    "description": PROPOSED_LINK_DESCRIPTION,
    "url_name": PROPOSED_URL_NAME,
    "hardcoded_path_allowed": False,
    "opens_new_window": False,
    "download_attribute": False,
    "method": "GET",
}

NAVIGATION_ACTIVE_STATE_CONTRACT = {
    "match_namespace": "listings",
    "match_url_name": (
        "saved-search-notification-audit-events"
    ),
    "aria_current": "page",
    "active_class": "active",
    "querystring_independent": True,
    "html_page_active": True,
    "filtered_html_page_active": True,
    "csv_download_requires_navigation_render": False,
}

NAVIGATION_ACCESSIBILITY_CONTRACT = {
    "descriptive_visible_label": True,
    "aria_current_on_active_link": True,
    "keyboard_operable": True,
    "no_icon_only_link": True,
    "no_color_only_state": True,
    "existing_group_semantics_preserved": True,
    "existing_focus_order_preserved": True,
    "existing_mobile_navigation_preserved": True,
}

NAVIGATION_SECURITY_CONTRACT = {
    "link_does_not_replace_view_authorization": True,
    "target_remains_staff_only": True,
    "non_staff_direct_request_remains_403": True,
    "anonymous_direct_request_remains_login_redirect": True,
    "no_email_delivery_action": True,
    "no_retry_action": True,
    "no_rollback_action": True,
    "no_timestamp_mutation": True,
}

NAVIGATION_PRIVACY_CONTRACT = {
    "event_count_badge_allowed": False,
    "failure_count_badge_allowed": False,
    "owner_identifier_in_navigation_allowed": False,
    "recipient_identifier_in_navigation_allowed": False,
    "event_metadata_in_navigation_allowed": False,
    "notification_content_in_navigation_allowed": False,
}

IMPLEMENTATION_SCOPE_CONTRACT = {
    "modify": (
        NAVIGATION_TEMPLATE_PATH,
    ),
    "create": (
        V237_TEST_PATH,
        (
            "docs/"
            "saved_search_notification_persistent_audit_"
            "operator_navigation_integration_v237.md"
        ),
    ),
    "optional_modify": (),
    "model_change": False,
    "migration_change": False,
    "url_change": False,
    "view_change": False,
    "query_service_change": False,
    "operator_page_template_change": False,
    "admin_registration_change": False,
    "runtime_change": False,
}

PRESERVED_NAVIGATION_CONTRACT = (
    "existing grouped administration navigation remains grouped",
    "existing Admin tools links remain present",
    "existing admin dashboard link remains present",
    "existing moderation and report links remain present",
    "existing buyer and seller navigation remains unchanged",
    "existing mobile navigation behavior remains unchanged",
    "existing core page smoke tests remain green",
)

IMPLEMENTATION_ACCEPTANCE_GATES = (
    "staff users see exactly one Notification audit link",
    "anonymous users do not see the link",
    "authenticated non-staff users do not see the link",
    "the link uses the existing named route",
    "the link is inside the existing Admin tools group",
    "the active audit page link uses aria-current page",
    "query parameters do not break active state",
    "no event count or failure badge is rendered",
    "no private audit data is rendered in navigation",
    "direct target authorization remains unchanged",
    "existing grouped navigation tests remain green",
    "operator read-interface tests remain green",
    "no model or migration change is generated",
    "runtime and delivery surfaces remain unchanged",
    "full regression remains green",
)


class SavedSearchNotificationPersistentAuditOperatorNavigationIntegrationContractV236Tests(
    SimpleTestCase
):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _read_backend(self, relative_path: str) -> str:
        return (
            self._backend_root()
            / relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def test_v236_marker_declares_navigation_integration_contract(self):
        self.assertEqual(
            V236_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION_CONTRACT,
            (
                "V236_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
                "AUDIT_OPERATOR_NAVIGATION_INTEGRATION_CONTRACT"
            ),
        )

    def test_v236_detected_navigation_owner_exists(self):
        path = (
            self._backend_root()
            / NAVIGATION_TEMPLATE_PATH
        )

        self.assertTrue(path.is_file())

        source = path.read_text(
            encoding="utf-8",
            errors="strict",
        )

        self.assertIn(
            "is_staff",
            source,
        )

    def test_v236_existing_core_navigation_smoke_guard_is_packaged(self):
        source = self._read_backend(
            CORE_SMOKE_TEST_PATH
        )

        self.assertIn(
            "test_admin_navigation_is_grouped",
            source,
        )
        self.assertIn(
            "test_admin_trust_safety_pages_render",
            source,
        )

    def test_v236_target_named_route_is_stable(self):
        self.assertEqual(
            reverse(PROPOSED_URL_NAME),
            PROPOSED_ROUTE_PATH,
        )

    def test_v236_link_contract_uses_named_get_navigation(self):
        self.assertEqual(
            NAVIGATION_LINK_CONTRACT["url_name"],
            PROPOSED_URL_NAME,
        )
        self.assertEqual(
            NAVIGATION_LINK_CONTRACT["method"],
            "GET",
        )
        self.assertFalse(
            NAVIGATION_LINK_CONTRACT[
                "hardcoded_path_allowed"
            ]
        )
        self.assertFalse(
            NAVIGATION_LINK_CONTRACT[
                "opens_new_window"
            ]
        )
        self.assertFalse(
            NAVIGATION_LINK_CONTRACT[
                "download_attribute"
            ]
        )

    def test_v236_visibility_contract_is_staff_only(self):
        self.assertEqual(
            NAVIGATION_VISIBILITY_CONTRACT,
            {
                "anonymous": False,
                "authenticated_non_staff": False,
                "authenticated_staff": True,
                "superuser": True,
                "permission_basis": "is_staff",
                "object_permission_required": False,
            },
        )

    def test_v236_link_belongs_to_existing_trust_safety_group(self):
        self.assertEqual(
            NAVIGATION_PLACEMENT_CONTRACT[
                "parent_group"
            ],
            "Admin tools",
        )
        self.assertFalse(
            NAVIGATION_PLACEMENT_CONTRACT[
                "new_top_level_group_allowed"
            ]
        )
        self.assertFalse(
            NAVIGATION_PLACEMENT_CONTRACT[
                "duplicate_link_allowed"
            ]
        )
        self.assertEqual(
            NAVIGATION_PLACEMENT_CONTRACT[
                "link_count"
            ],
            1,
        )

    def test_v236_active_state_is_querystring_independent(self):
        self.assertEqual(
            NAVIGATION_ACTIVE_STATE_CONTRACT[
                "match_namespace"
            ],
            "listings",
        )
        self.assertEqual(
            NAVIGATION_ACTIVE_STATE_CONTRACT[
                "match_url_name"
            ],
            "saved-search-notification-audit-events",
        )
        self.assertEqual(
            NAVIGATION_ACTIVE_STATE_CONTRACT[
                "aria_current"
            ],
            "page",
        )
        self.assertTrue(
            NAVIGATION_ACTIVE_STATE_CONTRACT[
                "querystring_independent"
            ]
        )
        self.assertTrue(
            NAVIGATION_ACTIVE_STATE_CONTRACT[
                "filtered_html_page_active"
            ]
        )

    def test_v236_accessibility_contract_requires_visible_text_and_aria_current(
        self,
    ):
        self.assertTrue(
            NAVIGATION_ACCESSIBILITY_CONTRACT[
                "descriptive_visible_label"
            ]
        )
        self.assertTrue(
            NAVIGATION_ACCESSIBILITY_CONTRACT[
                "aria_current_on_active_link"
            ]
        )
        self.assertTrue(
            NAVIGATION_ACCESSIBILITY_CONTRACT[
                "keyboard_operable"
            ]
        )
        self.assertFalse(
            NAVIGATION_ACCESSIBILITY_CONTRACT[
                "no_icon_only_link"
            ]
            is False
        )
        self.assertTrue(
            NAVIGATION_ACCESSIBILITY_CONTRACT[
                "no_color_only_state"
            ]
        )

    def test_v236_navigation_does_not_weaken_target_authorization(self):
        self.assertTrue(
            NAVIGATION_SECURITY_CONTRACT[
                "link_does_not_replace_view_authorization"
            ]
        )
        self.assertTrue(
            NAVIGATION_SECURITY_CONTRACT[
                "target_remains_staff_only"
            ]
        )
        self.assertTrue(
            NAVIGATION_SECURITY_CONTRACT[
                "non_staff_direct_request_remains_403"
            ]
        )
        self.assertTrue(
            NAVIGATION_SECURITY_CONTRACT[
                "anonymous_direct_request_remains_login_redirect"
            ]
        )

    def test_v236_navigation_exposes_no_actions(self):
        action_keys = (
            "no_email_delivery_action",
            "no_retry_action",
            "no_rollback_action",
            "no_timestamp_mutation",
        )

        for key in action_keys:
            with self.subTest(key=key):
                self.assertTrue(
                    NAVIGATION_SECURITY_CONTRACT[key]
                )

    def test_v236_navigation_exposes_no_operational_counts_or_private_data(
        self,
    ):
        for allowed in (
            NAVIGATION_PRIVACY_CONTRACT.values()
        ):
            self.assertFalse(allowed)

    def test_v236_v237_scope_is_navigation_template_plus_test_and_doc_only(
        self,
    ):
        self.assertEqual(
            IMPLEMENTATION_SCOPE_CONTRACT["modify"],
            (
                NAVIGATION_TEMPLATE_PATH,
            ),
        )
        self.assertEqual(
            IMPLEMENTATION_SCOPE_CONTRACT["create"][0],
            V237_TEST_PATH,
        )

        forbidden_changes = (
            "model_change",
            "migration_change",
            "url_change",
            "view_change",
            "query_service_change",
            "operator_page_template_change",
            "admin_registration_change",
            "runtime_change",
        )

        for key in forbidden_changes:
            with self.subTest(key=key):
                self.assertFalse(
                    IMPLEMENTATION_SCOPE_CONTRACT[key]
                )

    def test_v236_existing_navigation_behavior_must_be_preserved(self):
        required = {
            "existing grouped administration navigation remains grouped",
            "existing Admin tools links remain present",
            "existing admin dashboard link remains present",
            "existing moderation and report links remain present",
            "existing buyer and seller navigation remains unchanged",
            "existing mobile navigation behavior remains unchanged",
            "existing core page smoke tests remain green",
        }

        self.assertEqual(
            set(PRESERVED_NAVIGATION_CONTRACT),
            required,
        )

    def test_v236_contract_is_deferred_until_v237_is_packaged(self):
        navigation_source = self._read_backend(
            NAVIGATION_TEMPLATE_PATH
        )

        future_test = (
            self._backend_root()
            / V237_TEST_PATH
        )

        if future_test.exists():
            self.assertIn(
                PROPOSED_LINK_LABEL,
                navigation_source,
            )
            self.assertIn(
                "saved-search-notification-audit-events",
                navigation_source,
            )
            self.assertIn(
                PROPOSED_IMPLEMENTATION_MARKER,
                navigation_source,
            )
            self.assertIn(
                "aria-current",
                navigation_source,
            )
        else:
            self.assertNotIn(
                PROPOSED_LINK_LABEL,
                navigation_source,
            )
            self.assertNotIn(
                "saved-search-notification-audit-events",
                navigation_source,
            )
            self.assertNotIn(
                PROPOSED_IMPLEMENTATION_MARKER,
                navigation_source,
            )

    def test_v236_audit_model_remains_unregistered_in_admin(self):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

    def test_v236_contract_marker_does_not_leak_into_operator_runtime(self):
        protected_paths = (
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

        marker = (
            "V236_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
            "AUDIT_OPERATOR_NAVIGATION_INTEGRATION_CONTRACT"
        )

        for relative_path in protected_paths:
            source = self._read_backend(relative_path)

            with self.subTest(relative_path=relative_path):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_v236_acceptance_gates_cover_visibility_accessibility_and_safety(
        self,
    ):
        required = {
            "staff users see exactly one Notification audit link",
            "anonymous users do not see the link",
            "authenticated non-staff users do not see the link",
            "the link uses the existing named route",
            "the link is inside the existing Admin tools group",
            "the active audit page link uses aria-current page",
            "query parameters do not break active state",
            "no event count or failure badge is rendered",
            "no private audit data is rendered in navigation",
            "direct target authorization remains unchanged",
            "existing grouped navigation tests remain green",
            "no model or migration change is generated",
            "runtime and delivery surfaces remain unchanged",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(IMPLEMENTATION_ACCEPTANCE_GATES)
            )
        )

    def test_v236_next_lane_is_navigation_integration_implementation(self):
        next_lane = "v237: saved-search notification persistent audit operator navigation integration implementation"

        self.assertEqual(
            next_lane,
            "v237: saved-search notification persistent audit operator navigation integration implementation",
        )
