import type { ReferralSource, ReferralStatus, Urgency } from '../api/types'
import { STATUS_LABELS } from '../lib/statusWorkflow'

export interface QueueFiltersState {
  status: ReferralStatus | ''
  source: ReferralSource | ''
  urgency: Urgency | ''
  q: string
  sort: '-received_at' | 'received_at'
}

const STATUS_OPTIONS: ReferralStatus[] = ['new', 'in_review', 'accepted', 'rejected', 'scheduled']
const SOURCE_OPTIONS: { value: ReferralSource; label: string }[] = [
  { value: 'efax', label: 'eFax' },
  { value: 'ehr_fhir', label: 'EHR (FHIR)' },
  { value: 'web_form', label: 'Web form' },
]
const URGENCY_OPTIONS: { value: Urgency; label: string }[] = [
  { value: 'routine', label: 'Routine' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'stat', label: 'STAT' },
]

const selectClass =
  'rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-700 focus:border-slate-500 focus:outline-none'

export function QueueFilters({
  filters,
  onChange,
}: {
  filters: QueueFiltersState
  onChange: (next: QueueFiltersState) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <input
        type="search"
        placeholder="Search patient name…"
        value={filters.q}
        onChange={(e) => onChange({ ...filters, q: e.target.value })}
        className="min-w-48 flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 focus:border-slate-500 focus:outline-none"
      />

      <select
        value={filters.status}
        onChange={(e) => onChange({ ...filters, status: e.target.value as ReferralStatus | '' })}
        className={selectClass}
      >
        <option value="">All statuses</option>
        {STATUS_OPTIONS.map((status) => (
          <option key={status} value={status}>
            {STATUS_LABELS[status]}
          </option>
        ))}
      </select>

      <select
        value={filters.source}
        onChange={(e) => onChange({ ...filters, source: e.target.value as ReferralSource | '' })}
        className={selectClass}
      >
        <option value="">All sources</option>
        {SOURCE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <select
        value={filters.urgency}
        onChange={(e) => onChange({ ...filters, urgency: e.target.value as Urgency | '' })}
        className={selectClass}
      >
        <option value="">All urgencies</option>
        {URGENCY_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <select
        value={filters.sort}
        onChange={(e) => onChange({ ...filters, sort: e.target.value as QueueFiltersState['sort'] })}
        className={selectClass}
      >
        <option value="-received_at">Newest first</option>
        <option value="received_at">Oldest first</option>
      </select>
    </div>
  )
}
