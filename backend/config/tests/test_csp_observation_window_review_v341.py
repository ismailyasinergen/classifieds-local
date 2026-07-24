from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile

from django.test import SimpleTestCase

from scripts.analyze_csp_observation_window_v340 import (
    CSP_OBSERVATION_WINDOW_ANALYSIS_V340,
)
from scripts.review_csp_observation_window_v341 import (
    CSP_OBSERVATION_WINDOW_REVIEW_V341,
    CSP_REVIEW_INPUT_MAX_BYTES_V341,
    CSP_REVIEW_MAX_SYNTHETIC_RECORDS_V341,
    CSP_REVIEW_MIN_ORGANIC_RECORDS_V341,
    CSP_REVIEW_MIN_WINDOW_SECONDS_V341,
    CSP_REVIEW_RESULT_KEYS_V341,
    CSP_REVIEW_THRESHOLD_KEYS_V341,
    _read_bounded_json_v341,
    main,
    review_csp_observation_window_v341,
)


class CspObservationWindowReviewV341Tests(
    SimpleTestCase
):
    maxDiff = None

    def summary(
        self,
        *,
        organic=25,
        synthetic=0,
        seconds=86400,
        excluded=0,
    ):
        included = organic + synthetic
        start = datetime(
            2026, 7, 20, tzinfo=timezone.utc
        )
        end = start + timedelta(seconds=seconds)

        bucket = (
            [{"value": "img-src", "count": included}]
            if included
            else []
        )

        reasons = ["analysis_ready"]
        if included == 0:
            reasons.append("no_records_in_window")
        elif synthetic == included:
            reasons.append("synthetic_only_window")

        return {
            "marker":
                CSP_OBSERVATION_WINDOW_ANALYSIS_V340,
            "status": "ready",
            "ready": True,
            "read_only": True,
            "network_activity": False,
            "persistence": False,
            "enforcement": False,
            "window_start": start.isoformat().replace(
                "+00:00", "Z"
            ),
            "window_end": end.isoformat().replace(
                "+00:00", "Z"
            ),
            "window_seconds": seconds,
            "input_record_count": included + excluded,
            "included_record_count": included,
            "excluded_record_count": excluded,
            "synthetic_record_count": synthetic,
            "organic_record_count": organic,
            "directive_summary": deepcopy(bucket),
            "blocked_resource_summary": deepcopy(bucket),
            "disposition_summary": deepcopy(bucket),
            "media_type_summary": deepcopy(bucket),
            "status_code_summary": deepcopy(bucket),
            "reason_codes": reasons,
        }

    def test_contract_is_fixed(self):
        result = review_csp_observation_window_v341({})

        self.assertEqual(
            CSP_OBSERVATION_WINDOW_REVIEW_V341,
            "CSP_OBSERVATION_WINDOW_REVIEW_V341",
        )
        self.assertEqual(
            CSP_REVIEW_INPUT_MAX_BYTES_V341,
            128 * 1024,
        )
        self.assertEqual(
            CSP_REVIEW_MIN_WINDOW_SECONDS_V341,
            24 * 60 * 60,
        )
        self.assertEqual(
            CSP_REVIEW_MIN_ORGANIC_RECORDS_V341,
            25,
        )
        self.assertEqual(
            CSP_REVIEW_MAX_SYNTHETIC_RECORDS_V341,
            0,
        )
        self.assertEqual(
            tuple(result),
            CSP_REVIEW_RESULT_KEYS_V341,
        )
        self.assertEqual(
            tuple(result["thresholds"]),
            CSP_REVIEW_THRESHOLD_KEYS_V341,
        )

    def test_ready_boundary_is_safe(self):
        source = self.summary(excluded=3)
        before = deepcopy(source)

        result = review_csp_observation_window_v341(
            source
        )

        self.assertEqual(source, before)
        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(
            result["recommendation"],
            "review_clean_organic_findings",
        )
        self.assertEqual(
            result["reason_codes"],
            ["review_ready"],
        )
        self.assertFalse(result["automatic_action"])
        self.assertFalse(result["enforcement"])
        self.assertFalse(result["gate_change"])
        self.assertFalse(
            result["configuration_mutation"]
        )

    def test_invalid_v340_summaries_fail_closed(self):
        valid = self.summary()
        invalid_values = []

        for key, value in (
            ("marker", "wrong"),
            ("status", "not_ready"),
            ("ready", False),
            ("read_only", False),
            ("network_activity", True),
            ("persistence", True),
            ("enforcement", True),
            ("organic_record_count", 24),
        ):
            changed = deepcopy(valid)
            changed[key] = value
            invalid_values.append(changed)

        missing_key = deepcopy(valid)
        missing_key.pop("reason_codes")
        invalid_values.append(missing_key)

        extra_key = deepcopy(valid)
        extra_key["unexpected"] = True
        invalid_values.append(extra_key)

        for value in invalid_values:
            with self.subTest(value=value):
                result = review_csp_observation_window_v341(
                    value
                )
                self.assertEqual(
                    result["status"],
                    "not_ready",
                )
                self.assertFalse(result["ready"])
                self.assertEqual(
                    result["recommendation"],
                    "reject_summary",
                )
                self.assertEqual(
                    result["reason_codes"],
                    ["summary_invalid"],
                )

    def test_insufficient_evidence_outcomes_are_distinct(
        self,
    ):
        cases = (
            (
                self.summary(seconds=86399),
                "window_too_short_for_review",
            ),
            (
                self.summary(organic=0),
                "no_records_in_window",
            ),
            (
                self.summary(organic=0, synthetic=25),
                "synthetic_only_window",
            ),
            (
                self.summary(organic=25, synthetic=1),
                "synthetic_records_present",
            ),
            (
                self.summary(organic=24),
                "organic_record_count_below_threshold",
            ),
        )

        for source, expected_reason in cases:
            with self.subTest(reason=expected_reason):
                result = review_csp_observation_window_v341(
                    source
                )
                self.assertEqual(
                    result["status"],
                    "insufficient_evidence",
                )
                self.assertFalse(result["ready"])
                self.assertEqual(
                    result["recommendation"],
                    "continue_observation",
                )
                self.assertEqual(
                    result["reason_codes"],
                    [expected_reason],
                )

    def test_valid_v340_overflow_summary_is_accepted(
        self,
    ):
        bucket = [
            {"value": "a", "count": 10},
            {"value": "b", "count": 9},
            {"value": "c", "count": 8},
            {"value": "d", "count": 7},
            {"value": "e", "count": 6},
            {"value": "f", "count": 5},
            {"value": "g", "count": 4},
            {"value": "__other__", "count": 20},
        ]

        source = self.summary(organic=69)

        for field in (
            "directive_summary",
            "blocked_resource_summary",
            "disposition_summary",
            "media_type_summary",
            "status_code_summary",
        ):
            source[field] = deepcopy(bucket)

        result = review_csp_observation_window_v341(
            source
        )

        self.assertTrue(result["ready"])
        self.assertEqual(
            result["reason_codes"],
            ["review_ready"],
        )


    def test_bounded_summary_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            valid = root / "valid.json"
            valid.write_text(
                json.dumps(self.summary()),
                encoding="utf-8",
            )
            value, error = _read_bounded_json_v341(
                valid
            )
            self.assertIsNone(error)
            self.assertEqual(value, self.summary())

            malformed = root / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            value, error = _read_bounded_json_v341(
                malformed
            )
            self.assertIsNone(value)
            self.assertEqual(
                error,
                "summary_input_unreadable",
            )

            missing = root / "missing.json"
            value, error = _read_bounded_json_v341(
                missing
            )
            self.assertIsNone(value)
            self.assertEqual(
                error,
                "summary_input_unreadable",
            )

            oversized = root / "oversized.json"
            oversized.write_bytes(
                b"x"
                * (CSP_REVIEW_INPUT_MAX_BYTES_V341 + 1)
            )
            value, error = _read_bounded_json_v341(
                oversized
            )
            self.assertIsNone(value)
            self.assertEqual(
                error,
                "summary_input_too_large",
            )


    def test_cli_ready_json_and_strict_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "ready.json"
            summary_path.write_text(
                json.dumps(self.summary()),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "--summary-json",
                        str(summary_path),
                        "--json",
                        "--strict",
                    ]
                )

            raw_output = output.getvalue().strip()
            payload = json.loads(raw_output)

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["ready"])
            self.assertEqual(
                payload["reason_codes"],
                ["review_ready"],
            )
            self.assertEqual(
                raw_output,
                json.dumps(
                    payload,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )

    def test_cli_invalid_summary_fails_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "invalid.json"
            summary_path.write_text(
                "{}",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "--summary-json",
                        str(summary_path),
                        "--json",
                        "--strict",
                    ]
                )

            payload = json.loads(output.getvalue())

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["ready"])
            self.assertEqual(
                payload["recommendation"],
                "reject_summary",
            )
            self.assertEqual(
                payload["reason_codes"],
                ["summary_invalid"],
            )

    def test_count_time_and_reason_contracts_fail_closed(
        self,
    ):
        valid = self.summary()
        invalid_values = []

        changes = (
            (
                "window_start",
                "2026-07-20T00:00:00",
            ),
            (
                "window_end",
                "2026-07-21T00:00:00+00:00",
            ),
            ("window_seconds", 86399),
            ("input_record_count", 26),
            ("organic_record_count", True),
            (
                "reason_codes",
                [
                    "analysis_ready",
                    "no_records_in_window",
                ],
            ),
        )

        for key, value in changes:
            changed = deepcopy(valid)
            changed[key] = value
            invalid_values.append(changed)

        inconsistent = deepcopy(valid)
        inconsistent["synthetic_record_count"] = 1
        invalid_values.append(inconsistent)

        for value in invalid_values:
            with self.subTest(value=value):
                result = review_csp_observation_window_v341(
                    value
                )
                self.assertEqual(
                    result["reason_codes"],
                    ["summary_invalid"],
                )
                self.assertEqual(
                    result["recommendation"],
                    "reject_summary",
                )

    def test_summary_bucket_contract_fails_closed(
        self,
    ):
        malformed_buckets = (
            [
                {"value": "a", "count": 2},
                {"value": "a", "count": 1},
            ],
            [
                {"value": "a", "count": 1},
                {"value": "b", "count": 2},
            ],
            [{"value": "a", "count": 2}],
            [{"value": "", "count": 3}],
            [{"value": "a", "count": 0}],
            [{"value": "__other__", "count": 3}],
        )

        for bucket in malformed_buckets:
            with self.subTest(bucket=bucket):
                source = self.summary(organic=3)
                source["directive_summary"] = bucket

                result = review_csp_observation_window_v341(
                    source
                )

                self.assertEqual(
                    result["status"],
                    "not_ready",
                )
                self.assertEqual(
                    result["reason_codes"],
                    ["summary_invalid"],
                )

    def test_cli_input_errors_fail_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            malformed = root / "malformed.json"
            malformed.write_text("{", encoding="utf-8")

            oversized = root / "oversized.json"
            oversized.write_bytes(
                b"x"
                * (CSP_REVIEW_INPUT_MAX_BYTES_V341 + 1)
            )

            cases = (
                (
                    malformed,
                    "summary_input_unreadable",
                ),
                (
                    oversized,
                    "summary_input_too_large",
                ),
            )

            for summary_path, expected_reason in cases:
                with self.subTest(reason=expected_reason):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        exit_code = main(
                            [
                                "--summary-json",
                                str(summary_path),
                                "--json",
                                "--strict",
                            ]
                        )

                    payload = json.loads(
                        output.getvalue()
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["ready"])
                    self.assertIsNone(
                        payload["source_marker"]
                    )
                    self.assertEqual(
                        payload["reason_codes"],
                        [expected_reason],
                    )

    def test_text_output_is_operator_facing_and_safe(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "ready.json"
            summary_path.write_text(
                json.dumps(self.summary()),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "--summary-json",
                        str(summary_path),
                    ]
                )

            rendered = output.getvalue()

            self.assertEqual(exit_code, 0)
            self.assertIn(
                CSP_OBSERVATION_WINDOW_REVIEW_V341,
                rendered,
            )
            self.assertIn("status=ready", rendered)
            self.assertIn(
                "recommendation="
                "review_clean_organic_findings",
                rendered,
            )
            self.assertIn(
                "automatic_action=false",
                rendered,
            )
            self.assertIn(
                "reason_codes=review_ready",
                rendered,
            )
            self.assertNotIn("img-src", rendered)
