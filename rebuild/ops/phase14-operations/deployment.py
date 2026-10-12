"""Versioned, non-secret deployment record; never applies settings to a target."""
import base64
import hashlib

PRODUCT = 'f69c9d336c5baec787e2b0113d3ec77fd536c97e1ed0e3769ebb46bfda4bac58'
IMAGE = 'sha256:23e5fe716cd2f2e73c189f035eb3df345ca155c1cd31c78bfdbd0c06839a1839'
OVERLAY = '35afc2f08edc21d370d4000486c47b2e1607a9082d1a76cace940dd74aeb30d6'


def validate_deployment(record):
    if (not isinstance(record, dict) or set(record) != {'format', 'product', 'image', 'overlayPath', 'overlaySha256', 'overlayBase64'}
            or record['format'] != 1 or record['product'] != PRODUCT or record['image'] != IMAGE
            or record['overlayPath'] != 'rebuild/compose.original-notifications.yaml' or record['overlaySha256'] != OVERLAY
            or not isinstance(record['overlayBase64'], str) or len(record['overlayBase64']) > 4096):
        raise ValueError('deployment_refused')
    try:
        data = base64.b64decode(record['overlayBase64'], validate=True)
    except Exception:
        raise ValueError('deployment_refused') from None
    if hashlib.sha256(data).hexdigest() != OVERLAY:
        raise ValueError('deployment_refused')
    return data
