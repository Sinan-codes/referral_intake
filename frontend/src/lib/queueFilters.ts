import type { ReferralSource, ReferralStatus, Urgency } from '../api/types'

export interface QueueFiltersState {
  status: ReferralStatus | ''
  source: ReferralSource | ''
  urgency: Urgency | ''
  q: string
  sort: '-received_at' | 'received_at'
}

export function hasActiveFilters(filters: QueueFiltersState): boolean {
  return filters.status !== '' || filters.source !== '' || filters.urgency !== '' || filters.q !== ''
}
