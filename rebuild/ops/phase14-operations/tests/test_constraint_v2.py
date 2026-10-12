import copy
import json
import unittest
from pathlib import Path
from test_new_tables import full_catalog
from verify_original import compare_catalog


class ConstraintV2Tests(unittest.TestCase):
    def pair(self):
        pairs = json.loads((Path(__file__).parents[1] / 'constraint-variants-v2.json').read_text())
        a = full_catalog()
        a.update(format=3, constraintProfile='pg17.11-public-enum-v2', serverVersion=170011)
        for key, definitions in pairs.items():
            table, name = key.split('/')
            a['tables'][table] = dict(count=0, sha256='same', schema='same', columns=['state'], constraints=[dict(name=name, type='c', definition=definitions[0], validated=True)])
        b = copy.deepcopy(a)
        for key, definitions in pairs.items():
            table, name = key.split('/')
            b['tables'][table]['constraints'][0]['definition'] = definitions[1]
        return a, b

    def test_exact_six_demonstrated_pairs(self):
        a, b = self.pair()
        self.assertTrue(compare_catalog(a, b))

    def test_real_differences_refused(self):
        for kind in ['deleted', 'operator', 'literal', 'and_or', 'null', 'validated', 'schema', 'foreign_key', 'unique']:
            a, b = self.pair()
            row = b['tables']['media_mediaasset']
            if kind == 'deleted': row['constraints'] = []
            elif kind == 'schema': row['schema'] = 'different'
            elif kind == 'validated': row['constraints'][0]['validated'] = False
            elif kind in ['foreign_key', 'unique']:
                b['tables']['notifications_notificationdelivery']['constraints'].append(dict(name=kind, type=kind[0], definition='different', validated=True))
            else:
                row['constraints'][0]['definition'] += {'operator': ' <>', 'literal': " 'different'", 'and_or': ' OR TRUE', 'null': ' IS NULL'}[kind]
            with self.subTest(kind=kind), self.assertRaises(ValueError): compare_catalog(a, b)

    def test_old_missing_or_wrong_profile_refused(self):
        for field, value in [('format', 1), ('constraintProfile', None), ('serverVersion', 170010)]:
            a, b = self.pair()
            a[field] = value
            with self.assertRaises(ValueError): compare_catalog(a, b)
