import type { ReactNode } from 'react'
import type { ReferralSource, ReferralStatus, Urgency } from '../api/types'
import type { QueueFiltersState } from '../lib/queueFilters'
import { STATUS_LABELS } from '../lib/statusWorkflow'

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

/** A labeled field group -- every filter gets a visible name above its
 * control instead of relying on placeholder/default-option text alone,
 * which also gives each control a real accessible name via `htmlFor`. */
function FilterField({
  label,
  htmlFor,
  className = '',
  children,
}: {
  label: string
  htmlFor: string
  className?: string
  children: ReactNode
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={htmlFor} className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </label>
      {children}
    </div>
  )
}

export function QueueFilters({
  filters,
  onChange,
}: {
  filters: QueueFiltersState
  onChange: (next: QueueFiltersState) => void
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-end gap-4">
        <FilterField label="Search" htmlFor="filter-search" className="min-w-56 flex-1">
          <div className="relative">
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
              id="filter-search"
              type="search"
              placeholder="Patient name…"
              value={filters.q}
              onChange={(e) => onChange({ ...filters, q: e.target.value })}
              className={`${controlClass} w-full pl-8`}
            />
          </div>
        </FilterField>

        <FilterField label="Status" htmlFor="filter-status">
          <select
            id="filter-status"
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
        </FilterField>

        <FilterField label="Source" htmlFor="filter-source">
          <select
            id="filter-source"
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
        </FilterField>

        <FilterField label="Urgency" htmlFor="filter-urgency">
          <select
            id="filter-urgency"
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
        </FilterField>

        <FilterField label="Sort by" htmlFor="filter-sort" className="ml-auto">
          <select
            id="filter-sort"
            value={filters.sort}
            onChange={(e) => onChange({ ...filters, sort: e.target.value as QueueFiltersState['sort'] })}
            className={controlClass}
          >
            <option value="-received_at">Newest first</option>
            <option value="received_at">Oldest first</option>
          </select>
        </FilterField>
      </div>
    </div>
  )
}
