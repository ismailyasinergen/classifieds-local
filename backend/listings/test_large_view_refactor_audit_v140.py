from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import large_view_refactor_audit_v140 as audit


class LargeViewRefactorAuditV140Tests(SimpleTestCase):
    def test_v140_targets_known_large_active_view_files(self):
        self.assertIn(Path("backend/accounts/appeal_views.py"), audit.TARGET_ACTIVE_VIEW_FILES)
        self.assertIn(Path("backend/listings/views.py"), audit.TARGET_ACTIVE_VIEW_FILES)

    def test_v140_keeps_dev_backup_reference_only(self):
        self.assertIn(
            Path("backend/_dev_backups/appeal_views_before_override_cleanup.py"),
            audit.REFERENCE_ONLY_FILES,
        )

    def test_v140_parses_top_level_definitions_from_sample_view_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "backend" / "listings" / "views.py"
            sample.parent.mkdir(parents=True)
            sample.write_text(
                "from django.contrib.auth.decorators import login_required\n\n"
                "def _helper():\n"
                "    return 1\n\n"
                "@login_required\n"
                "def listing_dashboard(request):\n"
                "    return None\n\n"
                "class ListingViewMixin:\n"
                "    pass\n",
                encoding="utf-8",
            )

            definitions = audit.parse_definitions(sample)
            by_name = {definition.name: definition for definition in definitions}

            self.assertEqual(by_name["_helper"].category, "private_helper")
            self.assertEqual(by_name["listing_dashboard"].category, "function_view")
            self.assertEqual(by_name["ListingViewMixin"].category, "class_based_view_or_mixin")

    def test_v140_build_file_report_counts_views_helpers_and_classes(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "backend" / "accounts" / "appeal_views.py"
            sample.parent.mkdir(parents=True)
            sample.write_text(
                "def _appeal_helper():\n"
                "    return 1\n\n"
                "def appeal_queue(request):\n"
                "    return None\n\n"
                "class AppealExportView:\n"
                "    pass\n",
                encoding="utf-8",
            )

            report = audit.build_file_report(root, Path("backend/accounts/appeal_views.py"))

            self.assertTrue(report.exists)
            self.assertEqual(report.function_view_count, 1)
            self.assertEqual(report.class_based_view_count, 1)
            self.assertEqual(report.helper_count, 1)

    def test_v140_markdown_report_documents_non_goals_and_safe_order(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative in audit.TARGET_ACTIVE_VIEW_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("def sample_view(request):\n    return None\n", encoding="utf-8")

            report = audit.build_audit(root)
            markdown = audit.format_markdown_report(report)

            self.assertIn("Recommended safe refactor order", markdown)
            self.assertIn("v140 non-goals", markdown)
            self.assertIn("Do not change views, URLs, templates, models, migrations, or user behavior.", markdown)
            self.assertIn("backend/accounts/appeal_views.py", markdown)
            self.assertIn("backend/listings/views.py", markdown)

    def test_v140_write_markdown_report_creates_docs_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative in audit.TARGET_ACTIVE_VIEW_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("def sample_view(request):\n    return None\n", encoding="utf-8")

            output = audit.write_markdown_report(root, Path("docs/large_active_view_refactor_plan_v140.md"))

            self.assertTrue(output.exists())
            self.assertIn("v140 Large Active View File Refactor Planning", output.read_text(encoding="utf-8"))

    def test_v140_real_project_report_sees_targets_when_available(self):
        root = Path(".")
        report = audit.build_audit(root)

        active_paths = [item.path for item in report.active_files]
        self.assertEqual(active_paths, list(audit.TARGET_ACTIVE_VIEW_FILES))

        existing_targets = [item for item in report.active_files if item.exists]
        self.assertEqual(len(existing_targets), 2)

        for item in existing_targets:
            self.assertGreater(item.total_lines, 0)

    def test_v140_resolves_repo_root_paths_inside_backend_mount_layout(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            backend_mount_file = root / "accounts" / "appeal_views.py"
            backend_mount_file.parent.mkdir(parents=True)
            backend_mount_file.write_text("def appeal_queue(request):\n    return None\n", encoding="utf-8")

            resolved = audit.resolve_project_file_path(
                root,
                Path("backend/accounts/appeal_views.py"),
            )

            self.assertEqual(resolved, backend_mount_file)
            report = audit.build_file_report(root, Path("backend/accounts/appeal_views.py"))
            self.assertTrue(report.exists)
            self.assertEqual(report.function_view_count, 1)
