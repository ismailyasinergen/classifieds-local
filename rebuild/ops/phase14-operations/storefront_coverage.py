"""Pinned Storefront schema and aggregate-only snapshot coverage."""
import json

CONSTRAINTS = json.loads("[{\"name\":\"accounts_storefront_edit_version_check\",\"type\":\"c\",\"definition\":\"CHECK ((edit_version >= 0))\",\"validated\":true,\"deferrable\":false,\"deferred\":false,\"islocal\":true,\"inhcount\":0,\"noinherit\":false},{\"name\":\"accounts_storefront_owner_id_f6ab798f_fk_accounts_user_id\",\"type\":\"f\",\"definition\":\"FOREIGN KEY (owner_id) REFERENCES accounts_user(id) DEFERRABLE INITIALLY DEFERRED\",\"validated\":true,\"deferrable\":true,\"deferred\":true,\"islocal\":true,\"inhcount\":0,\"noinherit\":true},{\"name\":\"accounts_storefront_owner_id_key\",\"type\":\"u\",\"definition\":\"UNIQUE (owner_id)\",\"validated\":true,\"deferrable\":false,\"deferred\":false,\"islocal\":true,\"inhcount\":0,\"noinherit\":true},{\"name\":\"accounts_storefront_pkey\",\"type\":\"p\",\"definition\":\"PRIMARY KEY (id)\",\"validated\":true,\"deferrable\":false,\"deferred\":false,\"islocal\":true,\"inhcount\":0,\"noinherit\":true},{\"name\":\"storefront_draft_name_present\",\"type\":\"c\",\"definition\":\"CHECK (((draft_name)::text ~ '\\\\S'::text))\",\"validated\":true,\"deferrable\":false,\"deferred\":false,\"islocal\":true,\"inhcount\":0,\"noinherit\":false},{\"name\":\"storefront_public_snapshot_present\",\"type\":\"c\",\"definition\":\"CHECK (((NOT is_published) OR (((published_name)::text ~ '\\\\S'::text) AND (published_at IS NOT NULL))))\",\"validated\":true,\"deferrable\":false,\"deferred\":false,\"islocal\":true,\"inhcount\":0,\"noinherit\":false},{\"name\":\"storefront_version_positive\",\"type\":\"c\",\"definition\":\"CHECK ((edit_version >= 1))\",\"validated\":true,\"deferrable\":false,\"deferred\":false,\"islocal\":true,\"inhcount\":0,\"noinherit\":false}]")
FIELDS = [
    ('id', 'uuid', 'NO', None, 'pg_catalog', 'uuid', None, None, None),
    ('draft_name', 'character varying', 'NO', None, 'pg_catalog', 'varchar', 80, None, None),
    ('draft_intro', 'text', 'NO', None, 'pg_catalog', 'text', None, None, None),
    ('published_name', 'character varying', 'NO', None, 'pg_catalog', 'varchar', 80, None, None),
    ('published_intro', 'text', 'NO', None, 'pg_catalog', 'text', None, None, None),
    ('is_published', 'boolean', 'NO', None, 'pg_catalog', 'bool', None, None, None),
    ('edit_version', 'bigint', 'NO', None, 'pg_catalog', 'int8', None, None, None),
    ('published_at', 'timestamp with time zone', 'YES', None, 'pg_catalog', 'timestamptz', None, None, None),
    ('updated_at', 'timestamp with time zone', 'NO', None, 'pg_catalog', 'timestamptz', None, None, None),
    ('owner_id', 'bigint', 'NO', None, 'pg_catalog', 'int8', None, None, None),
]
COUNTS = ('count', 'published', 'unpublished', 'neverPublished', 'withdrawn', 'draftDiffersFromPublic')


def validate(catalog):
    row = catalog.get('tables', {}).get('accounts_storefront', {})
    if (['accounts', '0004_storefront'] not in catalog.get('migrations', [])
            or row.get('columns') != [c[0] for c in FIELDS]
            or row.get('columnMetadata') != [list(c) for c in FIELDS]
            or row.get('constraints') != CONSTRAINTS):
        raise ValueError('storefront_schema_missing')
    if any(s.get('table') == 'accounts_storefront' for s in catalog.get('sequences', [])):
        raise ValueError('storefront_sequence_refused')
    state = catalog.get('storefrontState', {})
    if (set(state) != set(COUNTS) | {'minEditVersion', 'maxEditVersion'}
            or any(type(state[k]) is not int or state[k] < 0 for k in COUNTS)
            or state['count'] != row.get('count')
            or state['published'] + state['unpublished'] != state['count']
            or state['neverPublished'] + state['withdrawn'] != state['unpublished']
            or state['draftDiffersFromPublic'] > state['count']):
        raise ValueError('storefront_state_refused')
    if state['count']:
        if (type(state['minEditVersion']) is not int or type(state['maxEditVersion']) is not int
                or not 1 <= state['minEditVersion'] <= state['maxEditVersion']):
            raise ValueError('storefront_version_refused')
    elif state['minEditVersion'] is not None or state['maxEditVersion'] is not None:
        raise ValueError('storefront_version_refused')
    return True


def aggregate(cursor):
    cursor.execute('SELECT count(*), count(*) FILTER (WHERE is_published), '
        'count(*) FILTER (WHERE NOT is_published), '
        'count(*) FILTER (WHERE NOT is_published AND published_at IS NULL), '
        'count(*) FILTER (WHERE NOT is_published AND published_at IS NOT NULL), '
        'count(*) FILTER (WHERE (draft_name,draft_intro) IS DISTINCT FROM (published_name,published_intro)), '
        'min(edit_version), max(edit_version) FROM accounts_storefront')
    return dict(zip((*COUNTS, 'minEditVersion', 'maxEditVersion'), cursor.fetchone()))


def receipt(catalog):
    validate(catalog)
    state = catalog['storefrontState']
    return {**state, 'coverage': 'aggregate_verified' if state['count'] else 'empty',
            'schemaVerified': True, 'snapshotValuesVerified': True, 'uuidNoSequenceVerified': True,
            'behaviorTestPerformed': False, 'realUserOperationPerformed': False}
