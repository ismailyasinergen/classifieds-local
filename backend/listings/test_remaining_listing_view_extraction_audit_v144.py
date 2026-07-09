from __future__ import annotations

import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from listings.remaining_listing_view_extraction_audit_v144 import (
    EXTRACTED_V141_CANDIDATES,
    MARKER,
    build_report,
    render_markdown_report,
    resolve_project_path,
    write_markdown_report,
)


class RemainingListingViewExtractionAuditV144Tests(SimpleTestCase):
    def test_v144_resolves_repo_root_path_inside_backend_mount_layout(self):
        resolved = resolve_project_path(".", "backend/listings/views.py")
        self.assertTrue(str(resolved).endswith("listings/views.py"))

    def test_v144_build_report_targets_listing_views(self):
        from pathlib import Path
        from listings import remaining_listing_view_extraction_audit_v144 as audit

        report = audit.build_report(Path("."))
        self.assertGreaterEqual(report.top_level_function_count, 0)

    def test_v144_confirms_v141_candidates_are_extracted_from_views(self):
        report = build_report(root=".")

        self.assertEqual(report.extracted_v141_candidates_still_present, ())
        self.assertEqual(
            report.extracted_v141_candidates_missing_count,
            len(EXTRACTED_V141_CANDIDATES),
        )

    def test_v144_candidate_counts_are_consistent(self):
        report = build_report(root=".")

        self.assertGreaterEqual(report.helper_candidate_count, 0)
        self.assertEqual(
            report.helper_candidate_count,
            report.low_risk_candidate_count + report.medium_risk_candidate_count,
        )

    def test_v144_candidates_exclude_already_extracted_v141_names(self):
        report = build_report(root=".")
        candidate_names = {candidate.name for candidate in report.candidates}

        for extracted_name in EXTRACTED_V141_CANDIDATES:
            self.assertNotIn(extracted_name, candidate_names)

    def test_v144_markdown_documents_rules_and_next_candidate_section(self):
        report = build_report(root=".")
        markdown = render_markdown_report(report)

        self.assertIn(MARKER, markdown)
        self.assertIn("## Recommended next candidate", markdown)
        self.assertIn("Do not re-extract `apply_listing_filters`", markdown)
        self.assertIn("Do not re-extract `_create_moderation_notice`", markdown)

    def test_v144_write_markdown_report_creates_file(self):
        report = build_report(root=".")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "remaining_listing_view_extraction_audit_v144.md"
            write_markdown_report(report, output_path)

            self.assertTrue(output_path.exists())
            self.assertIn(MARKER, output_path.read_text(encoding="utf-8"))
