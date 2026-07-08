from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import listing_view_helper_extraction_audit_v141 as audit


class ListingViewHelperExtractionAuditV141Tests(SimpleTestCase):
    def test_v141_targets_listing_views_file(self):
        self.assertEqual(audit.LISTING_VIEW_TARGET, Path("backend/listings/views.py"))

    def test_v141_resolves_repo_root_path_inside_backend_mount_layout(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mounted_file = root / "listings" / "views.py"
            mounted_file.parent.mkdir(parents=True)
            mounted_file.write_text("def sample_view(request):\n    return None\n", encoding="utf-8")

            resolved = audit.resolve_project_file_path(root, Path("backend/listings/views.py"))

            self.assertEqual(resolved, mounted_file)

    def test_v141_classifies_sample_helpers_and_view_like_functions(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "backend" / "listings" / "views.py"
            sample.parent.mkdir(parents=True)
            sample.write_text(
                "from django.contrib.auth.decorators import login_required\n\n"
                "def _private_helper(value):\n"
                "    return value\n\n"
                "def build_filter_query(params):\n"
                "    return params\n\n"
                "@login_required\n"
                "def seller_dashboard(request):\n"
                "    return None\n\n"
                "def listing_detail(request, slug):\n"
                "    return None\n",
                encoding="utf-8",
            )

            report = audit.build_report(root)
            by_name = {item.name: item for item in report.candidates}

            self.assertEqual(report.view_like_function_count, 2)
            self.assertEqual(by_name["_private_helper"].category, "private_helper")
            self.assertEqual(by_name["build_filter_query"].category, "query_or_format_helper")
            self.assertEqual(by_name["_private_helper"].risk, "low")
            self.assertEqual(by_name["build_filter_query"].risk, "low")

    def test_v141_excludes_request_first_functions_from_candidates(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "backend" / "listings" / "views.py"
            sample.parent.mkdir(parents=True)
            sample.write_text(
                "def listing_detail(request, slug):\n"
                "    return None\n\n"
                "def _helper(slug):\n"
                "    return slug\n",
                encoding="utf-8",
            )

            report = audit.build_report(root)
            candidate_names = {item.name for item in report.candidates}

            self.assertNotIn("listing_detail", candidate_names)
            self.assertIn("_helper", candidate_names)

    def test_v141_markdown_documents_non_goals_and_v142_rule(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "backend" / "listings" / "views.py"
            sample.parent.mkdir(parents=True)
            sample.write_text("def _helper():\n    return 1\n", encoding="utf-8")

            report = audit.build_report(root)
            markdown = audit.format_markdown_report(report)

            self.assertIn("Recommended v142 extraction rule", markdown)
            self.assertIn("v141 non-goals", markdown)
            self.assertIn("Do not move code out of `backend/listings/views.py` in this checkpoint.", markdown)

    def test_v141_write_markdown_report_creates_docs_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "backend" / "listings" / "views.py"
            sample.parent.mkdir(parents=True)
            sample.write_text("def _helper():\n    return 1\n", encoding="utf-8")

            output = audit.write_markdown_report(root, Path("docs/listing_view_helper_extraction_candidates_v141.md"))

            self.assertTrue(output.exists())
            self.assertIn("v141 Listing View Helper Extraction Candidates", output.read_text(encoding="utf-8"))

    def test_v141_real_project_report_finds_listing_views_candidates(self):
        report = audit.build_report(Path("."))

        self.assertTrue(report.exists)
        self.assertGreater(report.total_lines, 0)
        self.assertGreater(report.top_level_function_count, 0)
        self.assertGreaterEqual(report.helper_candidate_count, 1)
        self.assertGreaterEqual(report.low_risk_candidate_count, 1)
