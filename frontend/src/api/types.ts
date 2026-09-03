/**
 * Thin aliases over `schema.gen.ts`, generated from the backend's own
 * OpenAPI schema rather than hand-mirroring `backend/app/models/*.py`.
 *
 * Regenerate after changing anything in `backend/app/models/api.py` or
 * `backend/app/routers`:
 *
 *   cd backend && uv run python -m scripts.export_openapi
 *   cd frontend && npm run generate:types
 *
 * The rest of the app imports these names from here rather than reaching
 * into `components["schemas"][...]` directly, so a future switch of
 * generator/tooling only touches this one file.
 */
import type { components, operations } from './schema.gen'

export type ReferralSource = components['schemas']['ReferralSource']
export type Urgency = components['schemas']['Urgency']
export type ReferralStatus = components['schemas']['ReferralStatus']
export type PatientName = components['schemas']['PatientName']
export type Referral = components['schemas']['Referral']
export type ReferralSummary = components['schemas']['ReferralSummary']
export type ReferralDetail = components['schemas']['ReferralDetail']
export type PaginationMeta = components['schemas']['PaginationMeta']
export type ReferralListResponse = components['schemas']['ReferralListResponse']
export type ReferralDetailResponse = components['schemas']['ReferralDetailResponse']
export type StatusUpdateResponse = components['schemas']['StatusUpdateResponse']
export type ErrorDetail = components['schemas']['ErrorDetail']
export type ErrorResponse = components['schemas']['ErrorResponse']

/** Query params for `GET /referrals`, straight from the operation's own
 * generated parameter type -- so the sort literal and filter enums stay
 * tied to the backend's actual `ReferralListQuery`. */
export type ReferralListQuery = NonNullable<
  operations['list_referrals_route_referrals_get']['parameters']['query']
>
