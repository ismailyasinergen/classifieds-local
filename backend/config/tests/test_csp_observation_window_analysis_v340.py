from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile

from django.conf import settings
from django.test import SimpleTestCase

from config.csp_report_logging_v337 import (
    CSP_REPORT_EVIDENCE_KEYS_V337,
)
from scripts.analyze_csp_observation_window_v340 import (
    CSP_OBSERVATION_WINDOW_ANALYSIS_V340,
    CSP_WINDOW_INPUT_MAX_BYTES_V340,
    CSP_WINDOW_MAX_BUCKETS_V340,
    CSP_WINDOW_MAX_RECORDS_V340,
    CSP_WINDOW_OTHER_BUCKET_V340,
    CSP_WINDOW_MAX_SECONDS_V340,
    CSP_WINDOW_MIN_SECONDS_V340,
    CSP_WINDOW_REASON_CODES_V340,
    CSP_WINDOW_RECORD_KEYS_V340,
    CSP_WINDOW_RESULT_KEYS_V340,
    CSP_WINDOW_SUMMARY_KEYS_V340,
    _read_jsonl_stream_v340,
    analyze_csp_observation_window_v340,
    main,
)


class CspObservationWindowAnalysisV340Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.base_dir = Path(settings.BASE_DIR)
        cls.script_path = (
            cls.base_dir
            / "scripts"
            / "analyze_csp_observation_window_v340.py"
        )

    def approved_closeout(self):
        check_ids = (
            "expected_origin_valid",
            "readiness_evidence_valid",
            "edge_evidence_valid",
            "retention_evidence_valid",
            "delivery_evidence_valid",
            "log_evidence_valid",
            "smoke_evidence_linked",
            "enforcement_absent",
        )

        return {
            "marker": (
                "CSP_OBSERVATION_EVIDENCE_CLOSEOUT_AUDIT_V339"
            ),
            "status": "ready",
            "ready": True,
            "read_only": True,
            "checks": [
                {
                    "check_id": check_id,
                    "status": "ready",
                    "passed": True,
                    "reason_code": "ready",
                }
                for check_id in check_ids
            ],
            "ready_count": len(check_ids),
            "not_ready_count": 0,
        }

    def evidence(
        self,
        *,
        directive="script-src-attr",
        blocked_resource="inline",
        disposition="report",
        document_origin="https://example.test",
        source_origin="https://example.test",
        status_code=200,
        media_type="application/csp-report",
    ):
        values = {
            "media_type": media_type,
            "report_index": 1,
            "blocked_resource": blocked_resource,
            "column_number": 4,
            "disposition": disposition,
            "document_origin": document_origin,
            "effective_directive": directive,
            "line_number": 8,
            "source_origin": source_origin,
            "status_code": status_code,
            "violated_directive": directive,
        }

        return {
            key: values[key]
            for key in CSP_REPORT_EVIDENCE_KEYS_V337
        }

    def record(
        self,
        observed_at,
        **evidence_kwargs,
    ):
        return {
            "observed_at": observed_at,
            "event": "csp_violation_v334",
            "schema_version": 1,
            "evidence": self.evidence(
                **evidence_kwargs
            ),
        }

    def analyze(
        self,
        records,
        *,
        start="2026-07-23T10:00:00Z",
        end="2026-07-23T11:00:00Z",
        closeout=None,
    ):
        return analyze_csp_observation_window_v340(
            closeout_evidence=(
                self.approved_closeout()
                if closeout is None
                else closeout
            ),
            records=records,
            window_start=start,
            window_end=end,
        )

    def test_contract_constants_and_result_shape_are_fixed(
        self,
    ):
        result = self.analyze([])

        self.assertEqual(
            CSP_OBSERVATION_WINDOW_ANALYSIS_V340,
            "CSP_OBSERVATION_WINDOW_ANALYSIS_V340",
        )
        self.assertEqual(
            tuple(result),
            CSP_WINDOW_RESULT_KEYS_V340,
        )
        self.assertEqual(
            CSP_WINDOW_RECORD_KEYS_V340,
            (
                "observed_at",
                "event",
                "schema_version",
                "evidence",
            ),
        )
        self.assertEqual(
            CSP_WINDOW_SUMMARY_KEYS_V340,
            (
                "value",
                "count",
            ),
        )
        self.assertEqual(
            CSP_WINDOW_INPUT_MAX_BYTES_V340,
            1024 * 1024,
        )
        self.assertEqual(
            CSP_WINDOW_MAX_RECORDS_V340,
            10_000,
        )
        self.assertEqual(
            CSP_WINDOW_MIN_SECONDS_V340,
            60,
        )
        self.assertEqual(
            CSP_WINDOW_MAX_SECONDS_V340,
            7 * 24 * 60 * 60,
        )
        self.assertEqual(
            CSP_WINDOW_MAX_BUCKETS_V340,
            8,
        )
        self.assertEqual(
            CSP_WINDOW_OTHER_BUCKET_V340,
            "__other__",
        )
        self.assertTrue(
            {
                "analysis_ready",
                "record_invalid",
                "input_too_large",
            }.issubset(CSP_WINDOW_REASON_CODES_V340)
        )

    def test_approved_window_aggregates_safe_dimensions_deterministically(
        self,
    ):
        records = [
            self.record(
                "2026-07-23T10:10:00Z",
                directive="img-src",
                blocked_resource="https://cdn.example",
                disposition="report",
                status_code=200,
            ),
            self.record(
                "2026-07-23T10:20:00Z",
                directive="script-src-attr",
                blocked_resource="inline",
                disposition="report",
                status_code=0,
            ),
            self.record(
                "2026-07-23T10:30:00Z",
                directive="img-src",
                blocked_resource="data",
                disposition="enforce",
                status_code=None,
            ),
        ]

        result = self.analyze(records)

        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["read_only"])
        self.assertFalse(result["network_activity"])
        self.assertFalse(result["persistence"])
        self.assertFalse(result["enforcement"])
        self.assertEqual(result["input_record_count"], 3)
        self.assertEqual(result["included_record_count"], 3)
        self.assertEqual(result["excluded_record_count"], 0)
        self.assertEqual(
            result["directive_summary"],
            [
                {
                    "value": "img-src",
                    "count": 2,
                },
                {
                    "value": "script-src-attr",
                    "count": 1,
                },
            ],
        )
        self.assertEqual(
            result["blocked_resource_summary"],
            [
                {
                    "value": "data",
                    "count": 1,
                },
                {
                    "value": "inline",
                    "count": 1,
                },
                {
                    "value": "origin",
                    "count": 1,
                },
            ],
        )
        self.assertEqual(
            result["status_code_summary"],
            [
                {
                    "value": "2xx",
                    "count": 1,
                },
                {
                    "value": "none",
                    "count": 1,
                },
                {
                    "value": "zero",
                    "count": 1,
                },
            ],
        )

    def test_out_of_window_records_are_excluded_and_empty_window_is_ready(
        self,
    ):
        result = self.analyze(
            [
                self.record(
                    "2026-07-23T09:59:59Z"
                ),
                self.record(
                    "2026-07-23T11:00:00Z"
                ),
            ]
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["input_record_count"], 2)
        self.assertEqual(result["included_record_count"], 0)
        self.assertEqual(result["excluded_record_count"], 2)
        self.assertEqual(
            result["reason_codes"],
            [
                "analysis_ready",
                "no_records_in_window",
            ],
        )
        self.assertEqual(result["directive_summary"], [])

    def test_synthetic_records_are_separated_from_organic_records(
        self,
    ):
        synthetic_origin = (
            "https://v338-0123456789abcdef.invalid"
        )

        result = self.analyze(
            [
                self.record(
                    "2026-07-23T10:10:00Z",
                    document_origin=synthetic_origin,
                    source_origin=synthetic_origin,
                ),
                self.record(
                    "2026-07-23T10:20:00Z",
                ),
            ]
        )

        self.assertEqual(
            result["synthetic_record_count"],
            1,
        )
        self.assertEqual(
            result["organic_record_count"],
            1,
        )
        self.assertEqual(
            result["reason_codes"],
            ["analysis_ready"],
        )

        synthetic_only = self.analyze(
            [
                self.record(
                    "2026-07-23T10:10:00Z",
                    document_origin=synthetic_origin,
                    source_origin=synthetic_origin,
                )
            ]
        )

        self.assertEqual(
            synthetic_only["reason_codes"],
            [
                "analysis_ready",
                "synthetic_only_window",
            ],
        )

    def test_bucket_cardinality_is_bounded_with_other_bucket(
        self,
    ):
        records = [
            self.record(
                "2026-07-23T10:10:00Z",
                directive=f"x-directive-{index}",
            )
            for index in range(
                CSP_WINDOW_MAX_BUCKETS_V340 + 4
            )
        ]

        records.append(
            self.record(
                "2026-07-23T10:10:00Z",
                directive="other",
            )
        )

        result = self.analyze(records)
        summary = result["directive_summary"]

        self.assertEqual(
            len(summary),
            CSP_WINDOW_MAX_BUCKETS_V340,
        )
        self.assertEqual(
            summary[-1],
            {
                "value": CSP_WINDOW_OTHER_BUCKET_V340,
                "count": 6,
            },
        )
        self.assertIn(
            {
                "value": "other",
                "count": 1,
            },
            summary,
        )

        for item in summary:
            self.assertEqual(
                tuple(item),
                CSP_WINDOW_SUMMARY_KEYS_V340,
            )

    def test_unapproved_closeout_fails_closed(
        self,
    ):
        closeout = self.approved_closeout()
        closeout["checks"][0]["passed"] = False

        result = self.analyze(
            [],
            closeout=closeout,
        )

        self.assertFalse(result["ready"])
        self.assertEqual(
            result["reason_codes"],
            ["closeout_not_approved"],
        )
        self.assertEqual(result["input_record_count"], 0)

    def test_sorted_v339_cli_json_order_is_accepted(
        self,
    ):
        serialized = json.dumps(
            self.approved_closeout(),
            sort_keys=True,
            separators=(",", ":"),
        )

        sorted_closeout = json.loads(
            serialized
        )

        self.assertNotEqual(
            tuple(sorted_closeout),
            (
                "marker",
                "status",
                "ready",
                "read_only",
                "checks",
                "ready_count",
                "not_ready_count",
            ),
        )
        self.assertNotEqual(
            tuple(sorted_closeout["checks"][0]),
            (
                "check_id",
                "status",
                "passed",
                "reason_code",
            ),
        )

        result = self.analyze(
            [],
            closeout=sorted_closeout,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(
            result["status"],
            "ready",
        )
        self.assertEqual(
            result["reason_codes"],
            [
                "analysis_ready",
                "no_records_in_window",
            ],
        )

    def test_window_bounds_and_timezone_validation_fail_closed(
        self,
    ):
        cases = (
            (
                "2026-07-23T10:00:00",
                "2026-07-23T11:00:00Z",
                "window_invalid",
            ),
            (
                "2026-07-23T11:00:00Z",
                "2026-07-23T10:00:00Z",
                "window_invalid",
            ),
            (
                "2026-07-23T10:00:00Z",
                "2026-07-23T10:00:30Z",
                "window_too_short",
            ),
            (
                "2026-07-01T00:00:00Z",
                "2026-07-09T00:00:00Z",
                "window_too_long",
            ),
            (
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00.000001Z",
                "window_too_long",
            ),
        )

        for start, end, reason in cases:
            with self.subTest(
                start=start,
                end=end,
            ):
                result = self.analyze(
                    [],
                    start=start,
                    end=end,
                )

                self.assertFalse(
                    result["ready"]
                )
                self.assertEqual(
                    result["reason_codes"],
                    [reason],
                )

    def test_invalid_record_schema_or_v337_evidence_fails_closed(
        self,
    ):
        valid = self.record(
            "2026-07-23T10:10:00Z"
        )

        invalid_cases = []

        extra_record_key = dict(valid)
        extra_record_key["raw_report"] = "secret"
        invalid_cases.append(extra_record_key)

        invalid_event = dict(valid)
        invalid_event["event"] = "different"
        invalid_cases.append(invalid_event)

        invalid_evidence = dict(valid)
        invalid_evidence["evidence"] = dict(
            valid["evidence"]
        )
        invalid_evidence["evidence"][
            "blocked_resource"
        ] = "https://example.test/private/path?token=x"
        invalid_cases.append(invalid_evidence)

        for record in invalid_cases:
            with self.subTest(record=record):
                result = self.analyze(
                    [record]
                )

                self.assertFalse(
                    result["ready"]
                )
                self.assertEqual(
                    result["reason_codes"],
                    ["record_invalid"],
                )

    def test_bounded_stream_reader_rejects_oversized_and_excess_records(
        self,
    ):
        values, error = _read_jsonl_stream_v340(
            io.BytesIO(
                b"x"
                * (
                    CSP_WINDOW_INPUT_MAX_BYTES_V340
                    + 1
                )
            )
        )

        self.assertIsNone(values)
        self.assertEqual(error, "input_too_large")

        line = json.dumps(
            self.record(
                "2026-07-23T10:10:00Z"
            ),
            separators=(",", ":"),
        ).encode("utf-8")

        values, error = _read_jsonl_stream_v340(
            io.BytesIO(
                b"\n".join(
                    [line]
                    * (
                        CSP_WINDOW_MAX_RECORDS_V340
                        + 1
                    )
                )
            )
        )

        self.assertIsNone(values)
        self.assertIn(
            error,
            {
                "input_too_large",
                "record_limit_exceeded",
            },
        )

    def test_cli_json_is_deterministic_and_strict(
        self,
    ):
        closeout = json.dumps(
            self.approved_closeout(),
            separators=(",", ":"),
        ).encode("utf-8")

        record = json.dumps(
            self.record(
                "2026-07-23T10:10:00Z"
            ),
            separators=(",", ":"),
        ).encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            closeout_path = (
                Path(directory)
                / "closeout.json"
            )
            closeout_path.write_bytes(closeout)

            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(
                    [
                        "--closeout-json",
                        str(closeout_path),
                        "--window-start",
                        "2026-07-23T10:00:00Z",
                        "--window-end",
                        "2026-07-23T11:00:00Z",
                        "--json",
                        "--strict",
                    ],
                    stdin=io.BytesIO(record),
                )

        self.assertEqual(exit_code, 0)

        payload = json.loads(
            output.getvalue()
        )

        self.assertTrue(payload["ready"])
        self.assertEqual(
            payload["included_record_count"],
            1,
        )
        self.assertNotIn(
            "https://example.test",
            output.getvalue(),
        )

    def test_result_never_outputs_origins_paths_queries_or_samples(
        self,
    ):
        result = self.analyze(
            [
                self.record(
                    "2026-07-23T10:10:00Z",
                    blocked_resource=(
                        "https://cdn.example"
                    ),
                    document_origin=(
                        "https://private.example"
                    ),
                    source_origin=(
                        "https://source.example"
                    ),
                )
            ]
        )

        rendered = json.dumps(
            result,
            sort_keys=True,
        )

        for forbidden in (
            "cdn.example",
            "private.example",
            "source.example",
            "script-sample",
            "raw_report",
            "?",
            "#",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    rendered,
                )

    def test_source_has_no_network_write_database_or_enforcement_path(
        self,
    ):
        source = self.script_path.read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "import requests",
            "from urllib",
            "import socket",
            "import subprocess",
            "django.db",
            ".write_text(",
            ".write_bytes(",
            "Content-Security-Policy",
            "CSP_ENFORCEMENT_ENABLED",
            "os.environ",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    source,
                )

        self.assertIn(
            '"network_activity": False',
            source,
        )
        self.assertIn(
            '"persistence": False',
            source,
        )
        self.assertIn(
            '"enforcement": False',
            source,
        )

    def test_v340_adds_no_database_migration(
        self,
    ):
        matches = []

        for app_name in (
            "accounts",
            "categories",
            "listings",
            "pages",
        ):
            matches.extend(
                (
                    self.base_dir
                    / app_name
                    / "migrations"
                ).glob("*v340*.py")
            )

        self.assertEqual(matches, [])
