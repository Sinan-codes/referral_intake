"""Raw, source-shaped payloads exactly as each upstream system sends them.

These models intentionally stay permissive (most fields Optional) because each
source is unreliable in its own way: efax is OCR noise, ehr_fhir is a partial
FHIR resource, web_form is a public form nobody validated. Business rules,
defaults, and unit conversions belong in the normalizer that maps these into
`referral.Referral` -- not here. This layer's only job is "what did the
source actually send".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _LenientModel(BaseModel):
    """Base for raw source payloads: trim OCR/user whitespace, ignore unknown fields."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


# --- efax --------------------------------------------------------------------


class EfaxPatient(_LenientModel):
    full_name: str | None = None
    dob: str | None = None  # "MM/DD/YYYY" -- OCR'd, not guaranteed parseable


class EfaxRecord(_LenientModel):
    id: str
    received_ts: int  # unix seconds, UTC
    patient: EfaxPatient
    referring_provider: str | None = None
    reason_free_text: str | None = None
    priority: str | None = None  # source vocabulary, e.g. "ROUTINE" / "STAT"
    page_count: int | None = None


class EfaxSource(_LenientModel):
    description: str
    records: list[EfaxRecord]


# --- ehr_fhir ------------------------------------------------------------------


class FhirReasonCode(_LenientModel):
    text: str | None = None


class FhirSubject(_LenientModel):
    reference: str | None = None
    display: str | None = None  # "LAST, FIRST"
    birthDate: str | None = None  # ISO date, e.g. "1953-01-13"


class FhirRequester(_LenientModel):
    display: str | None = None


class FhirServiceRequest(_LenientModel):
    resourceType: Literal["ServiceRequest"]
    id: str
    status: str | None = None
    authoredOn: str | None = None  # ISO 8601 datetime with explicit offset/"Z"
    subject: FhirSubject | None = None
    requester: FhirRequester | None = None
    reasonCode: list[FhirReasonCode] | None = None
    priority: str | None = None  # e.g. "routine" / "urgent" / "asap"


class FhirSource(_LenientModel):
    description: str
    records: list[FhirServiceRequest]


# --- web_form ------------------------------------------------------------------


class WebFormRecord(_LenientModel):
    submissionId: str
    submittedAt: str  # ISO 8601 with explicit UTC offset
    firstName: str | None = None
    lastName: str | None = None
    dateOfBirth: str | None = None  # ISO date
    referredBy: str | None = None
    notes: str | None = None
    urgent: bool = False
    consentToContact: bool = False


class WebFormSource(_LenientModel):
    description: str
    records: list[WebFormRecord]


# --- seed file container --------------------------------------------------------


class ReferralSources(_LenientModel):
    efax: EfaxSource
    ehr_fhir: FhirSource
    web_form: WebFormSource


class ReferralsSeedFile(_LenientModel):
    sources: ReferralSources
