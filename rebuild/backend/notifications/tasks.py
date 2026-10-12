from celery import shared_task
from django.conf import settings
import logging


@shared_task(ignore_result=True, soft_time_limit=45, time_limit=55)
def consume_in_app_notifications():
    if not getattr(settings, 'IN_APP_NOTIFICATIONS_ENABLED', False):
        return {'status': 'disabled', 'chunks': 0}
    from .consumer import consume_pending
    try:
        result = consume_pending()
    except Exception:
        raise RuntimeError('notification_consumer_unavailable') from None
    logging.getLogger(__name__).info('in_app_consumer_completed chunks=%s', result['chunks'])
    return result
