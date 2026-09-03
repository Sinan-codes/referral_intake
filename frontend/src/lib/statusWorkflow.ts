import type { ReferralStatus } from '../api/types'

/**
 * Mirrors `ALLOWED_TRANSITIONS` in `backend/app/models/referral.py`.
 *
 * The server is the source of truth and re-validates every transition on
 * `PATCH /referrals/:id/status` -- this copy only drives which action
 * buttons the UI offers, so a stale copy fails safe (a disallowed click
 * still gets rejected by the server, surfaced via `ApiError`).
 */
export const ALLOWED_TRANSITIONS: Record<ReferralStatus, ReferralStatus[]> = {
  new: ['in_review'],
  in_review: ['accepted', 'rejected'],
  accepted: ['scheduled'],
  rejected: [],
  scheduled: [],
}

export const STATUS_LABELS: Record<ReferralStatus, string> = {
  new: 'New',
  in_review: 'In review',
  accepted: 'Accepted',
  rejected: 'Rejected',
  scheduled: 'Scheduled',
}

export function nextStatuses(status: ReferralStatus): ReferralStatus[] {
  return ALLOWED_TRANSITIONS[status]
}
