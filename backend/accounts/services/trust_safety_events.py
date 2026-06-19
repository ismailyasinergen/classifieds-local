
# TRUST_SAFETY_EVENT_SERVICE_V1
def record_trust_safety_event(
    *,
    event_type,
    title,
    actor=None,
    target_user=None,
    listing=None,
    listing_report=None,
    user_report=None,
    appeal=None,
    public_note="",
    internal_note="",
    metadata=None,
):
    from accounts.models import TrustSafetyEvent

    if target_user is None:
        if user_report and getattr(user_report, "reported_user", None):
            target_user = user_report.reported_user
        elif listing and getattr(listing, "owner", None):
            target_user = listing.owner
        elif appeal and getattr(appeal, "appellant", None):
            target_user = appeal.appellant

    return TrustSafetyEvent.objects.create(
        event_type=event_type,
        title=title,
        actor=actor,
        target_user=target_user,
        listing=listing,
        listing_report=listing_report,
        user_report=user_report,
        appeal=appeal,
        public_note=public_note or "",
        internal_note=internal_note or "",
        metadata=metadata or {},
    )
