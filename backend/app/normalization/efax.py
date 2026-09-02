"""Normalizes efax OCR records into the internal `Referral` model.

efax is the messiest source: OCR output, fields routinely missing or
garbled. The rules here are deliberately conservative about what counts as
unusable (no patient name at all) versus merely degraded (unparseable DOB,
unrecognized priority) -- degraded data still produces a Referral that a
coordinator can see and fix, since dropping it silently would be worse than
showing it with a gap.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timezone

from app.models.raw import EfaxRecord
from app.models.referral import PatientName, Referral, ReferralSource, Urgency
from app.normalization.common import (
    UNKNOWN_PRIORITY_FALLBACK,
    NormalizationError,
    clean,
    normalize_name_casing,
)

_SOURCE = "efax"

_PRIORITY_MAP: dict[str, Urgency] = {
    "ROUTINE": Urgency.ROUTINE,
    "STAT": Urgency.STAT,
}

_DOB_FORMAT = "%m/%d/%Y"


def normalize_efax_record(record: EfaxRecord) -> Referral:
    """Map one raw efax record onto a `Referral`.

    Raises `NormalizationError` only when the record has no patient name --
    everything else missing or malformed degrades gracefully instead of
    failing the whole record.
    """

    full_name = (record.patient.full_name or "").strip()
    if not full_name:
        raise NormalizationError(_SOURCE, record.id, "missing patient name")

    display_name = normalize_name_casing(full_name)
    first_name, last_name = _split_name(display_name)

    return Referral(
        id=f"{_SOURCE}:{record.id}",
        source=ReferralSource.EFAX,
        source_record_id=record.id,
        # unix seconds, UTC -- the one timestamp encoding with no timezone
        # ambiguity to resolve at all.
        received_at=datetime.fromtimestamp(record.received_ts, tz=timezone.utc),
        patient_name=PatientName(
            raw_full_name=display_name,
            first_name=first_name,
            last_name=last_name,
        ),
        date_of_birth=_parse_dob(record.patient.dob),
        referring_provider=clean(record.referring_provider),
        reason=clean(record.reason_free_text),
        urgency=_map_priority(record.priority),
    )


def normalize_efax_records(
    records: Iterable[EfaxRecord],
) -> tuple[list[Referral], list[NormalizationError]]:
    """Normalize a batch, keeping bad records from blocking good ones.

    Returns (referrals, errors) rather than raising, so the caller (e.g. a
    seed-loading script) decides whether to log-and-skip or hard-fail.
    """

    referrals: list[Referral] = []
    errors: list[NormalizationError] = []
    for record in records:
        try:
            referrals.append(normalize_efax_record(record))
        except NormalizationError as exc:
            errors.append(exc)
    return referrals, errors


def _split_name(full_name: str) -> tuple[str | None, str | None]:
    parts = full_name.split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _parse_dob(raw_dob: str | None) -> date | None:
    if not raw_dob or not raw_dob.strip():
        return None
    try:
        return datetime.strptime(raw_dob.strip(), _DOB_FORMAT).date()
    except ValueError:
        # Garbled OCR date: DOB becomes "unknown" rather than failing the record.
        return None


def _map_priority(raw_priority: str | None) -> Urgency:
    if raw_priority is None:
        return UNKNOWN_PRIORITY_FALLBACK
    return _PRIORITY_MAP.get(raw_priority.strip().upper(), UNKNOWN_PRIORITY_FALLBACK)
