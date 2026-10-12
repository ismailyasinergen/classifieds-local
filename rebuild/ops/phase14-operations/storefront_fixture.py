"""Nonempty Storefront scenarios; only the new synthetic source may write."""
import json
import os
import re
import sys


def main():
    if (os.environ.get('RECOVERY_ROLE') != 'synthetic-source'
            or not re.fullmatch('[a-f0-9]{16}', sys.argv[1])
            or sys.argv[1] != os.environ.get('RECOVERY_RUN')):
        raise ValueError('synthetic_source_required')
    import django
    django.setup()
    from accounts.models import User, Storefront
    from accounts.storefronts import create_storefront, change_storefront
    from catalog.models import Category
    from listings.services import create_listing_draft
    from listings.publication import submit_revision
    from listings.models import Listing
    from moderation.services import approve_revision
    from moderation.models import Restriction
    from django.db import connection
    if (connection.settings_dict['NAME'] != 'recovery' or connection.settings_dict['HOST'] != 'db'
            or Storefront.objects.exists()):
        raise ValueError('fixture_database_refused')
    users = [User.objects.get(email=e) for e in ['phase11-1@example.test', 'phase11-2@example.test',
        'p13-23@example.test', 'p13-24@example.test']]
    moderator = User.objects.get(email='other@example.test')
    for index, actor in enumerate(users):
        row = create_storefront(actor=actor, name=f'Kurtarma vitrini {index}', intro='Public tanıtım')
        if index != 1:
            row = change_storefront(actor=actor, storefront_id=row.pk, expected_version=row.edit_version, action='publish')
        if index == 0:
            change_storefront(actor=actor, storefront_id=row.pk, expected_version=row.edit_version,
                action='save', name='P15_PRIVATE_DRAFT_CANARY', intro='P15_PRIVATE_INTRO_CANARY')
            User.objects.filter(pk=actor.pk).update(first_name='P15_PRIVATE_ACCOUNT_CANARY')
        elif index == 2:
            change_storefront(actor=actor, storefront_id=row.pk, expected_version=row.edit_version, action='unpublish')
        elif index == 3:
            Restriction.objects.create(seller=actor, actor=moderator, reason='Synthetic seller restriction')
    for index, actor in enumerate(users[:2]):
        revision = create_listing_draft(actor=actor, category_id=Category.objects.get().pk,
            content={'title': f'Vitrin örnek {index}', 'description': 'Synthetic public item', 'price': '12.50',
                'currency': 'EUR', 'location': 'İstanbul',
                'attributes': {'model_year': 2020, 'area': '82.5', 'electric': False}})
        submit_revision(actor=actor, revision_id=revision.pk)
        approve_revision(actor=moderator, revision_id=revision.pk, expected_public_revision_id=None, reason='Synthetic storefront recovery')
    hidden = create_listing_draft(actor=users[0], category_id=Category.objects.get().pk,
        content={'title': 'P15_PRIVATE_LISTING_CANARY', 'description': 'Synthetic private draft', 'price': '12.50',
            'currency': 'EUR', 'location': 'İstanbul',
            'attributes': {'model_year': 2020, 'area': '82.5', 'electric': False}})
    # No lifecycle service exists in this release; this isolated fixture also covers a closed listing.
    Listing.objects.filter(pk=hidden.listing_id).update(lifecycle='closed')
    print(json.dumps({'pass': True, 'storefronts': Storefront.objects.count(), 'syntheticOnly': True}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'pass': False, 'category': 'storefront_fixture_failed'}))
        sys.exit(1)
