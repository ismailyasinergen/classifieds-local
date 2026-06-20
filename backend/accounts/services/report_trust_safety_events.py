# REPORT_TRUST_SAFETY_EVENT_SERVICE_V1
def _record_event_safely(**kwargs):
    try:
        from accounts.services.trust_safety_events import record_trust_safety_event

        return record_trust_safety_event(**kwargs)
    except Exception:
        return None


def listing_report_metadata(report):
    return {
        "report_id": report.pk,
        "report_status": report.status,
        "report_action_taken": report.action_taken,
        "report_reason": report.reason,
        "reported_listing_id": report.listing_id,
        "reporter_id": report.reporter_id,
    }


def user_report_metadata(report):
    return {
        "report_id": report.pk,
        "report_status": report.status,
        "report_action_taken": report.action_taken,
        "reported_user_id": report.reported_user_id,
        "reporter_id": report.reporter_id,
        "source_listing_id": report.source_listing_id,
        "reasons": report.reasons or [],
    }


def record_listing_report_reviewed(report, *, actor, dismissed=False):
    from accounts.models import TrustSafetyEvent

    metadata = listing_report_metadata(report)
    if dismissed:
        metadata["dismissed"] = True

    title_action = "dismissed" if dismissed else "reviewed"

    return _record_event_safely(
        actor=actor,
        target_user=report.listing.owner,
        listing=report.listing,
        listing_report=report,
        event_type=TrustSafetyEvent.EventType.LISTING_REPORT_REVIEWED,
        title=f"Listing report #{report.pk} {title_action}",
        public_note=report.reporter_note or "",
        internal_note=report.admin_note or "",
        metadata=metadata,
    )


def record_listing_report_suspended(report, *, actor):
    from accounts.models import TrustSafetyEvent

    return _record_event_safely(
        actor=actor,
        target_user=report.listing.owner,
        listing=report.listing,
        listing_report=report,
        event_type=TrustSafetyEvent.EventType.LISTING_SUSPENDED,
        title=f"Listing #{report.listing_id} suspended from report #{report.pk}",
        public_note=report.reporter_note or "",
        internal_note=report.admin_note or "",
        metadata=listing_report_metadata(report),
    )


def record_listing_report_archived(report, *, actor):
    from accounts.models import TrustSafetyEvent

    return _record_event_safely(
        actor=actor,
        target_user=report.listing.owner,
        listing=report.listing,
        listing_report=report,
        event_type=TrustSafetyEvent.EventType.LISTING_ARCHIVED,
        title=f"Listing #{report.listing_id} archived from report #{report.pk}",
        public_note=report.reporter_note or "",
        internal_note=report.admin_note or "",
        metadata=listing_report_metadata(report),
    )


def record_user_report_action(report, *, actor, event_type, title):
    return _record_event_safely(
        actor=actor,
        target_user=report.reported_user,
        listing=report.source_listing,
        user_report=report,
        event_type=event_type,
        title=title,
        public_note=report.reporter_note or "",
        internal_note=report.admin_note or "",
        metadata=user_report_metadata(report),
    )


def record_user_report_reviewed(report, *, actor, dismissed=False):
    from accounts.models import TrustSafetyEvent

    title_action = "dismissed" if dismissed else "reviewed"
    return record_user_report_action(
        report,
        actor=actor,
        event_type=TrustSafetyEvent.EventType.SELLER_REPORT_REVIEWED,
        title=f"Seller report #{report.pk} {title_action}",
    )


def record_user_report_warning(report, *, actor):
    from accounts.models import TrustSafetyEvent

    return record_user_report_action(
        report,
        actor=actor,
        event_type=TrustSafetyEvent.EventType.SELLER_WARNED,
        title=f"Seller #{report.reported_user_id} warned from report #{report.pk}",
    )


def record_user_report_suspension(report, *, actor):
    from accounts.models import TrustSafetyEvent

    return record_user_report_action(
        report,
        actor=actor,
        event_type=TrustSafetyEvent.EventType.SELLER_SUSPENDED,
        title=f"Seller #{report.reported_user_id} suspended from report #{report.pk}",
    )


def record_user_report_verification_removed(report, *, actor):
    from accounts.models import TrustSafetyEvent

    return record_user_report_action(
        report,
        actor=actor,
        event_type=TrustSafetyEvent.EventType.SELLER_VERIFICATION_REMOVED,
        title=f"Seller #{report.reported_user_id} verification removed from report #{report.pk}",
    )


def record_user_report_listings_archived(report, *, actor):
    from accounts.models import TrustSafetyEvent

    return record_user_report_action(
        report,
        actor=actor,
        event_type=TrustSafetyEvent.EventType.SELLER_LISTINGS_ARCHIVED,
        title=f"Seller #{report.reported_user_id} listings archived from report #{report.pk}",
    )


def record_user_report_messaging_blocked(report, *, actor):
    from accounts.models import TrustSafetyEvent

    return record_user_report_action(
        report,
        actor=actor,
        event_type=TrustSafetyEvent.EventType.SELLER_MESSAGING_BLOCKED,
        title=f"Seller #{report.reported_user_id} messaging blocked from report #{report.pk}",
    )
