from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from events.models import OutboxEvent
from listings.models import Listing, ListingRevision
from listings.publication import StalePublicRevision, locked_revision, require_publishable_content
from listings.services import InvalidRevisionState
from .models import ModerationDecision, PriceChange
from .policies import require_reviewer


def _reason(reason):
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 2000:
        raise ValidationError({"reason": "1–2000 karakterlik inceleme gerekçesi girin."})
    return reason.strip()


def approve_revision(*, actor: User, revision_id: int,
                     expected_public_revision_id: int | None, reason: str) -> ListingRevision:
    with transaction.atomic():
        listing, revision = locked_revision(revision_id=revision_id)
        require_reviewer(actor=actor)
        if revision.status == ListingRevision.Status.APPROVED:
            if listing.public_revision_id == revision.pk:
                return revision
            raise InvalidRevisionState("Eski onaylı revizyon yeniden yayımlanamaz.")
        if revision.status != ListingRevision.Status.SUBMITTED:
            raise InvalidRevisionState("Yalnız gönderilmiş revizyon onaylanabilir.")
        if expected_public_revision_id is not None and (
                type(expected_public_revision_id) is not int or expected_public_revision_id < 1):
            raise ValidationError({"expected_public_revision_id": "Geçerli revizyon kimliği girin."})
        if listing.public_revision_id != expected_public_revision_id:
            raise StalePublicRevision()
        if listing.lifecycle == Listing.Lifecycle.CLOSED:
            raise InvalidRevisionState("Kapalı ilan için yeni revizyon yayımlanamaz.")
        reason = _reason(reason)
        require_publishable_content(revision=revision)
        previous = None
        if listing.public_revision_id is not None:
            previous = ListingRevision.objects.get(pk=listing.public_revision_id, listing=listing, status="approved")
        now = timezone.now()
        first_publication = listing.first_published_at is None
        revision.status = ListingRevision.Status.APPROVED
        revision.save(update_fields=["status", "updated_at"])
        ModerationDecision.objects.create(revision=revision, actor=actor, outcome="approved",
                                          reason=reason, decided_at=now)
        listing.public_revision = revision
        if previous is None:
            listing.lifecycle = Listing.Lifecycle.LIVE
        if listing.first_published_at is None:
            listing.first_published_at = now
        listing.save(update_fields=["public_revision", "lifecycle", "first_published_at", "updated_at"])
        changed_price = previous is not None and (
            previous.price != revision.price or previous.currency != revision.currency)
        change = None
        if changed_price:
            change = PriceChange.objects.create(
                listing=listing, revision=revision, previous_revision=previous,
                old_amount=previous.price, new_amount=revision.price,
                old_currency=previous.currency, new_currency=revision.currency, published_at=now)
        from events.boundaries import next_publication_boundary
        boundary = next_publication_boundary() if first_publication else None
        OutboxEvent.objects.create(
            event_type=OutboxEvent.Type.REVISION_PUBLISHED, revision=revision,
            payload={"listing_id": str(listing.pk), "revision_id": revision.pk,
                     "price": format(revision.price, ".2f"), "currency": revision.currency,
                     "notification_version": 1, "first_publication": first_publication,
                     "publication_boundary": boundary})
        if change is not None:
            OutboxEvent.objects.create(
                event_type=OutboxEvent.Type.PRICE_CHANGED, revision=revision,
                payload={"listing_id": str(listing.pk), "revision_id": revision.pk,
                         "previous_revision_id": previous.pk,
                         "old_amount": format(change.old_amount, ".2f"),
                         "new_amount": format(change.new_amount, ".2f"),
                         "old_currency": change.old_currency, "new_currency": change.new_currency,
                         "is_price_drop": change.is_price_drop})
        return revision


def reject_revision(*, actor: User, revision_id: int, reason: str) -> ListingRevision:
    with transaction.atomic():
        listing, revision = locked_revision(revision_id=revision_id)
        require_reviewer(actor=actor)
        if revision.status != ListingRevision.Status.SUBMITTED:
            raise InvalidRevisionState("Yalnız gönderilmiş revizyon reddedilebilir.")
        reason = _reason(reason)
        revision.status = ListingRevision.Status.REJECTED
        revision.save(update_fields=["status", "updated_at"])
        ModerationDecision.objects.create(revision=revision, actor=actor, outcome="rejected", reason=reason)
        return revision
