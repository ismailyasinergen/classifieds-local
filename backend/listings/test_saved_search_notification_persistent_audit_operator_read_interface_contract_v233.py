from __future__ import annotations

from pathlib import Path

from django.contrib import admin
from django.test import SimpleTestCase

from listings.models import SavedSearchNotificationAuditEvent


V233_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE_CONTRACT = (
    "V233_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE_CONTRACT"
)

PROPOSED_QUERY_MODULE = (
    "listings/saved_search_notification_audit_operator.py"
)

PROPOSED_VIEW_MODULE = (
    "listings/saved_search_notification_audit_operator_views.py"
)

PROPOSED_TEMPLATE = (
    "listings/templates/listings/"
    "saved_search_notification_audit_events.html"
)

PROPOSED_URL_PATH = (
    "staff/saved-search-notification-audit/"
)

PROPOSED_URL_NAME = (
    "saved-search-notification-audit-events"
)

PROPOSED_FILTER_TYPE = (
    "SavedSearchNotificationAuditOperatorFilters"
)

PROPOSED_PAGE_TYPE = (
    "SavedSearchNotificationAuditOperatorPage"
)

PROPOSED_PARSE_FUNCTION = (
    "parse_saved_search_notification_audit_operator_filters"
)

PROPOSED_QUERY_FUNCTION = (
    "build_saved_search_notification_audit_operator_queryset"
)

PROPOSED_SERIALIZE_FUNCTION = (
    "serialize_saved_search_notification_audit_event_for_operator"
)

PROPOSED_SANITIZE_FUNCTION = (
    "sanitize_saved_search_notification_audit_metadata_for_operator"
)

PROPOSED_CSV_FUNCTION = (
    "iter_saved_search_notification_audit_csv_rows"
)

PROPOSED_VIEW_CLASS = (
    "SavedSearchNotificationAuditEventListView"
)

EXPECTED_MODEL_FIELDS = (
    "id",
    "saved_search",
    "owner_id_snapshot",
    "event_type",
    "outcome",
    "reason_code",
    "occurred_at",
    "created_at",
    "batch_id",
    "correlation_id",
    "delivery_attempt_id",
    "idempotency_key",
    "notification_fingerprint",
    "rollback_of",
    "actor_type",
    "actor_identifier",
    "source",
    "checked_at_before",
    "checked_at_after",
    "sent_at_before",
    "sent_at_after",
    "metadata",
)

EXPECTED_INDEX_NAMES = {
    "ssna_saved_occ_idx",
    "ssna_event_occ_idx",
    "ssna_outcome_occ_idx",
    "ssna_batch_idx",
    "ssna_corr_idx",
    "ssna_attempt_idx",
    "ssna_fingerprint_idx",
    "ssna_rollback_idx",
}

OPERATOR_ACCESS_CONTRACT = {
    "authentication": "required",
    "authorization": "is_staff",
    "anonymous_response": 302,
    "authenticated_non_staff_response": 403,
    "allowed_methods": (
        "GET",
        "HEAD",
    ),
    "forbidden_methods": (
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ),
    "cross_owner_visibility": (
        "staff may inspect all persisted audit events"
    ),
}

OPERATOR_ROUTE_CONTRACT = {
    "path": PROPOSED_URL_PATH,
    "name": PROPOSED_URL_NAME,
    "view": PROPOSED_VIEW_CLASS,
    "template": PROPOSED_TEMPLATE,
    "html_format": "html",
    "csv_format": "csv",
    "csv_query_parameter": "format",
}

OPERATOR_FILTER_CONTRACT = {
    "event_id": {
        "kind": "uuid",
        "lookup": "exact",
    },
    "saved_search_id": {
        "kind": "positive_integer",
        "lookup": "exact",
    },
    "owner_id_snapshot": {
        "kind": "bounded_text",
        "maximum_length": 64,
        "lookup": "exact",
    },
    "event_type": {
        "kind": "choice",
        "choices": tuple(
            SavedSearchNotificationAuditEvent
            .EventType
            .values
        ),
    },
    "outcome": {
        "kind": "choice",
        "choices": tuple(
            SavedSearchNotificationAuditEvent
            .Outcome
            .values
        ),
    },
    "actor_type": {
        "kind": "choice",
        "choices": tuple(
            SavedSearchNotificationAuditEvent
            .ActorType
            .values
        ),
    },
    "source": {
        "kind": "bounded_text",
        "maximum_length": 128,
        "lookup": "exact",
    },
    "reason_code": {
        "kind": "bounded_text",
        "maximum_length": 96,
        "lookup": "exact",
    },
    "batch_id": {
        "kind": "uuid",
        "lookup": "exact",
    },
    "correlation_id": {
        "kind": "uuid",
        "lookup": "exact",
    },
    "delivery_attempt_id": {
        "kind": "uuid",
        "lookup": "exact",
    },
    "idempotency_key": {
        "kind": "bounded_text",
        "maximum_length": 128,
        "lookup": "exact",
    },
    "notification_fingerprint": {
        "kind": "sha256",
        "maximum_length": 64,
        "lookup": "exact",
    },
    "rollback_linked": {
        "kind": "boolean",
        "lookup": "rollback_of__isnull",
    },
    "occurred_from": {
        "kind": "aware_iso8601_datetime",
        "lookup": "occurred_at__gte",
    },
    "occurred_to": {
        "kind": "aware_iso8601_datetime",
        "lookup": "occurred_at__lte",
    },
    "page": {
        "kind": "positive_integer",
        "default": 1,
    },
    "page_size": {
        "kind": "bounded_positive_integer",
        "default": 50,
        "maximum": 100,
    },
    "format": {
        "kind": "choice",
        "choices": (
            "html",
            "csv",
        ),
        "default": "html",
    },
}

OPERATOR_QUERY_CONTRACT = {
    "model": "SavedSearchNotificationAuditEvent",
    "select_related": (
        "saved_search",
    ),
    "forbidden_select_related": (
        "saved_search__user",
    ),
    "ordering": (
        "-occurred_at",
        "-created_at",
        "-id",
    ),
    "default_page_size": 50,
    "maximum_page_size": 100,
    "maximum_csv_rows": 5000,
    "count_required_for_html": True,
    "unbounded_export_allowed": False,
}

OPERATOR_SUMMARY_FIELDS = (
    "event_id",
    "occurred_at",
    "saved_search_id",
    "saved_search_label",
    "owner_id_snapshot",
    "event_type",
    "outcome",
    "reason_code",
    "source",
    "actor_type",
    "correlation_id",
    "delivery_attempt_id",
    "rollback_of_id",
)

OPERATOR_DETAIL_FIELDS = (
    "created_at",
    "batch_id",
    "idempotency_key",
    "notification_fingerprint",
    "actor_identifier",
    "checked_at_before",
    "checked_at_after",
    "sent_at_before",
    "sent_at_after",
    "metadata",
)

OPERATOR_FORBIDDEN_FIELDS = (
    "owner_email",
    "recipient_email",
    "saved_search_query_params",
    "saved_search_querystring",
    "saved_search_path",
    "email_subject",
    "rendered_email_body",
    "rendered_html",
    "rendered_text",
    "listing_title",
    "listing_description",
    "private_listing_url",
    "exception_message",
    "traceback",
    "stack_trace",
    "authorization",
    "cookie",
    "session",
    "token",
    "password",
    "secret",
    "credential",
)

OPERATOR_METADATA_CONTRACT = {
    "input": "stored metadata JSON object",
    "output": "recursively sanitized JSON object",
    "sort_keys": True,
    "maximum_depth": 6,
    "maximum_rendered_bytes": 16384,
    "redaction_text": "[redacted]",
    "deny_sensitive_keys": True,
    "deny_non_string_keys": True,
    "trust_database_payload_blindly": False,
}

OPERATOR_HTML_CONTRACT = {
    "escape_all_values": True,
    "metadata_rendering": "escaped canonical JSON",
    "fingerprint_display": "truncated with explicit copy value",
    "empty_value_text": "—",
    "pagination_required": True,
    "filter_state_preserved": True,
    "csv_link_preserves_filters": True,
    "rollback_link_is_read_only": True,
    "no_inline_actions": True,
    "no_forms_that_mutate": True,
}

OPERATOR_CSV_HEADERS = (
    "event_id",
    "occurred_at",
    "created_at",
    "saved_search_id",
    "saved_search_label",
    "owner_id_snapshot",
    "event_type",
    "outcome",
    "reason_code",
    "source",
    "actor_type",
    "actor_identifier",
    "batch_id",
    "correlation_id",
    "delivery_attempt_id",
    "idempotency_key",
    "notification_fingerprint",
    "rollback_of_id",
    "checked_at_before",
    "checked_at_after",
    "sent_at_before",
    "sent_at_after",
    "metadata_json",
)

OPERATOR_CSV_CONTRACT = {
    "headers": OPERATOR_CSV_HEADERS,
    "maximum_rows": 5000,
    "uses_same_filters_as_html": True,
    "ordering_matches_html": True,
    "timestamps": "UTC ISO-8601",
    "content_type": "text/csv; charset=utf-8",
    "filename": "saved-search-notification-audit.csv",
    "formula_prefixes": (
        "=",
        "+",
        "-",
        "@",
    ),
    "formula_escape_prefix": "'",
    "unbounded_export_allowed": False,
}

OPERATOR_ERROR_CONTRACT = {
    "invalid_choice": 400,
    "invalid_uuid": 400,
    "invalid_datetime": 400,
    "naive_datetime": 400,
    "reversed_date_range": 400,
    "invalid_page": 400,
    "invalid_page_size": 400,
    "oversized_page_size": 400,
    "unsupported_format": 400,
    "silently_ignore_invalid_filters": False,
}

OPERATOR_ROLLBACK_LINK_CONTRACT = {
    "display_rollback_of": True,
    "target_same_interface": True,
    "target_filter": "event_id",
    "missing_target_is_non_crashing": True,
    "preview_action_present": False,
    "apply_action_present": False,
    "mutation_present": False,
}

READ_ONLY_INVARIANTS = (
    "query service performs no create",
    "query service performs no save",
    "query service performs no update",
    "query service performs no delete",
    "query service performs no bulk update",
    "view accepts GET and HEAD only",
    "view contains no delivery action",
    "view contains no rollback action",
    "view does not mutate notification timestamps",
    "view does not import the sender",
    "view does not import the scheduler",
    "view does not import the runtime recorder",
    "view does not import the persistence writer",
    "audit model remains unregistered in Django admin",
    "saved-search admin remains unchanged",
    "no model field change",
    "no migration",
    "no retention deletion",
    "no background worker",
)

IMPLEMENTATION_ACCEPTANCE_GATES = (
    "staff authentication is required",
    "authenticated non-staff users receive 403",
    "POST PUT PATCH and DELETE receive 405",
    "all filters are explicitly validated",
    "invalid filters fail closed with 400",
    "query ordering is deterministic",
    "HTML pagination is bounded",
    "CSV export is bounded",
    "CSV uses the same filters and ordering as HTML",
    "CSV formula injection is neutralized",
    "recipient and owner email are never exposed",
    "saved-search query details are never exposed",
    "rendered email content is never exposed",
    "stored metadata is sanitized again on read",
    "rollback links are navigational only",
    "no delivery or rollback action is exposed",
    "no timestamp mutation is possible",
    "audit model remains append-only and admin-unregistered",
    "no model or migration change is introduced",
    "existing runtime integration remains unchanged",
    "full regression remains green",
)


class SavedSearchNotificationPersistentAuditOperatorReadInterfaceContractV233Tests(
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

    def test_v233_marker_declares_operator_read_interface_contract(self):
        self.assertEqual(
            V233_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE_CONTRACT,
            (
                "V233_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
                "AUDIT_OPERATOR_READ_INTERFACE_CONTRACT"
            ),
        )

    def test_v233_names_exact_future_modules_route_and_template(self):
        self.assertEqual(
            PROPOSED_QUERY_MODULE,
            "listings/saved_search_notification_audit_operator.py",
        )
        self.assertEqual(
            PROPOSED_VIEW_MODULE,
            (
                "listings/"
                "saved_search_notification_audit_operator_views.py"
            ),
        )
        self.assertEqual(
            PROPOSED_TEMPLATE,
            (
                "listings/templates/listings/"
                "saved_search_notification_audit_events.html"
            ),
        )
        self.assertEqual(
            PROPOSED_URL_PATH,
            "staff/saved-search-notification-audit/",
        )
        self.assertEqual(
            PROPOSED_URL_NAME,
            "saved-search-notification-audit-events",
        )

    def test_v233_names_exact_future_public_query_api(self):
        self.assertEqual(
            {
                PROPOSED_FILTER_TYPE,
                PROPOSED_PAGE_TYPE,
                PROPOSED_PARSE_FUNCTION,
                PROPOSED_QUERY_FUNCTION,
                PROPOSED_SERIALIZE_FUNCTION,
                PROPOSED_SANITIZE_FUNCTION,
                PROPOSED_CSV_FUNCTION,
                PROPOSED_VIEW_CLASS,
            },
            {
                "SavedSearchNotificationAuditOperatorFilters",
                "SavedSearchNotificationAuditOperatorPage",
                (
                    "parse_saved_search_notification_"
                    "audit_operator_filters"
                ),
                (
                    "build_saved_search_notification_"
                    "audit_operator_queryset"
                ),
                (
                    "serialize_saved_search_notification_"
                    "audit_event_for_operator"
                ),
                (
                    "sanitize_saved_search_notification_"
                    "audit_metadata_for_operator"
                ),
                (
                    "iter_saved_search_notification_"
                    "audit_csv_rows"
                ),
                "SavedSearchNotificationAuditEventListView",
            },
        )

    def test_v233_contract_matches_persistent_model_fields(self):
        actual_fields = tuple(
            field.name
            for field in (
                SavedSearchNotificationAuditEvent
                ._meta
                .fields
            )
        )

        self.assertEqual(
            actual_fields,
            EXPECTED_MODEL_FIELDS,
        )

    def test_v233_contract_preserves_existing_database_indexes(self):
        actual_index_names = {
            index.name
            for index in (
                SavedSearchNotificationAuditEvent
                ._meta
                .indexes
            )
        }

        self.assertEqual(
            actual_index_names,
            EXPECTED_INDEX_NAMES,
        )

    def test_v233_access_contract_is_staff_only_and_get_only(self):
        self.assertEqual(
            OPERATOR_ACCESS_CONTRACT["authentication"],
            "required",
        )
        self.assertEqual(
            OPERATOR_ACCESS_CONTRACT["authorization"],
            "is_staff",
        )
        self.assertEqual(
            OPERATOR_ACCESS_CONTRACT[
                "authenticated_non_staff_response"
            ],
            403,
        )
        self.assertEqual(
            OPERATOR_ACCESS_CONTRACT["allowed_methods"],
            (
                "GET",
                "HEAD",
            ),
        )
        self.assertEqual(
            set(
                OPERATOR_ACCESS_CONTRACT[
                    "forbidden_methods"
                ]
            ),
            {
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
            },
        )

    def test_v233_route_contract_uses_one_read_only_html_csv_surface(self):
        self.assertEqual(
            OPERATOR_ROUTE_CONTRACT["path"],
            PROPOSED_URL_PATH,
        )
        self.assertEqual(
            OPERATOR_ROUTE_CONTRACT["name"],
            PROPOSED_URL_NAME,
        )
        self.assertEqual(
            OPERATOR_ROUTE_CONTRACT["view"],
            PROPOSED_VIEW_CLASS,
        )
        self.assertEqual(
            OPERATOR_ROUTE_CONTRACT[
                "csv_query_parameter"
            ],
            "format",
        )

    def test_v233_filter_contract_covers_event_and_correlation_identity(self):
        required_filters = {
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
            "page",
            "page_size",
            "format",
        }

        self.assertEqual(
            set(OPERATOR_FILTER_CONTRACT),
            required_filters,
        )

    def test_v233_choice_filters_use_exact_model_taxonomy(self):
        self.assertEqual(
            set(
                OPERATOR_FILTER_CONTRACT[
                    "event_type"
                ]["choices"]
            ),
            set(
                SavedSearchNotificationAuditEvent
                .EventType
                .values
            ),
        )
        self.assertEqual(
            set(
                OPERATOR_FILTER_CONTRACT[
                    "outcome"
                ]["choices"]
            ),
            set(
                SavedSearchNotificationAuditEvent
                .Outcome
                .values
            ),
        )
        self.assertEqual(
            set(
                OPERATOR_FILTER_CONTRACT[
                    "actor_type"
                ]["choices"]
            ),
            set(
                SavedSearchNotificationAuditEvent
                .ActorType
                .values
            ),
        )

    def test_v233_identifier_filters_are_exact_not_fuzzy(self):
        exact_filters = (
            "event_id",
            "saved_search_id",
            "owner_id_snapshot",
            "source",
            "reason_code",
            "batch_id",
            "correlation_id",
            "delivery_attempt_id",
            "idempotency_key",
            "notification_fingerprint",
        )

        for filter_name in exact_filters:
            with self.subTest(filter_name=filter_name):
                self.assertEqual(
                    OPERATOR_FILTER_CONTRACT[
                        filter_name
                    ]["lookup"],
                    "exact",
                )

    def test_v233_query_contract_is_deterministic_and_bounded(self):
        self.assertEqual(
            OPERATOR_QUERY_CONTRACT["ordering"],
            (
                "-occurred_at",
                "-created_at",
                "-id",
            ),
        )
        self.assertEqual(
            OPERATOR_QUERY_CONTRACT[
                "default_page_size"
            ],
            50,
        )
        self.assertEqual(
            OPERATOR_QUERY_CONTRACT[
                "maximum_page_size"
            ],
            100,
        )
        self.assertEqual(
            OPERATOR_QUERY_CONTRACT[
                "maximum_csv_rows"
            ],
            5000,
        )
        self.assertFalse(
            OPERATOR_QUERY_CONTRACT[
                "unbounded_export_allowed"
            ]
        )

    def test_v233_query_contract_does_not_join_owner_pii(self):
        self.assertIn(
            "saved_search",
            OPERATOR_QUERY_CONTRACT[
                "select_related"
            ],
        )
        self.assertIn(
            "saved_search__user",
            OPERATOR_QUERY_CONTRACT[
                "forbidden_select_related"
            ],
        )

    def test_v233_summary_and_detail_fields_cover_operator_evidence(self):
        required_fields = {
            "event_id",
            "occurred_at",
            "saved_search_id",
            "owner_id_snapshot",
            "event_type",
            "outcome",
            "reason_code",
            "source",
            "correlation_id",
            "delivery_attempt_id",
            "rollback_of_id",
            "idempotency_key",
            "notification_fingerprint",
            "metadata",
        }

        self.assertTrue(
            required_fields.issubset(
                set(OPERATOR_SUMMARY_FIELDS)
                | set(OPERATOR_DETAIL_FIELDS)
            )
        )

    def test_v233_read_model_explicitly_forbids_private_payloads(self):
        required_forbidden = {
            "owner_email",
            "recipient_email",
            "saved_search_query_params",
            "saved_search_querystring",
            "rendered_email_body",
            "rendered_html",
            "listing_title",
            "exception_message",
            "traceback",
            "token",
            "password",
            "secret",
        }

        self.assertTrue(
            required_forbidden.issubset(
                set(OPERATOR_FORBIDDEN_FIELDS)
            )
        )

        visible_fields = (
            set(OPERATOR_SUMMARY_FIELDS)
            | set(OPERATOR_DETAIL_FIELDS)
            | set(OPERATOR_CSV_HEADERS)
        )

        self.assertTrue(
            visible_fields.isdisjoint(
                required_forbidden
            )
        )

    def test_v233_metadata_is_revalidated_and_bounded_on_read(self):
        self.assertFalse(
            OPERATOR_METADATA_CONTRACT[
                "trust_database_payload_blindly"
            ]
        )
        self.assertTrue(
            OPERATOR_METADATA_CONTRACT[
                "deny_sensitive_keys"
            ]
        )
        self.assertTrue(
            OPERATOR_METADATA_CONTRACT[
                "deny_non_string_keys"
            ]
        )
        self.assertEqual(
            OPERATOR_METADATA_CONTRACT[
                "redaction_text"
            ],
            "[redacted]",
        )
        self.assertLessEqual(
            OPERATOR_METADATA_CONTRACT[
                "maximum_rendered_bytes"
            ],
            16384,
        )

    def test_v233_html_contract_is_escaped_paginated_and_action_free(self):
        self.assertTrue(
            OPERATOR_HTML_CONTRACT[
                "escape_all_values"
            ]
        )
        self.assertEqual(
            OPERATOR_HTML_CONTRACT[
                "metadata_rendering"
            ],
            "escaped canonical JSON",
        )
        self.assertTrue(
            OPERATOR_HTML_CONTRACT[
                "pagination_required"
            ]
        )
        self.assertTrue(
            OPERATOR_HTML_CONTRACT[
                "filter_state_preserved"
            ]
        )
        self.assertTrue(
            OPERATOR_HTML_CONTRACT[
                "no_inline_actions"
            ]
        )
        self.assertTrue(
            OPERATOR_HTML_CONTRACT[
                "no_forms_that_mutate"
            ]
        )

    def test_v233_csv_contract_is_bounded_and_filter_equivalent(self):
        self.assertEqual(
            OPERATOR_CSV_CONTRACT["maximum_rows"],
            5000,
        )
        self.assertTrue(
            OPERATOR_CSV_CONTRACT[
                "uses_same_filters_as_html"
            ]
        )
        self.assertTrue(
            OPERATOR_CSV_CONTRACT[
                "ordering_matches_html"
            ]
        )
        self.assertFalse(
            OPERATOR_CSV_CONTRACT[
                "unbounded_export_allowed"
            ]
        )
        self.assertEqual(
            OPERATOR_CSV_CONTRACT["headers"],
            OPERATOR_CSV_HEADERS,
        )

    def test_v233_csv_contract_neutralizes_formula_injection(self):
        self.assertEqual(
            set(
                OPERATOR_CSV_CONTRACT[
                    "formula_prefixes"
                ]
            ),
            {
                "=",
                "+",
                "-",
                "@",
            },
        )
        self.assertEqual(
            OPERATOR_CSV_CONTRACT[
                "formula_escape_prefix"
            ],
            "'",
        )

    def test_v233_invalid_filters_fail_closed(self):
        expected_400_cases = {
            "invalid_choice",
            "invalid_uuid",
            "invalid_datetime",
            "naive_datetime",
            "reversed_date_range",
            "invalid_page",
            "invalid_page_size",
            "oversized_page_size",
            "unsupported_format",
        }

        for case_name in expected_400_cases:
            with self.subTest(case_name=case_name):
                self.assertEqual(
                    OPERATOR_ERROR_CONTRACT[
                        case_name
                    ],
                    400,
                )

        self.assertFalse(
            OPERATOR_ERROR_CONTRACT[
                "silently_ignore_invalid_filters"
            ]
        )

    def test_v233_rollback_links_are_navigation_only(self):
        self.assertTrue(
            OPERATOR_ROLLBACK_LINK_CONTRACT[
                "display_rollback_of"
            ]
        )
        self.assertTrue(
            OPERATOR_ROLLBACK_LINK_CONTRACT[
                "target_same_interface"
            ]
        )
        self.assertEqual(
            OPERATOR_ROLLBACK_LINK_CONTRACT[
                "target_filter"
            ],
            "event_id",
        )
        self.assertFalse(
            OPERATOR_ROLLBACK_LINK_CONTRACT[
                "preview_action_present"
            ]
        )
        self.assertFalse(
            OPERATOR_ROLLBACK_LINK_CONTRACT[
                "apply_action_present"
            ]
        )
        self.assertFalse(
            OPERATOR_ROLLBACK_LINK_CONTRACT[
                "mutation_present"
            ]
        )

    def test_v233_read_only_invariants_exclude_runtime_and_mutation(self):
        required = {
            "query service performs no create",
            "query service performs no update",
            "query service performs no delete",
            "view accepts GET and HEAD only",
            "view contains no delivery action",
            "view contains no rollback action",
            "view does not mutate notification timestamps",
            "view does not import the runtime recorder",
            "view does not import the persistence writer",
            "audit model remains unregistered in Django admin",
            "no migration",
            "no retention deletion",
            "no background worker",
        }

        self.assertTrue(
            required.issubset(
                set(READ_ONLY_INVARIANTS)
            )
        )

    def test_v233_audit_model_remains_unregistered_in_admin(self):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

    def test_v233_is_contract_only_until_v234_is_packaged(self):
        query_path = (
            self._backend_root()
            / PROPOSED_QUERY_MODULE
        )

        view_path = (
            self._backend_root()
            / PROPOSED_VIEW_MODULE
        )

        template_path = (
            self._backend_root()
            / PROPOSED_TEMPLATE
        )

        v234_test_path = (
            self._backend_root()
            / "listings"
            / (
                "test_saved_search_notification_persistent_"
                "audit_operator_read_interface_v234.py"
            )
        )

        urls_source = self._read_backend(
            "listings/urls.py"
        )

        if v234_test_path.exists():
            self.assertTrue(query_path.is_file())
            self.assertTrue(view_path.is_file())
            self.assertTrue(template_path.is_file())
            self.assertIn(
                PROPOSED_URL_PATH,
                urls_source,
            )
            self.assertIn(
                PROPOSED_URL_NAME,
                urls_source,
            )
        else:
            self.assertFalse(query_path.exists())
            self.assertFalse(view_path.exists())
            self.assertFalse(template_path.exists())
            self.assertNotIn(
                PROPOSED_URL_PATH,
                urls_source,
            )
            self.assertNotIn(
                PROPOSED_URL_NAME,
                urls_source,
            )

    def test_v233_contract_does_not_modify_runtime_surfaces(self):
        runtime_paths = (
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
            "V233_SAVED_SEARCH_NOTIFICATION_PERSISTENT_"
            "AUDIT_OPERATOR_READ_INTERFACE_CONTRACT"
        )

        for relative_path in runtime_paths:
            source = self._read_backend(relative_path)

            with self.subTest(relative_path=relative_path):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_v233_acceptance_gates_cover_security_and_privacy(self):
        required_gates = {
            "staff authentication is required",
            "authenticated non-staff users receive 403",
            "POST PUT PATCH and DELETE receive 405",
            "invalid filters fail closed with 400",
            "HTML pagination is bounded",
            "CSV export is bounded",
            "CSV formula injection is neutralized",
            "recipient and owner email are never exposed",
            "rendered email content is never exposed",
            "stored metadata is sanitized again on read",
            "no delivery or rollback action is exposed",
            "no timestamp mutation is possible",
            "no model or migration change is introduced",
            "existing runtime integration remains unchanged",
            "full regression remains green",
        }

        self.assertTrue(
            required_gates.issubset(
                set(IMPLEMENTATION_ACCEPTANCE_GATES)
            )
        )

    def test_v233_recent_persistence_and_runtime_files_remain_packaged(self):
        required_paths = (
            (
                "listings/"
                "saved_search_notification_audit_persistence.py"
            ),
            (
                "listings/"
                "saved_search_notification_audit_runtime.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_audit_"
                "persistence_model_migration_v229.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_audit_"
                "persistence_write_service_v230.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_audit_"
                "runtime_integration_contract_v231.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_audit_"
                "runtime_integration_v232.py"
            ),
        )

        for relative_path in required_paths:
            with self.subTest(relative_path=relative_path):
                self.assertTrue(
                    (
                        self._backend_root()
                        / relative_path
                    ).is_file()
                )

    def test_v233_next_lane_is_operator_read_interface_implementation(self):
        next_lane = "v234: saved-search notification persistent audit operator read-interface implementation"

        self.assertEqual(
            next_lane,
            "v234: saved-search notification persistent audit operator read-interface implementation",
        )
