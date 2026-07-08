"""
LISTING_MODERATION_HELPER_EXTRACTION_V143

Extracted listing moderation helper functions.

This module starts by housing _create_moderation_notice, which was previously
defined in backend/listings/views.py.

Import hygiene note:
Only imports required by _create_moderation_notice should live here. View-only
classes, mixins, decorators, forms, pagination, and template helpers belong in
views.py.
"""

from __future__ import annotations

def _create_moderation_notice(recipient, title, body, notice_type="report_update", listing=None, listing_report=None):
    from accounts.models import ModerationNotice

    if not recipient:
        return None

    return ModerationNotice.objects.create(
        recipient=recipient,
        title=title,
        body=body,
        notice_type=notice_type,
        listing=listing,
        listing_report=listing_report,
    )
