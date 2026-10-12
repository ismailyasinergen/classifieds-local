import copy
import io
import tarfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from test_new_tables import full_catalog
from snapshot_catalog import require_phase10_catalog
from verify_original import compare_catalog
from archive_io import stream_safe_source
from restore_runtime import check_archive


class StorefrontContractTests(unittest.TestCase):
    def test_real_target_rejects_catalog_and_behavior_write_entry(self):
        from verify_storefronts import require_synthetic
        for mode in ['catalog', 'behavior']:
            with self.assertRaisesRegex(ValueError, 'synthetic_target_required'):
                require_synthetic('original-target', 'a'*16, 'a'*16, mode)
        require_synthetic('synthetic-target', 'a'*16, 'a'*16, 'behavior')

    def test_storefront_contract_and_all_missing_columns_constraints(self):
        self.assertTrue(require_phase10_catalog(full_catalog()))
        for key in ['columns', 'columnMetadata', 'constraints']:
            for index in range(len(full_catalog()['tables']['accounts_storefront'][key])):
                catalog = full_catalog()
                catalog['tables']['accounts_storefront'][key].pop(index)
                with self.assertRaisesRegex(ValueError, 'storefront_schema_missing'):
                    require_phase10_catalog(catalog)

    def test_altered_types_null_defaults_relationship_or_check_refused(self):
        for field, value in [(1, 'text'), (2, 'YES'), (3, '0'), (5, 'int8')]:
            catalog = full_catalog()
            catalog['tables']['accounts_storefront']['columnMetadata'][0][field] = value
            with self.assertRaises(ValueError):
                require_phase10_catalog(catalog)
        for index in range(7):
            for field, value in [('validated', False), ('definition', 'different'), ('deferrable', None)]:
                catalog = full_catalog()
                catalog['tables']['accounts_storefront']['constraints'][index][field] = value
                with self.assertRaises(ValueError):
                    require_phase10_catalog(catalog)

    def test_uuid_or_edit_version_is_not_a_sequence(self):
        for column in ['id', 'edit_version']:
            catalog = full_catalog()
            catalog['sequences'].append(dict(table='accounts_storefront', column=column))
            with self.assertRaisesRegex(ValueError, 'storefront_sequence_refused'):
                require_phase10_catalog(catalog)

    def test_version_and_digest_differences_refused(self):
        catalog = full_catalog()
        catalog['storefrontState']['minEditVersion'] = 0
        with self.assertRaisesRegex(ValueError, 'storefront_version_refused'):
            require_phase10_catalog(catalog)
        actual, expected = full_catalog(), full_catalog()
        actual['tables']['accounts_storefront']['sha256'] = 'changed_private_row'
        with self.assertRaisesRegex(ValueError, 'snapshot_catalog_mismatch'):
            compare_catalog(actual, expected)

    def test_empty_scope_and_old_catalog_version(self):
        from storefront_coverage import receipt
        catalog = full_catalog()
        catalog['tables']['accounts_storefront']['count'] = 0
        catalog['storefrontState'] = dict.fromkeys(catalog['storefrontState'], 0)
        catalog['storefrontState'].update(minEditVersion=None, maxEditVersion=None)
        self.assertEqual(receipt(catalog)['coverage'], 'empty')
        self.assertFalse(receipt(catalog)['behaviorTestPerformed'])
        catalog['format'] = 2
        with self.assertRaisesRegex(ValueError, 'catalog_version_refused'):
            require_phase10_catalog(catalog)

    def test_old_catalog_without_storefront_refused(self):
        catalog = full_catalog()
        catalog['tables'].pop('accounts_storefront', None)
        with self.assertRaisesRegex(ValueError, 'storefront_schema_missing'):
            require_phase10_catalog(catalog)

    def test_private_source_rejected_before_stat_or_read(self):
        for name in ['rebuild/private/.env.example', 'rebuild/.ENV.local', 'rebuild/.env']:
            with patch('pathlib.Path.stat', side_effect=AssertionError('content_boundary_crossed')) as probe:
                with self.assertRaisesRegex(ValueError, 'source_path_refused'):
                    stream_safe_source([dict(path=name, sha256='0'*64)], '/unused', io.BytesIO())
                probe.assert_not_called()

    def test_private_archive_rejected_before_member_read(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w') as archive:
            member = tarfile.TarInfo('rebuild/private/.env.example')
            member.size = 3
            archive.addfile(member, io.BytesIO(b'xyz'))
        data.seek(0)
        with patch('tarfile.TarFile.extractfile', side_effect=AssertionError('private_read')) as read:
            with self.assertRaisesRegex(ValueError, 'source_member_refused'):
                check_archive(data, 'source')
            read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
