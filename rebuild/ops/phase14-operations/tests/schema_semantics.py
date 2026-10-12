def main():
    """Supporting INSERT probes in synthetic temporary tables; not a general SQL equivalence proof."""
    import json
    import os
    from pathlib import Path

    if os.environ.get('RECOVERY_ROLE') != 'synthetic-source':
        raise ValueError('synthetic_source_required')
    import django
    django.setup()
    from django.db import connection
    from psycopg import sql, errors

    pairs = json.loads((Path(__file__).parents[1] / 'constraint-variants-v2.json').read_bytes())
    fields = {'events_outboxevent': ('event_type', 'listing.revision_published'), 'listings_listing': ('lifecycle', 'live'),
              'listings_listingrevision': ('status', 'approved'), 'media_mediaasset': ('state', 'ready'),
              'moderation_appealdecision': ('outcome', 'uphold'), 'moderation_moderationdecision': ('outcome', 'approved')}
    connection.ensure_connection()
    conn = connection.connection
    result = {'checks': 0, 'columns': [], 'pass': False}
    with conn.transaction():
        cast = conn.execute("SELECT castmethod,castcontext FROM pg_cast WHERE castsource='varchar'::regtype AND casttarget='text'::regtype").fetchone()
        if cast != ('b', 'i'):
            raise ValueError('cast_semantics_refused')
        result['varcharToText'] = {'method': 'binary_coercible', 'context': 'implicit'}
        for key, definitions in pairs.items():
            table = key.split('/')[0]
            field, valid = fields[table]
            column = conn.execute("SELECT data_type,character_maximum_length,is_nullable,collation_schema,collation_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=%s", (table, field)).fetchone()
            result['columns'].append({'table': table, 'field': field, 'metadata': list(column)})
            outcomes = []
            for definition in definitions:
                conn.execute(sql.SQL('CREATE TEMP TABLE p13_constraint_probe ({} varchar({}) {} {}) ON COMMIT DROP').format(sql.Identifier(field), sql.Literal(column[1]), sql.SQL('NOT NULL' if column[2] == 'NO' else ''), sql.SQL(definition)))
                accepted = []
                for value in [valid, 'invalid', '', None]:
                    try:
                        with conn.transaction():
                            conn.execute(sql.SQL('INSERT INTO p13_constraint_probe VALUES (%s)'), (value,))
                        accepted.append(True)
                    except (errors.CheckViolation, errors.NotNullViolation, errors.StringDataRightTruncation):
                        accepted.append(False)
                outcomes.append(accepted)
                conn.execute('DROP TABLE p13_constraint_probe')
            if outcomes[0] != outcomes[1] or outcomes[0] != [True, False, False, column[2] == 'YES']:
                raise ValueError('constraint_insert_probe_failed')
            result['checks'] += 4
    result['pass'] = True
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        import json, sys
        print(json.dumps({"pass": False, "category": str(error) if type(error) is ValueError and str(error) in ("synthetic_source_required", "cast_semantics_refused", "constraint_insert_probe_failed") else "schema_probe_failed", "errorType": type(error).__name__, "sqlstate": getattr(error, "sqlstate", None)}))
        sys.exit(1)
