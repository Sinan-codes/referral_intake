import type {
  ErrorResponse,
  ReferralDetailResponse,
  ReferralListQuery,
  ReferralListResponse,
  ReferralStatus,
  StatusUpdateResponse,
} from './types'

/** Thrown for any non-2xx response, carrying the server's error envelope. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly field: string | null

  constructor(status: number, error: ErrorResponse['error']) {
    super(error.message)
    this.name = 'ApiError'
    this.status = status
    this.code = error.code
    this.field = error.field ?? null
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!res.ok) {
    const body: ErrorResponse | null = await res.json().catch(() => null)
    if (body?.error) throw new ApiError(res.status, body.error)
    throw new ApiError(res.status, { code: 'unknown_error', message: res.statusText, field: null })
  }

  return res.json() as Promise<T>
}

function toSearchParams(params: ReferralListQuery): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export function listReferrals(params: ReferralListQuery): Promise<ReferralListResponse> {
  return request(`/referrals${toSearchParams(params)}`)
}

export function getReferral(id: string): Promise<ReferralDetailResponse> {
  return request(`/referrals/${encodeURIComponent(id)}`)
}

export function updateReferralStatus(
  id: string,
  status: ReferralStatus,
): Promise<StatusUpdateResponse> {
  return request(`/referrals/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}
