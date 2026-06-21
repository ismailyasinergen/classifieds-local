# SAVED_SEARCH_NOTIFICATION_RUNBOOK_COMMAND_ALIGNMENT_V88_TESTS
from django.test import SimpleTestCase

from listings.management.commands.check_saved_search_notifications import Command


class SavedSearchNotificationRunbookCommandAlignmentTests(SimpleTestCase):
    def test_command_examples_include_runbook_aligned_single_search_retry(self):
        text = Command.examples

        self.assertIn("Dry-run one saved search", text)
        self.assertIn("--saved-search-id 123", text)
        self.assertIn("--site-base-url https://classifieds.local", text)

    def test_command_examples_include_runbook_aligned_send_after_dry_run(self):
        text = Command.examples

        self.assertIn("Send one saved search after dry-run verification", text)
        self.assertIn("--saved-search-id 123 --send", text)

    def test_command_examples_include_runbook_aligned_stale_batch(self):
        text = Command.examples

        self.assertIn("Process only stale searches in a bounded batch", text)
        self.assertIn("--stale-before-hours 24 --max-searches 100", text)

    def test_command_safety_notes_match_runbook_language(self):
        text = Command.examples

        self.assertIn("Dry-run is the default", text)
        self.assertIn("Use --send only after reviewing output", text)
        self.assertIn("failed sends do not update timestamps", text)
