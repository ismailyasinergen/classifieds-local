from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import project_hygiene_audit_v139 as audit


class ProjectHygieneAuditCleanupV139Tests(SimpleTestCase):
    def test_v139_classifies_reference_html_and_downloaded_js_as_reference_snapshots(self):
        reference_path = Path(
            "backend/reference_html/sahibinden/emlak_konut_daire_files/gtm.js.download"
        )
        minified_reference_path = Path(
            "backend/reference_html/sahibinden/emlak_konut_daire_files/js"
        )

        self.assertEqual(audit.classify_path(reference_path), "reference_snapshot")
        self.assertEqual(audit.classify_path(minified_reference_path), "reference_snapshot")

    def test_v139_classifies_dev_backups_separately_from_active_source(self):
        backup_path = Path("backend/_dev_backups/appeal_views_before_override_cleanup.py")

        self.assertEqual(audit.classify_path(backup_path), "dev_backup")

    def test_v139_classifies_active_app_code_as_active_source(self):
        active_path = Path("backend/listings/views.py")

        self.assertEqual(audit.classify_path(active_path), "active_source")

    def test_v139_build_report_ignores_reference_conflict_like_noise(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            active_file = root / "backend" / "listings" / "safe.py"
            active_file.parent.mkdir(parents=True)
            active_file.write_text("def ok():\n    return 'clean'\n", encoding="utf-8")

            reference_file = (
                root
                / "backend"
                / "reference_html"
                / "sahibinden"
                / "emlak_konut_daire_files"
                / "gtm.js.download"
            )
            reference_file.parent.mkdir(parents=True)
            reference_file.write_text(
                "<<<<<<< noisy copied reference blob\n=======\n>>>>>>> reference\n",
                encoding="utf-8",
            )

            report = audit.build_report(root=root)

            self.assertEqual(len(report.active_conflict_marker_hits), 0)
            self.assertIn(reference_file, report.reference_snapshot_files)
            self.assertIn(active_file, report.active_source_files)

    def test_v139_build_report_flags_real_active_source_conflict_markers(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            active_file = root / "backend" / "listings" / "views.py"
            active_file.parent.mkdir(parents=True)
            active_file.write_text(
                "def broken():\n<<<<<<< HEAD\n    return 1\n=======\n    return 2\n>>>>>>> branch\n",
                encoding="utf-8",
            )

            report = audit.build_report(root=root)

            self.assertEqual(len(report.active_conflict_marker_hits), 3)
            self.assertIn(active_file, [hit[0] for hit in report.active_conflict_marker_hits])

    def test_v139_unicode_safe_output_handles_turkish_paths_for_windows_console(self):
        text = audit.safe_output_text("Şişli reference path", encoding="cp1252")

        self.assertEqual(text, "\\u015ei\\u015fli reference path")
        self.assertIn("\\u015e", text)
        self.assertIn("\\u015f", text)
        self.assertIn("reference path", text)

    def test_v139_equal_sign_headings_are_not_treated_as_merge_conflicts(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            active_file = root / "README.md"
            active_file.write_text(
                "===== NORMAL AUDIT SECTION =====\nNo merge conflict here.\n",
                encoding="utf-8",
            )

            report = audit.build_report(root=root)

            self.assertEqual(len(report.active_conflict_marker_hits), 0)
