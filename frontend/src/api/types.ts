/**
 * Mirrors `backend/app/models/referral.py` and `backend/app/models/api.py`.
 *
 * The backend is Python, so these can't be generated from a shared source
 * yet -- api.py is explicitly written as the module an OpenAPI-to-TS
 * generator would point at later. Until then this file is kept in sync by
 * hand against the response shapes those Pydantic models produce.
 */

export type ReferralSource = 'efax' | 'ehr_fhir' | 'web_form'

export type Urgency = 'routine' | 'urgent' | 'stat'

export type ReferralStatus = 'new' | 'in_review' | 'accepted' | 'rejected' | 'scheduled'

export interface PatientName {
  raw_full_name: string
  first_name: string | null
  last_name: string | null
}

export interface Referral {
  id: string
  source: ReferralSource
  source_record_id: string
  received_at: string
  patient_name: PatientName
  date_of_birth: string | null
  referring_provider: string | null
  reason: string | null
  urgency: Urgency
  status: ReferralStatus
  duplicate_group_id: string | null
  possible_duplicate: boolean
}

export interface ReferralSummary {
  id: string
  source: ReferralSource
  patient_name: string
  date_of_birth: string | null
  received_at: string
  status: ReferralStatus
}

export interface ReferralDetail extends Referral {
  duplicate_group: ReferralSummary[]
}

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface ReferralListResponse {
  data: Referral[]
  meta: PaginationMeta
}

export interface ReferralDetailResponse {
  data: ReferralDetail
}

export interface StatusUpdateResponse {
  data: Referral
}

export interface ErrorDetail {
  code: string
  message: string
  field: string | null
}

export interface ErrorResponse {
  error: ErrorDetail
}
