from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


V317_LISTING_SHARE_PRINT_ACTIONS = (
    "LISTING_SHARE_PRINT_ACTIONS_V317"
)


class ListingSharePrintActionsV317Tests(
    SimpleTestCase
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.base_dir = Path(settings.BASE_DIR)

        cls.template_path = (
            cls.base_dir
            / "listings"
            / "templates"
            / "listings"
            / "listing_detail.html"
        )

        cls.template_source = (
            cls.template_path.read_text(
                encoding="utf-8"
            )
        )

    def test_v317_marker_and_controls_are_packaged(
        self,
    ):
        self.assertIn(
            V317_LISTING_SHARE_PRINT_ACTIONS,
            self.template_source,
        )

        self.assertIn(
            "data-listing-share-v317",
            self.template_source,
        )

        self.assertIn(
            "data-listing-print-v317",
            self.template_source,
        )

        self.assertIn(
            "Share listing",
            self.template_source,
        )

        self.assertIn(
            "Print / Save PDF",
            self.template_source,
        )

    def test_v317_share_prefers_native_browser_api(
        self,
    ):
        self.assertIn(
            "navigator.share",
            self.template_source,
        )

        self.assertIn(
            "title: document.title",
            self.template_source,
        )

        self.assertIn(
            "url: window.location.href",
            self.template_source,
        )

    def test_v317_copy_fallback_is_resilient(
        self,
    ):
        required_fragments = (
            "navigator.clipboard",
            "navigator.clipboard.writeText",
            'document.createElement("textarea")',
            'document.execCommand("copy")',
            "Listing link copied.",
            "Listing link could not be copied.",
        )

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.template_source,
                )

    def test_v317_print_action_uses_browser_dialog(
        self,
    ):
        self.assertIn(
            "window.print();",
            self.template_source,
        )

        self.assertIn(
            "Opening print and PDF options.",
            self.template_source,
        )

    def test_v317_controls_are_accessible_and_non_submitting(
        self,
    ):
        required_fragments = (
            'type="button"',
            'role="status"',
            'aria-live="polite"',
            'aria-atomic="true"',
            'aria-describedby="listing-action-status-v317"',
        )

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.template_source,
                )

    def test_v317_adds_no_database_migration(
        self,
    ):
        migration_matches = []

        for app_name in (
            "accounts",
            "listings",
        ):
            migration_root = (
                self.base_dir
                / app_name
                / "migrations"
            )

            migration_matches.extend(
                migration_root.glob("*v317*.py")
            )

        self.assertEqual(
            migration_matches,
            [],
        )
