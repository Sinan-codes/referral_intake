"""Normalizes FHIR ServiceRequest records (polled from the partner EHR) into
the internal `Referral` model.

This is the most structured of the three sources, but two fields still need
translation: `subject.display` arrives as "LAST, FIRST" and has to be
reordered/split, and `priority` uses FHIR's own vocabulary rather than ours.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

from app.models.raw import FhirServiceRequest
from app.models.referral import PatientName, Referral, ReferralSource, Urgency
from app.normalization.common import (
    UNKNOWN_PRIORITY_FALLBACK,
    NormalizationError,
    clean,
    normalize_name_casing,
)

_SOURCE = "ehr_fhir"

_PRIORITY_MAP: dict[str, Urgency] = {
    "ROUTINE": Urgency.ROUTINE,
    "URGENT": Urgency.URGENT,
    "ASAP": Urgency.STAT,
    "STAT": Urgency.STAT,
}


def normalize_fhir_record(record: FhirServiceRequest) -> Referral:
    """Map one raw FHIR ServiceRequest onto a `Referral`.

    Raises `NormalizationError` when the record has no usable patient
    identity or no `authoredOn` -- both are required fields on `Referral`
    with nothing sensible to default to. Everything else (DOB, reason,
    requester, priority) degrades gracefully instead of failing the record.
    """

    display = (record.subject.display if record.subject else None) or ""
    display = display.strip()
    if not display:
        raise NormalizationError(_SOURCE, record.id, "missing patient name")

    received_at = _parse_authored_on(record.authoredOn)
    if received_at is None:
        raise NormalizationError(_SOURCE, record.id, "missing or unparseable authoredOn")

    first_name, last_name = _split_display_name(display)
    raw_full_name = " ".join(part for part in (first_name, last_name) if part) or display

    return Referral(
        id=f"{_SOURCE}:{record.id}",
        source=ReferralSource.EHR_FHIR,
        source_record_id=record.id,
        received_at=received_at,
        patient_name=PatientName(
            raw_full_name=raw_full_name,
            first_name=first_name,
            last_name=last_name,
        ),
        date_of_birth=_parse_birth_date(record.subject.birthDate if record.subject else None),
        referring_provider=clean(record.requester.display if record.requester else None),
        reason=_first_reason_text(record),
        urgency=_map_priority(record.priority),
    )


def normalize_fhir_records(
    records: Iterable[FhirServiceRequest],
) -> tuple[list[Referral], list[NormalizationError]]:
    """Normalize a batch, keeping bad records from blocking good ones."""

    referrals: list[Referral] = []
    errors: list[NormalizationError] = []
    for record in records:
        try:
            referrals.append(normalize_fhir_record(record))
        except NormalizationError as exc:
            errors.append(exc)
    return referrals, errors


def _parse_authored_on(raw_value: str | None) -> datetime | None:
    if not raw_value or not raw_value.strip():
        return None
    try:
        return datetime.fromisoformat(raw_value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_birth_date(raw_value: str | None) -> date | None:
    if not raw_value or not raw_value.strip():
        return None
    try:
        return date.fromisoformat(raw_value.strip())
    except ValueError:
        return None


def _split_display_name(display: str) -> tuple[str | None, str | None]:
    # FHIR `display` arrives as "LAST, FIRST", always caps in this feed. No
    # comma at all (malformed upstream data) degrades to "whole string as
    # last name, no first name" rather than failing the record.
    last, _, first = display.partition(",")
    last_name = normalize_name_casing(last.strip()) or None
    first_name = normalize_name_casing(first.strip()) or None
    return first_name, last_name


def _first_reason_text(record: FhirServiceRequest) -> str | None:
    if not record.reasonCode:
        return None
    return clean(record.reasonCode[0].text)


def _map_priority(raw_priority: str | None) -> Urgency:
    if raw_priority is None:
        return UNKNOWN_PRIORITY_FALLBACK
    return _PRIORITY_MAP.get(raw_priority.strip().upper(), UNKNOWN_PRIORITY_FALLBACK)
