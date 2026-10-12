import unittest
from verify_original import compare_catalog, decrypt_factors


class OriginalTests(unittest.TestCase):
    def test_snapshot_catalog_equality(self):
        data = {'tables': {'t': {'count': 2, 'sha256': 'a', 'schema': 'b'}}, 'migrations': [], 'sequences': []}
        self.assertTrue(compare_catalog(data, data))

    def test_count_digest_schema_drift(self):
        for field in ('count', 'sha256', 'schema'):
            before = {'tables': {'t': {'count': 2, 'sha256': 'a', 'schema': 'b'}}, 'migrations': [], 'sequences': []}
            after = {**before, 'tables': {'t': {**before['tables']['t'], field: 'wrong'}}}
            with self.assertRaisesRegex(ValueError, '^snapshot_catalog_mismatch$'):
                compare_catalog(after, before)

    def test_zero_factors_is_unavailable(self):
        self.assertEqual(decrypt_factors([], lambda _: 'unused'), {'primary': 0, 'recovery': 0, 'coverage': 'unavailable'})

    def test_both_encrypted_factor_types_are_checked_without_token_consumption(self):
        seen = []
        def decrypt(value):
            seen.append(value)
            return 'private-canary'
        result = decrypt_factors([('totp', {'secret': 'cipher1'}), ('recovery_codes', {'seed': 'cipher2'})], decrypt)
        self.assertEqual(seen, ['cipher1', 'cipher2'])
        self.assertEqual(result, {'primary': 1, 'recovery': 1, 'coverage': 'verified'})

    def test_missing_ciphertext_is_refused(self):
        with self.assertRaisesRegex(ValueError, '^mfa_field_missing$'):
            decrypt_factors([('totp', {})], lambda _: 'value')
