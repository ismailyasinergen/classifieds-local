from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.rate_limits import enforce_action_limit
from .case_audit import append_case_event
from .case_inputs import CaseConflict, SubmissionResult, normalize_text, parse_client_token, submission_fingerprint
from .case_locking import lock_report_case
from .case_policies import require_appeal_reviewer, require_case_actor
from .messaging import revoke_messaging_restriction
from .models import Appeal, AppealDecision, MessagingRestriction, ReportDecision, Restriction
from .submission_receipts import lookup_receipt, record_receipt


def submit_appeal(*, actor, decision_id, explanation, client_token):
    require_case_actor(actor=actor)
    explanation = normalize_text(explanation, field="explanation")
    token = parse_client_token(client_token)
    fingerprint = submission_fingerprint(operation="appeal", target_type="decision",
        target_id=decision_id, reason_code="", explanation=explanation)
    report_id = ReportDecision.objects.values_list("report_id", flat=True).get(pk=decision_id)
    with transaction.atomic():
        case = lock_report_case(actor=actor, report_id=report_id)
        current = require_case_actor(actor=case.target.actor)
        decision = case.decision
        if decision is None or str(decision.pk) != str(decision_id):
            raise CaseConflict("identity_changed")
        if case.report.subject_user_id != current.pk or decision.action == "no_action":
            raise PermissionDenied("Yalnız kendi kısıt kararınıza itiraz edebilirsiniz.")
        receipt = lookup_receipt(actor_id=current.pk, operation="appeal", token=token, fingerprint=fingerprint)
        if receipt is not None:
            return SubmissionResult(Appeal.objects.get(pk=receipt.appeal_id, appellant_id=current.pk), "replayed")
        if case.appeal is not None:
            if case.appeal.appellant_id != current.pk:
                raise CaseConflict("identity_changed")
            record_receipt(actor_id=current.pk, operation="appeal", token=token,
                           fingerprint=fingerprint, appeal_id=case.appeal.pk)
            return SubmissionResult(case.appeal, "existing_target")
        now = timezone.now()
        enforce_action_limit(events=Appeal.objects.filter(appellant_id=current.pk), action="appeal", at=now)
        appeal = Appeal.objects.create(decision=decision, appellant=current,
            explanation=explanation, client_token=token, created_at=now)
        record_receipt(actor_id=current.pk, operation="appeal", token=token,
                       fingerprint=fingerprint, appeal_id=appeal.pk)
        append_case_event(actor_id=current.pk, report_id=case.report.pk, appeal_id=appeal.pk, action="appeal_created")
        return SubmissionResult(appeal, "created")


def decide_appeal(*, actor, appeal_id, outcome, reason):
    reason = normalize_text(reason, field="reason")
    if outcome not in AppealDecision.Outcome.values:
        raise ValidationError({"outcome": "Geçerli bir itiraz kararı seçin."})
    identity = Appeal.objects.values_list("decision_id", "decision__report_id", "appellant_id").get(pk=appeal_id)
    with transaction.atomic():
        case = lock_report_case(actor=actor, report_id=identity[1], extra_user_ids=[identity[2]])
        appeal, decision = case.appeal, case.decision
        if (appeal is None or str(appeal.pk) != str(appeal_id) or appeal.decision_id != identity[0]
                or appeal.appellant_id != identity[2] or appeal.appellant_id != case.report.subject_user_id):
            raise CaseConflict("identity_changed")
        current = require_appeal_reviewer(actor=case.target.actor, decision=decision)
        if decision.action == "no_action":
            raise CaseConflict("invalid_sanction")
        if outcome == "revoke" and decision.messaging_restriction_id and not current.has_perm("moderation.restrict_messaging"):
            raise PermissionDenied("Mesajlaşma kısıtlama izniniz yok.")
        if case.appeal_decision is not None:
            result = case.appeal_decision
            if (result.actor_id, result.outcome, result.reason) != (current.pk, outcome, reason):
                raise CaseConflict("appeal_decision_conflict")
            return result
        if decision.visibility_restriction_id:
            restriction = Restriction.objects.select_for_update().get(pk=decision.visibility_restriction_id)
            if (case.report.target_type != "listing" or restriction.listing_id != case.target.listing.pk
                    or restriction.seller_id is not None or restriction.actor_id != decision.actor_id):
                raise CaseConflict("identity_changed")
            if outcome == "revoke" and restriction.revoked_at is None:
                restriction.revoked_at = timezone.now()
                restriction.save(update_fields=["revoked_at"])
        elif decision.messaging_restriction_id:
            restriction = MessagingRestriction.objects.select_for_update().get(pk=decision.messaging_restriction_id)
            if (case.report.target_type != "message" or restriction.user_id != case.report.subject_user_id
                    or restriction.actor_id != decision.actor_id):
                raise CaseConflict("identity_changed")
            if outcome == "revoke":
                revoke_messaging_restriction(actor=current, restriction_id=restriction.pk)
        else:
            raise CaseConflict("invalid_sanction")
        result = AppealDecision.objects.create(appeal=appeal, actor=current, outcome=outcome, reason=reason)
        append_case_event(actor_id=current.pk, report_id=case.report.pk, appeal_id=appeal.pk, action="appeal_decided")
        return result
