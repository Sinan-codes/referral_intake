"""Normalizes public web-form submissions into the internal `Referral` model.

This is the most reliable source: the name arrives pre-split into first/last
and `urgent` is an explicit boolean rather than free text needing a lookup.
The one real translation is capacity: a boolean can express "routine" or
"urgent" but never "stat" -- a coordinator filling out this form on a
patient's behalf has no way to signal the same top urgency efax and
ehr_fhir can. See the README for how that caps this source's matching.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

from app.models.raw import WebFormRecord
from app.models.referral import PatientName, Referral, ReferralSource, Urgency
from app.normalization.common import NormalizationError, clean, normalize_name_casing

_SOURCE = "web_form"


def normalize_web_form_record(record: WebFormRecord) -> Referral:
    """Map one raw web-form submission onto a `Referral`.

    Raises `NormalizationError` when the record has no usable patient name
    or no `submittedAt` -- both are required fields on `Referral` with
    nothing sensible to default to.
    """

    first_name = _clean_name_part(record.firstName)
    last_name = _clean_name_part(record.lastName)
    if not first_name and not last_name:
        raise NormalizationError(_SOURCE, record.submissionId, "missing patient name")

    received_at = _parse_submitted_at(record.submittedAt)
    if received_at is None:
        raise NormalizationError(
            _SOURCE, record.submissionId, "missing or unparseable submittedAt"
        )

    raw_full_name = " ".join(part for part in (first_name, last_name) if part)

    return Referral(
        id=f"{_SOURCE}:{record.submissionId}",
        source=ReferralSource.WEB_FORM,
        source_record_id=record.submissionId,
        received_at=received_at,
        patient_name=PatientName(
            raw_full_name=raw_full_name,
            first_name=first_name,
            last_name=last_name,
        ),
        date_of_birth=_parse_dob(record.dateOfBirth),
        referring_provider=clean(record.referredBy),
        reason=clean(record.notes),
        # The form only has a boolean, so it can never express `stat` --
        # a documented ceiling on this source's urgency signal.
        urgency=Urgency.URGENT if record.urgent else Urgency.ROUTINE,
    )


def normalize_web_form_records(
    records: Iterable[WebFormRecord],
) -> tuple[list[Referral], list[NormalizationError]]:
    """Normalize a batch, keeping bad records from blocking good ones."""

    referrals: list[Referral] = []
    errors: list[NormalizationError] = []
    for record in records:
        try:
            referrals.append(normalize_web_form_record(record))
        except NormalizationError as exc:
            errors.append(exc)
    return referrals, errors


def _clean_name_part(value: str | None) -> str | None:
    cleaned = clean(value)
    return normalize_name_casing(cleaned) if cleaned else None


def _parse_submitted_at(raw_value: str | None) -> datetime | None:
    if not raw_value or not raw_value.strip():
        return None
    try:
        return datetime.fromisoformat(raw_value.strip())
    except ValueError:
        return None


def _parse_dob(raw_value: str | None) -> date | None:
    if not raw_value or not raw_value.strip():
        return None
    try:
        return date.fromisoformat(raw_value.strip())
    except ValueError:
        return None
