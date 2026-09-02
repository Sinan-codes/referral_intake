"""HTTP routes for the referral intake queue.

Kept thin: routes translate HTTP <-> the `db` layer and enforce the one rule
that belongs at this boundary -- status changes must follow
`ALLOWED_TRANSITIONS` -- everything else (normalization, dedup) already
happened before a referral ever reached this table.
"""

from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.db import (
    count_referrals,
    get_referral,
    list_referrals,
    list_referrals_in_duplicate_group,
    update_referral_status,
)
from app.models.api import (
    ErrorDetail,
    PaginationMeta,
    ReferralDetail,
    ReferralDetailResponse,
    ReferralListQuery,
    ReferralListResponse,
    ReferralSummary,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from app.models.referral import is_valid_transition

router = APIRouter(prefix="/referrals", tags=["referrals"])


def _not_found(referral_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ErrorDetail(
            code="not_found", message=f"referral {referral_id!r} not found"
        ).model_dump(),
    )


@router.get("", response_model=ReferralListResponse)
async def list_referrals_route(
    request: Request, query: Annotated[ReferralListQuery, Query()]
) -> ReferralListResponse:
    conn = request.app.state.db
    total = count_referrals(
        conn, status=query.status, source=query.source, urgency=query.urgency, q=query.q
    )
    referrals = list_referrals(
        conn,
        status=query.status,
        source=query.source,
        urgency=query.urgency,
        q=query.q,
        sort=query.sort,
        limit=query.page_size,
        offset=(query.page - 1) * query.page_size,
    )
    total_pages = math.ceil(total / query.page_size) if total else 0
    return ReferralListResponse(
        data=referrals,
        meta=PaginationMeta(
            page=query.page, page_size=query.page_size, total=total, total_pages=total_pages
        ),
    )


@router.get("/{referral_id}", response_model=ReferralDetailResponse)
async def get_referral_route(referral_id: str, request: Request) -> ReferralDetailResponse:
    conn = request.app.state.db
    referral = get_referral(conn, referral_id)
    if referral is None:
        raise _not_found(referral_id)

    duplicate_group: list[ReferralSummary] = []
    if referral.duplicate_group_id is not None:
        peers = list_referrals_in_duplicate_group(
            conn, referral.duplicate_group_id, exclude_id=referral.id
        )
        duplicate_group = [
            ReferralSummary(
                id=peer.id,
                source=peer.source,
                patient_name=peer.patient_name.raw_full_name,
                date_of_birth=peer.date_of_birth.isoformat() if peer.date_of_birth else None,
                received_at=peer.received_at.isoformat(),
                status=peer.status,
            )
            for peer in peers
        ]

    detail = ReferralDetail(**referral.model_dump(), duplicate_group=duplicate_group)
    return ReferralDetailResponse(data=detail)


@router.patch("/{referral_id}/status", response_model=StatusUpdateResponse)
async def update_status_route(
    referral_id: str, body: StatusUpdateRequest, request: Request
) -> StatusUpdateResponse:
    conn = request.app.state.db
    referral = get_referral(conn, referral_id)
    if referral is None:
        raise _not_found(referral_id)

    if not is_valid_transition(referral.status, body.status):
        raise HTTPException(
            status_code=409,
            detail=ErrorDetail(
                code="invalid_transition",
                message=(
                    f"cannot move referral from {referral.status.value!r} "
                    f"to {body.status.value!r}"
                ),
                field="status",
            ).model_dump(),
        )

    update_referral_status(conn, referral_id, body.status)
    updated = get_referral(conn, referral_id)
    return StatusUpdateResponse(data=updated)
