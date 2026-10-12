import hashlib
import json
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from django.core.exceptions import ValidationError

from .models import Appeal, ContentReport

LISTING_REASONS = (
    ("fraud", "Dolandırıcılık şüphesi"), ("prohibited", "Uygun olmayan ürün veya içerik"),
    ("misleading", "Yanıltıcı bilgi"), ("spam", "Spam/tekrar"), ("other", "Diğer"),
)
MESSAGE_REASONS = (
    ("fraud", "Dolandırıcılık şüphesi"), ("harassment", "Taciz/tehdit"),
    ("spam", "Spam/tekrar"), ("other", "Diğer"),
)


class CaseConflict(ValidationError):
    def __init__(self, code="case_conflict"):
        super().__init__("İstek veya içerik değişti; güncel sayfayı yeniden yükleyin.", code=code)


@dataclass(frozen=True)
class SubmissionResult:
    record: ContentReport | Appeal
    disposition: Literal["created", "replayed", "existing_target"]


def normalize_text(value, *, field, required=True, limit=2000):
    if not isinstance(value, str):
        raise ValidationError({field: "Geçerli bir metin girin."})
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValidationError({field: "Geçerli bir metin girin."}) from None
    if "\x00" in value or len(value) > limit or (required and not value):
        raise ValidationError({field: f"1–{limit} karakterlik geçerli bir metin girin."})
    return value


def parse_client_token(value):
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            pass
    raise ValidationError({"client_token": "Gönderim kimliği geçersiz; sayfayı yeniden yükleyin."})


def submission_fingerprint(*, operation, target_type, target_id, reason_code, explanation):
    payload = dict(operation=operation, target_type=target_type, target_id=str(target_id),
                   reason_code=reason_code, explanation=normalize_text(explanation, field="explanation"))
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()
