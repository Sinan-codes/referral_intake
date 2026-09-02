"""The normalized internal referral model.

Every source (efax, ehr_fhir, web_form) is mapped into this one shape so the
rest of the app never has to branch on where a referral came from. Fields
that any source can legitimately fail to supply are `Optional` -- that's a
deliberate signal for callers to handle the missing case, not an oversight.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, computed_field, field_validator


class ReferralSource(str, Enum):
    EFAX = "efax"
    EHR_FHIR = "ehr_fhir"
    WEB_FORM = "web_form"


class Urgency(str, Enum):
    """One ordinal scale collapsing three source vocabularies onto it.

    - efax:     ROUTINE -> routine, STAT -> stat
    - ehr_fhir: routine -> routine, urgent -> urgent, asap (or stat) -> stat
    - web_form: urgent=False -> routine, urgent=True -> urgent
                (the boolean can never express `stat` -- a lossy mapping,
                documented in the README as a duplicate/urgency failure mode)
    """

    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"


class ReferralStatus(str, Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"


# The only transitions the workflow diagram allows:
#   new -> in_review -> {accepted -> scheduled, rejected}
# `scheduled` and `rejected` are terminal. Anything not listed here must be
# rejected by the API, not just hidden in the UI.
ALLOWED_TRANSITIONS: dict[ReferralStatus, frozenset[ReferralStatus]] = {
    ReferralStatus.NEW: frozenset({ReferralStatus.IN_REVIEW}),
    ReferralStatus.IN_REVIEW: frozenset(
        {ReferralStatus.ACCEPTED, ReferralStatus.REJECTED}
    ),
    ReferralStatus.ACCEPTED: frozenset({ReferralStatus.SCHEDULED}),
    ReferralStatus.REJECTED: frozenset(),
    ReferralStatus.SCHEDULED: frozenset(),
}


def is_valid_transition(current: ReferralStatus, target: ReferralStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


class PatientName(BaseModel):
    """Best-effort split of whatever name shape the source used.

    `raw_full_name` is always populated -- it's what we display and search
    on. `first_name`/`last_name` are Optional because splitting "GRACE
    DELACROIX" or "RENTERIA, MARGUERITE" into parts is a heuristic, not a
    guarantee, and callers must not assume it always succeeded.
    """

    raw_full_name: str
    first_name: str | None = None
    last_name: str | None = None


class Referral(BaseModel):
    id: str  # stable & deterministic: f"{source.value}:{source_record_id}"
    source: ReferralSource
    source_record_id: str
    received_at: datetime  # always normalized to tz-aware UTC

    patient_name: PatientName
    date_of_birth: date | None = None  # a source can fail to supply this

    referring_provider: str | None = None
    reason: str | None = None  # None means "unknown", not "empty string"

    urgency: Urgency
    status: ReferralStatus = ReferralStatus.NEW

    duplicate_group_id: str | None = None  # set once duplicate detection runs

    @field_validator("received_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def possible_duplicate(self) -> bool:
        return self.duplicate_group_id is not None
