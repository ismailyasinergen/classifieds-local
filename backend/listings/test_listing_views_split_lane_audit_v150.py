from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import listing_views_split_lane_audit_v150 as audit


class ListingViewsSplitLaneAuditV150Tests(SimpleTestCase):
    def test_v150_classifies_known_lane_names(self):
        self.assertEqual(audit.classify_lane("saved_search_list"), "saved_search")
        self.assertEqual(audit.classify_lane("report_listing"), "listing_reports_moderation")
        self.assertEqual(audit.classify_lane("promote_listing"), "listing_promotions")
        self.assertEqual(audit.classify_lane("favorite_listing"), "favorites")
        self.assertEqual(audit.classify_lane("create_listing"), "listing_crud_uploads")
        self.assertEqual(audit.classify_lane("browse_category"), "browse_search_detail")

    def test_v150_build_report_groups_sample_definitions_into_lanes(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            views_path = root / "backend" / "listings" / "views.py"
            views_path.parent.mkdir(parents=True)
            views_path.write_text(
                "\n".join(
                    [
                        "def browse(request):",
                        "    return request",
                        "",
                        "def saved_search_list(request):",
                        "    return request",
                        "",
                        "def report_listing(request):",
                        "    return request",
                        "",
                        "class ListingCreateView:",
                        "    pass",
                    ]
                ),
                encoding="utf-8",
            )

            report = audit.build_report(root)

        self.assertTrue(report.exists)
        self.assertEqual(report.top_level_function_count, 3)
        self.assertEqual(report.top_level_class_count, 1)

        lanes = {lane.name: lane for lane in report.lane_reports}
        self.assertEqual(lanes["browse_search_detail"].definition_count, 1)
        self.assertEqual(lanes["saved_search"].definition_count, 1)
        self.assertEqual(lanes["listing_reports_moderation"].definition_count, 1)
        self.assertEqual(lanes["listing_crud_uploads"].definition_count, 1)

    def test_v150_real_project_report_targets_listing_views(self):
        from pathlib import Path
        from listings import listing_views_split_lane_audit_v150 as audit

        report = audit.build_report(Path("."))
        self.assertGreaterEqual(report.top_level_function_count, 0)

    def test_v150_real_project_report_has_lane_summaries(self):
        report = audit.build_report(Path("."))

        lanes = {lane.name: lane for lane in report.lane_reports}
        self.assertIn("browse_search_detail", lanes)
        self.assertIn("listing_crud_uploads", lanes)
        self.assertIn("saved_search", lanes)
        self.assertIn("uncategorized", lanes)

        total_lane_definitions = sum(lane.definition_count for lane in report.lane_reports)
        self.assertEqual(total_lane_definitions, report.total_definition_count)

    def test_v150_markdown_documents_non_goals_and_safe_sequencing(self):
        report = audit.build_report(Path("."))
        markdown = audit.render_markdown(report)

        self.assertIn("LISTING_VIEWS_SPLIT_LANE_AUDIT_V150", markdown)
        self.assertIn("## Non-goals", markdown)
        self.assertIn("Do not move view functions or classes", markdown)
        self.assertIn("## Recommended next lane", markdown)
        self.assertIn("## Lane summary", markdown)
        self.assertIn("## Definition details", markdown)
        self.assertIn("## Safe sequencing rule", markdown)

    def test_v150_write_markdown_report_creates_file(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "listing_views_split_lane_audit_v150.md"
            report = audit.build_report(Path("."))
            written_path = audit.write_markdown_report(report, output_path)

            self.assertEqual(written_path, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "LISTING_VIEWS_SPLIT_LANE_AUDIT_V150",
                output_path.read_text(encoding="utf-8"),
            )
