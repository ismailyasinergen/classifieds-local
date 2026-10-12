from django.db import transaction
from django.db.transaction import TransactionManagementError

from .case_inputs import CaseConflict
from .models import CaseSubmissionReceipt


def require_atomic():
    if not transaction.get_connection().in_atomic_block:
        raise TransactionManagementError("Case writes require an actor anchor inside atomic.")


def lookup_receipt(*, actor_id, operation, token, fingerprint):
    require_atomic()
    receipt = CaseSubmissionReceipt.objects.filter(
        actor_id=actor_id, operation=operation, client_token=token).first()
    if receipt is not None and receipt.fingerprint != fingerprint:
        raise CaseConflict("token_conflict")
    return receipt


def record_receipt(*, actor_id, operation, token, fingerprint, report_id=None, appeal_id=None):
    require_atomic()
    return CaseSubmissionReceipt.objects.create(
        actor_id=actor_id, operation=operation, client_token=token, fingerprint=fingerprint,
        report_id=report_id, appeal_id=appeal_id)
