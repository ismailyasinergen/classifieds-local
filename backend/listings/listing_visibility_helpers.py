"""
ACTIVE_APPROVED_LISTINGS_HELPER_EXTRACTION_V146

Listing visibility query helper functions.

This module starts by housing active_approved_listings, which was previously
defined in backend/listings/views.py.

Import hygiene note:
Only imports required by visibility query helpers should live here. UI and
request handling concerns stay in views.py.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from .models import Listing


def active_approved_listings(queryset):
    return queryset.filter(
        status=Listing.Status.APPROVED,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )
