"""Only new synthetic data: real preference/publication/delivery services plus bounded fault injection."""
import json
import os
import sys
from datetime import timedelta


def main():
    if os.environ.get('RECOVERY_ROLE') != 'synthetic-source' or os.environ.get('RECOVERY_RUN') != sys.argv[1]:
        raise ValueError('fixture_identity_refused')
    import django
    django.setup()
    from django.test import override_settings
    from django.utils import timezone
    from accounts.models import User
    from allauth.account.models import EmailAddress
    from catalog.models import Category
    from listings.services import create_listing_draft
    from listings.publication import submit_revision
    from moderation.services import approve_revision
    from notifications.services import save_search, set_notifications, mark_notification, delete_search
    from notifications.models import SavedSearch, NotificationDelivery, NotificationMatch
    from notifications.consumer import discover, consume_pending, _chunk, _retry, CONSUMER
    from listings.search.parsing import parse_search_spec, search_spec_to_dict
    from django.http import QueryDict
    from events.models import OutboxEvent, EventConsumption
    if NotificationDelivery.objects.exists():
        raise ValueError('fixture_not_empty')
    users = []
    searches = []
    for index in range(25):
        user = User.objects.create_user(email=f'p13-{index:02d}@example.test', password=None)
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        search, _ = save_search(actor=user, name='Synthetic notice', payload=search_spec_to_dict(parse_search_spec(QueryDict('q=Recovery+notice'))))
        set_notifications(actor=user, search_id=search.pk, enabled=True)
        users.append(user)
        searches.append(search)
    extra, _ = save_search(actor=users[0], name='Second matching search', payload=search_spec_to_dict(parse_search_spec(QueryDict('q=Recovery+notice&price_min=1&currency=EUR'))))
    set_notifications(actor=users[0], search_id=extra.pk, enabled=True)
    def publish(title):
        owner = User.objects.get(email='owner@example.test')
        revision = create_listing_draft(actor=owner, category_id=Category.objects.get().pk, content={
            'title': title, 'description': 'Synthetic recovery only', 'price': '10', 'currency': 'EUR',
            'location': 'Berlin', 'attributes': {'model_year': 2020, 'area': '82.5', 'electric': False}})
        submit_revision(actor=owner, revision_id=revision.pk)
        approve_revision(actor=User.objects.get(email='other@example.test'), revision_id=revision.pk, expected_public_revision_id=None, reason='Synthetic recovery')
        return OutboxEvent.objects.get(revision=revision, event_type=OutboxEvent.Type.REVISION_PUBLISHED)
    first = publish('Recovery notice complete')
    with override_settings(IN_APP_NOTIFICATIONS_ENABLED=True):
        for _ in range(4):
            consume_pending()
    if NotificationDelivery.objects.filter(event=first).count() != 25:
        raise ValueError('fixture_delivery_failed')
    mark_notification(actor=users[0], delivery_id=NotificationDelivery.objects.get(event=first, recipient=users[0]).pk)
    mark_notification(actor=users[1], delivery_id=NotificationDelivery.objects.get(event=first, recipient=users[1]).pk, archive=True)
    delete_search(actor=users[0], search_id=extra.pk)
    partial = publish('Recovery notice partial')
    discover()
    selected = []
    _chunk(selected)
    partial_job = EventConsumption.objects.get(event=partial, consumer=CONSUMER)
    if partial_job.status != 'pending' or partial_job.recipient_cursor != users[19].pk or NotificationDelivery.objects.filter(event=partial).count() != 20:
        raise ValueError('fixture_partial_failed')
    set_notifications(actor=users[24], search_id=searches[24].pk, enabled=False)
    delete_search(actor=users[23], search_id=searches[23].pk)
    set_notifications(actor=users[22], search_id=searches[22].pk, enabled=False)
    set_notifications(actor=users[22], search_id=searches[22].pk, enabled=True)
    SavedSearch.objects.filter(pk=searches[21].pk).update(spec={'version': 999})
    retry = publish('Recovery notice retry')
    failed = publish('Recovery notice failed')
    discover()
    retry_job = EventConsumption.objects.get(event=retry, consumer=CONSUMER)
    _retry([retry_job.pk, 0], 'database_transient')
    failed_job = EventConsumption.objects.get(event=failed, consumer=CONSUMER)
    for _ in range(5):
        _retry([failed_job.pk, 0], 'processing_error')
    if not NotificationMatch.objects.filter(search=None).exists():
        raise ValueError('fixture_null_contribution_failed')
    print(json.dumps({'pass': True, 'checks': 4, 'recipients': 25, 'deliveries': NotificationDelivery.objects.count(), 'partialRecipients': 20, 'faultInjectionSyntheticOnly': True}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'pass': False, 'category': 'notification_fixture_failed'}))
        sys.exit(1)
