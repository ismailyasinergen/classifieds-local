"""
DEFAULT_LISTING_EXPIRY_HELPER_EXTRACTION_V145

Listing lifecycle helper functions.

This module starts by housing default_listing_expiry, which was previously
defined in backend/listings/views.py.

Import hygiene note:
Only imports required by lifecycle helpers should live here. UI and request
handling concerns stay in views.py.
"""

from __future__ import annotations

from datetime import timedelta
from django.utils import timezone


def default_listing_expiry():
    return timezone.now() + timedelta(days=30)
