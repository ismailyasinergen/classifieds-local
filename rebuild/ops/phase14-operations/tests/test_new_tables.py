import unittest
from verify_original import compare_catalog


def full_catalog():
    columns = {
        'listings_favorite': ['id'],
        'events_publicationboundary': ['id', 'value'],
        'events_eventconsumption': ['id', 'event_id', 'consumer', 'status', 'recipient_cursor', 'attempts', 'next_attempt_at', 'reason', 'updated_at'],
        'notifications_savedsearch': ['id', 'user_id', 'name', 'spec', 'notifications_enabled', 'notification_boundary', 'notifications_enabled_at', 'notification_error'],
        'notifications_notificationdelivery': ['id', 'event_id', 'recipient_id', 'channel', 'listing_id', 'read_at', 'archived_at', 'created_at'],
        'notifications_notificationmatch': ['id', 'delivery_id', 'search_id', 'boundary'],
    }
    catalog = {'tables': {t: {'count': 2, 'columns': cols, 'constraints': [{'name': t + '_pkey', 'type': 'p', 'definition': 'PRIMARY KEY (id)', 'validated': True}]} for t, cols in columns.items()},
               'migrations': [['listings', '0006_favorite'], ['notifications', '0001_initial'], ['events', '0002_publicationboundary_eventconsumption'], ['notifications', '0002_in_app_notifications']],
               'sequences': [{'table': t, 'column': 'id'} for t in columns], 'publicationBoundary': {'rows': 1, 'value': 17}}
    for table, names in {'events_eventconsumption': ['events_consumer_event_unique'], 'notifications_notificationdelivery': ['notification_event_recipient_channel', 'notification_in_app_only'], 'notifications_notificationmatch': ['notification_match_unique']}.items():
        catalog['tables'][table]['constraints'].extend({'name': n, 'type': 'u', 'definition': 'synthetic constraint', 'validated': True} for n in names)
    for table, targets in {'events_eventconsumption': ['events_outboxevent'], 'notifications_savedsearch': ['accounts_user'], 'notifications_notificationdelivery': ['events_outboxevent', 'accounts_user', 'listings_listing'], 'notifications_notificationmatch': ['notifications_notificationdelivery', 'notifications_savedsearch']}.items():
        catalog['tables'][table]['constraints'].extend({'name': t + '_fk', 'type': 'f', 'definition': 'FOREIGN KEY (id) REFERENCES ' + t + '(id)', 'validated': True} for t in targets)
    catalog.update(format=3, constraintProfile='pg17.11-public-enum-v2', serverVersion=170011)
    catalog['publicationBoundary'].update(minId=1,maxId=1,idSequence=dict(last=1,called=False))
    catalog['notificationState'] = dict(consumption=dict.fromkeys(('pending','retry','completed','skipped','failed'),0),enabledSearches=0,disabledSearches=2,readDeliveries=0,archivedDeliveries=0,nullSearchMatches=0)
    from storefront_coverage import FIELDS, CONSTRAINTS
    import copy
    catalog['tables']['accounts_storefront'] = dict(count=2, columns=[c[0] for c in FIELDS],
        columnMetadata=[list(c) for c in FIELDS], constraints=copy.deepcopy(CONSTRAINTS))
    catalog['migrations'].append(['accounts', '0004_storefront'])
    catalog['storefrontState'] = dict(count=2, published=1, unpublished=1, neverPublished=1, withdrawn=0,
        draftDiffersFromPublic=1, minEditVersion=1, maxEditVersion=3)
    return catalog


class Phase10CatalogTests(unittest.TestCase):
    def test_complete_phase10_catalog_accepted_and_changes_rejected(self):
        import copy
        catalog = full_catalog()
        self.assertTrue(compare_catalog(catalog, catalog))
        changed = copy.deepcopy(catalog)
        changed['tables']['listings_favorite']['count'] = 0
        with self.assertRaisesRegex(ValueError, 'snapshot_catalog_mismatch'):
            compare_catalog(changed, catalog)

    def test_both_catalogs_omitting_new_tables_are_rejected(self):
        catalog = {'tables': {}, 'migrations': [], 'sequences': []}
        with self.assertRaisesRegex(ValueError, 'phase10_schema_missing'):
            compare_catalog(catalog, catalog)

    def test_one_new_table_missing_is_rejected(self):
        for missing in ('listings_favorite', 'notifications_savedsearch'):
            catalog = {'tables': {name: {'count': 2} for name in ('listings_favorite', 'notifications_savedsearch') if name != missing},
                       'migrations': [['listings', '0006_favorite'], ['notifications', '0001_initial']], 'sequences': []}
            with self.assertRaisesRegex(ValueError, 'phase10_schema_missing'):
                compare_catalog(catalog, catalog)


if __name__ == '__main__':
    unittest.main()
