"""Request/response schemas for the HTTP boundary.

Kept separate from the internal domain model (`referral.Referral`) so the
wire format can evolve independently of storage/matching logic -- e.g. the
duplicate group embedded in a detail response is an API-shaping concern, not
something the domain model itself needs to carry. This is also the module
we'd point an OpenAPI-to-TypeScript generator at to share types with the
frontend, rather than hand-duplicating them on each side.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.referral import Referral, ReferralSource, ReferralStatus, Urgency


class ReferralSummary(BaseModel):
    """Lightweight referral shape used inside another referral's duplicate group.

    Deliberately not the full `Referral` -- embedding full records into each
    other's duplicate group would nest indefinitely for a larger cluster.
    """

    id: str
    source: ReferralSource
    patient_name: str
    date_of_birth: str | None = None
    received_at: str
    status: ReferralStatus


class ReferralDetail(Referral):
    duplicate_group: list[ReferralSummary] = Field(default_factory=list)


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ReferralListResponse(BaseModel):
    data: list[Referral]
    meta: PaginationMeta


class ReferralDetailResponse(BaseModel):
    data: ReferralDetail


class ReferralListQuery(BaseModel):
    """Query params for `GET /referrals`, bound via `Depends()` in the route."""

    status: ReferralStatus | None = None
    source: ReferralSource | None = None
    urgency: Urgency | None = None
    q: str | None = None  # free-text match on patient name
    sort: str = "-received_at"  # "-received_at" | "received_at"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class StatusUpdateRequest(BaseModel):
    status: ReferralStatus


class StatusUpdateResponse(BaseModel):
    data: Referral


class ErrorDetail(BaseModel):
    code: str  # machine-readable, e.g. "invalid_transition", "not_found"
    message: str
    field: str | None = None  # set for a single-field validation failure


class ErrorResponse(BaseModel):
    error: ErrorDetail
