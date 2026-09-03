import type { ReferralSource, ReferralStatus, Urgency } from '../api/types'
import { STATUS_LABELS } from '../lib/statusWorkflow'
import { Button } from './Button'

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

const controlClass =
  'h-9 rounded-md border border-slate-300 bg-white px-2.5 text-sm text-slate-700 focus:border-slate-500 focus:outline-none'

function hasActiveFilters(filters: QueueFiltersState): boolean {
  return filters.status !== '' || filters.source !== '' || filters.urgency !== '' || filters.q !== ''
}

export function QueueFilters({
  filters,
  onChange,
}: {
  filters: QueueFiltersState
  onChange: (next: QueueFiltersState) => void
}) {
  function clear() {
    onChange({ status: '', source: '', urgency: '', q: '', sort: filters.sort })
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="relative min-w-56 flex-1">
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
          className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
        >
          <path
            fillRule="evenodd"
            d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z"
            clipRule="evenodd"
          />
        </svg>
        <input
          type="search"
          placeholder="Search patient name…"
          value={filters.q}
          onChange={(e) => onChange({ ...filters, q: e.target.value })}
          className={`${controlClass} w-full pl-8`}
        />
      </div>

      <span aria-hidden="true" className="h-6 w-px bg-slate-200" />

      <select
        value={filters.status}
        onChange={(e) => onChange({ ...filters, status: e.target.value as ReferralStatus | '' })}
        className={controlClass}
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
        className={controlClass}
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
        className={controlClass}
      >
        <option value="">All urgencies</option>
        {URGENCY_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <div className="ml-auto flex items-center gap-2">
        {hasActiveFilters(filters) && (
          <Button variant="ghost" onClick={clear}>
            Clear filters
          </Button>
        )}
        <select
          value={filters.sort}
          onChange={(e) => onChange({ ...filters, sort: e.target.value as QueueFiltersState['sort'] })}
          className={controlClass}
        >
          <option value="-received_at">Newest first</option>
          <option value="received_at">Oldest first</option>
        </select>
      </div>
    </div>
  )
}
