import unittest
from notification_coverage import receipt, TABLES
from test_new_tables import full_catalog


class CoverageTests(unittest.TestCase):
    def test_real_target_resume_refused_before_django_or_db(self):
        import os
        import sys
        from unittest.mock import patch
        from verify_notifications import main
        with patch.dict(os.environ, {'RECOVERY_ROLE': 'original-target', 'RECOVERY_RUN': 'a' * 16}), patch.object(sys, 'argv', ['verify', 'a' * 16, 'resume']):
            with self.assertRaisesRegex(ValueError, '^synthetic_target_required$'):
                main()

    def test_empty_and_nonempty_are_distinct(self):
        for count in (0, 2):
            catalog = full_catalog()
            for table in TABLES:
                catalog['tables'][table]['count'] = count
            result = receipt(catalog)
            self.assertTrue(all(t['coverage'] == ('empty' if count == 0 else 'aggregate_verified') for t in result['tables'].values()))
            self.assertFalse(result['realUserOperationPerformed'])
            self.assertFalse(result['restoredConsumerExecuted'])

    def test_missing_and_invalid_counts_refused(self):
        for value in (-1, 'PRIVATE_CANARY', None, True):
            catalog = full_catalog()
            catalog['tables'][TABLES[0]]['count'] = value
            with self.assertRaisesRegex(ValueError, '^notification_count_refused$'):
                receipt(catalog)
        catalog = full_catalog()
        del catalog['notificationState']
        with self.assertRaises(KeyError):
            receipt(catalog)
