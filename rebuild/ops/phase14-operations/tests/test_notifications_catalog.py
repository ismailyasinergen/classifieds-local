import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from snapshot_catalog import require_phase10_catalog
from test_new_tables import full_catalog


class NotificationCatalogTests(unittest.TestCase):
    def test_each_notification_table_required(self):
        for name in list(full_catalog()['tables']):
            catalog = full_catalog()
            del catalog['tables'][name]
            with self.assertRaises(ValueError):
                require_phase10_catalog(catalog)

    def test_each_notification_column_required(self):
        for name, entry in full_catalog()['tables'].items():
            if name == 'listings_favorite':
                continue
            for column in entry['columns']:
                catalog = full_catalog()
                catalog['tables'][name]['columns'].remove(column)
                with self.assertRaises(ValueError):
                    require_phase10_catalog(catalog)

    def test_missing_relations_constraints_and_counter_refused(self):
        for name in ['events_eventconsumption', 'notifications_notificationdelivery', 'notifications_notificationmatch']:
            catalog = full_catalog()
            catalog['tables'][name]['constraints'] = []
            with self.assertRaises(ValueError):
                require_phase10_catalog(catalog)
        catalog = full_catalog()
        del catalog['publicationBoundary']
        with self.assertRaisesRegex(ValueError, 'publication_boundary_missing'):
            require_phase10_catalog(catalog)

    def test_counter_change_is_not_sequence_equivalence(self):
        from verify_original import compare_catalog
        expected, actual = full_catalog(), full_catalog()
        actual['publicationBoundary']['value'] = 0
        with self.assertRaisesRegex(ValueError, 'snapshot_catalog_mismatch'):
            compare_catalog(actual, expected)

    def test_deployment_wrong_or_missing_binding_refused(self):
        from deployment import validate_deployment
        for record in [None, {}, {'format': 1}, {'overlayBase64': 'PRIVATE_CANARY'}]:
            with self.assertRaises(ValueError) as result:
                validate_deployment(record)
            self.assertNotIn('PRIVATE_CANARY', str(result.exception))

    def test_old_table_only_catalog_is_rejected(self):
        catalog = {
            'tables': {'listings_favorite': {}, 'notifications_savedsearch': {}},
            'migrations': [['listings', '0006_favorite'], ['notifications', '0001_initial']],
            'sequences': [{'table': t, 'column': 'id'} for t in ['listings_favorite', 'notifications_savedsearch']],
        }
        with self.assertRaises(ValueError):
            require_phase10_catalog(catalog)


if __name__ == '__main__':
    unittest.main()
