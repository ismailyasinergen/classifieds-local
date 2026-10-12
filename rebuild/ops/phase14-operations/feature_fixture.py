"""Only a newly guarded synthetic source may create these nonempty domain records."""
import json
import os
import re
import sys


def main():
    if os.environ.get('RECOVERY_ROLE') != 'synthetic-source' or not re.fullmatch('[a-f0-9]{16}', sys.argv[1]) or sys.argv[1] != os.environ.get('RECOVERY_RUN'):
        raise ValueError('fixture_identity_refused')
    import django
    django.setup()
    from django.db import connection
    if connection.settings_dict['NAME'] != 'recovery' or connection.settings_dict['HOST'] != 'db':
        raise ValueError('fixture_database_refused')
    from accounts.models import User
    from catalog.models import Category, AttributeSchema
    from listings.models import Listing, Favorite
    from listings.favorites import add_favorite
    from listings.queries import public_listings
    from notifications.models import SavedSearch
    from notifications.services import save_search
    from listings.search.parsing import parse_search_spec, search_spec_to_dict
    from django.http import QueryDict
    if SavedSearch.objects.exists():
        raise ValueError('fixture_not_empty')
    category = Category.objects.get()
    schema = AttributeSchema.objects.get(category=category, version=1)
    query = QueryDict('', mutable=True)
    query.update({'q': 'İstanbul araç', 'currency': 'EUR', 'price_min': '10.50', 'price_max': '1234.56',
                  'category': str(category.pk), 'schema': str(schema.pk), 'schema_version': '1',
                  'a.area.min': '82.50', 'page': '9'})
    payload = search_spec_to_dict(parse_search_spec(query))
    for index in (1, 2):
        actor = User.objects.get(email=f'phase11-{index}@example.test')
        add_favorite(actor=actor, listing_id=public_listings().get().pk)
        row, created = save_search(actor=actor, name=f'İstanbul aramam {index}', payload=payload)
        if not created or row.spec['price_min'] != '10.50' or not row.spec['resolved_schemas']:
            raise ValueError('fixture_spec_refused')
    # A later compatible schema must not widen the frozen saved specification.
    AttributeSchema.objects.create(category=category, version=2, definition=schema.definition)
    if Favorite.objects.count() != 4 or SavedSearch.objects.count() != 2:
        raise ValueError('fixture_nonempty_failed')
    print(json.dumps({'pass': True, 'favorites': 4, 'savedSearches': 2, 'frozenSchema': True}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'pass': False, 'category': 'feature_fixture_failed'}))
        sys.exit(1)
