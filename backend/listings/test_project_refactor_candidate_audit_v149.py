from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import project_refactor_candidate_audit_v149 as audit


class ProjectRefactorCandidateAuditV149Tests(SimpleTestCase):
    def test_v149_build_file_report_counts_python_structure(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "backend" / "sample" / "views.py"
            sample.parent.mkdir(parents=True)
            sample.write_text(
                "\n".join(
                    [
                        "import os",
                        "from pathlib import Path",
                        "",
                        "def sample_view(request):",
                        "    return request",
                        "",
                        "def helper_name(value):",
                        "    return value",
                        "",
                        "class SampleView:",
                        "    def get(self):",
                        "        return None",
                    ]
                ),
                encoding="utf-8",
            )

            report = audit.build_file_report(root, sample)

        self.assertEqual(report.path, Path("backend/sample/views.py"))
        self.assertEqual(report.top_level_function_count, 2)
        self.assertEqual(report.top_level_class_count, 1)
        self.assertEqual(report.method_count, 1)
        self.assertEqual(report.import_count, 2)
        self.assertEqual(report.view_like_function_count, 1)

    def test_v149_skips_tests_and_migrations(self):
        self.assertTrue(audit.should_skip_path(Path("backend/listings/migrations/0001_initial.py")))
        self.assertTrue(audit.should_skip_path(Path("backend/listings/test_example.py")))
        self.assertTrue(audit.should_skip_path(Path("backend/_dev_backups/example.py")))
        self.assertTrue(audit.should_skip_path(Path("backend/listings/large_view_refactor_audit_v140.py")))
        self.assertFalse(audit.should_skip_path(Path("backend/listings/views.py")))

    def test_v149_real_project_report_finds_active_python_files(self):
        report = audit.build_project_report(Path("."))

        self.assertGreater(report.scanned_file_count, 0)
        self.assertEqual(report.parse_error_count, 0)

        paths = {item.path.as_posix() for item in report.reports}
        self.assertTrue(
            {"backend/listings/views.py", "listings/views.py"} & paths,
            paths,
        )

    def test_v149_report_recommends_parseable_candidate_when_project_has_files(self):
        report = audit.build_project_report(Path("."))

        self.assertIsNotNone(report.recommended_next_candidate)
        self.assertIsNone(report.recommended_next_candidate.syntax_error)

    def test_v149_markdown_documents_non_goals_and_safe_sequencing(self):
        report = audit.build_project_report(Path("."))
        markdown = audit.render_markdown(report)

        self.assertIn("PROJECT_REFACTOR_CANDIDATE_AUDIT_V149", markdown)
        self.assertIn("## Non-goals", markdown)
        self.assertIn("Do not move code", markdown)
        self.assertIn("## Safe sequencing rule", markdown)
        self.assertIn("## Top candidates", markdown)

    def test_v149_write_markdown_report_creates_file(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "audit.md"
            report = audit.build_project_report(Path("."))
            written_path = audit.write_markdown_report(report, output_path)

            self.assertEqual(written_path, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn(
                "PROJECT_REFACTOR_CANDIDATE_AUDIT_V149",
                output_path.read_text(encoding="utf-8"),
            )
