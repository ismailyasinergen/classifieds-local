"""Functional checks write only the isolated synthetic target, never real restored accounts."""
import json
import os
import sys


def main():
    assert os.environ.get('RECOVERY_ROLE') == 'synthetic-target' and os.environ.get('RECOVERY_RUN') == sys.argv[1]
    import django
    django.setup()
    from accounts.models import User
    from listings.models import Favorite
    from notifications.models import SavedSearch
    from notifications.services import save_search
    from listings.search.parsing import search_spec_from_dict, search_spec_to_dict, search_querystring, parse_search_spec
    from django.test import Client
    from django.http import QueryDict
    from django.db import transaction
    from urllib.parse import urlsplit
    from unittest.mock import patch
    checks = 0
    def check(ok):
        nonlocal checks
        if not ok:
            raise ValueError('feature_restore_assertion_failed')
        checks += 1
    check(Favorite.objects.count() == 4 and SavedSearch.objects.filter(user__email__startswith='phase11-').count() == 2)
    for index in (1, 2):
        actor = User.objects.get(email=f'phase11-{index}@example.test')
        row = SavedSearch.objects.get(user=actor)
        spec = search_spec_from_dict(row.spec)
        check(row.name == f'İstanbul aramam {index}')
        check(row.spec['keyword'] == 'İstanbul araç' and row.spec['currency'] == 'EUR' and row.spec['price_min'] == '10.50' and row.spec['price_max'] == '1234.56')
        check(spec.attribute_schema.version == 1 and all(ref.version == 1 for ref in spec.resolved_schemas))
        check(search_spec_to_dict(spec) == row.spec)
        client = Client()
        client.force_login(actor)
        response = client.get('/favorilerim/')
        check(response.status_code == 200 and 'no-store' in response['Cache-Control'])
        check(len(response.context_data['page_obj']) == 2) if hasattr(response, 'context_data') else check(Favorite.objects.filter(user=actor).count() == 2)
        check('İlan şu anda kullanılamıyor'.encode() in response.content)
        from listings.queries import public_listings
        for favorite in Favorite.objects.filter(user=actor).select_related('listing__public_revision'):
            if not public_listings().filter(pk=favorite.listing_id).exists():
                check(client.get(f'/ilanlar/{favorite.listing_id}/').status_code == 404)
                check(favorite.listing.public_revision.title.encode() not in response.content)
        response = client.get(f'/kayitli-aramalarim/{row.pk}/ac/')
        check(response.status_code == 302 and urlsplit(response.url).path == '/')
        query = QueryDict(urlsplit(response.url).query)
        check('page' not in query and search_spec_to_dict(parse_search_spec(query)) == row.spec)
        other = SavedSearch.objects.filter(user__email__startswith='phase11-').exclude(user=actor).get()
        check(client.get(f'/kayitli-aramalarim/{other.pk}/ac/').status_code == 404)
        before = SavedSearch.objects.count()
        duplicate, created = save_search(actor=actor, name='Başka ad', payload=row.spec)
        check(not created and duplicate.pk == row.pk and duplicate.name == row.name and SavedSearch.objects.count() == before)
        with transaction.atomic():
            SavedSearch.objects.filter(pk=row.pk).update(spec={'version': 999})
            with patch('listings.views.matching_public_listings', side_effect=AssertionError('result_query_forbidden')):
                check(client.get(f'/kayitli-aramalarim/{row.pk}/ac/').status_code == 400)
            transaction.set_rollback(True)
    print(json.dumps({'pass': True, 'checks': checks, 'favorites': 4, 'savedSearches': 2, 'syntheticOnly': True}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'pass': False, 'category': 'feature_restore_verification_failed'}))
        sys.exit(1)
