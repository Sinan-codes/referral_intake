import type { ReferralSource, ReferralStatus, Urgency } from '../api/types'
import { STATUS_LABELS } from '../lib/statusWorkflow'

const badgeBase =
  'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset'

const URGENCY_STYLES: Record<Urgency, string> = {
  routine: 'bg-slate-100 text-slate-700 ring-slate-300',
  urgent: 'bg-amber-100 text-amber-800 ring-amber-300',
  stat: 'bg-red-100 text-red-700 ring-red-300',
}

const URGENCY_LABELS: Record<Urgency, string> = {
  routine: 'Routine',
  urgent: 'Urgent',
  stat: 'STAT',
}

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  return <span className={`${badgeBase} ${URGENCY_STYLES[urgency]}`}>{URGENCY_LABELS[urgency]}</span>
}

const STATUS_STYLES: Record<ReferralStatus, string> = {
  new: 'bg-sky-100 text-sky-700 ring-sky-300',
  in_review: 'bg-violet-100 text-violet-700 ring-violet-300',
  accepted: 'bg-emerald-100 text-emerald-700 ring-emerald-300',
  rejected: 'bg-slate-200 text-slate-600 ring-slate-300',
  scheduled: 'bg-teal-100 text-teal-700 ring-teal-300',
}

export function StatusBadge({ status }: { status: ReferralStatus }) {
  return <span className={`${badgeBase} ${STATUS_STYLES[status]}`}>{STATUS_LABELS[status]}</span>
}

const SOURCE_LABELS: Record<ReferralSource, string> = {
  efax: 'eFax',
  ehr_fhir: 'EHR (FHIR)',
  web_form: 'Web form',
}

export function SourceBadge({ source }: { source: ReferralSource }) {
  return (
    <span className={`${badgeBase} bg-white text-slate-600 ring-slate-300`}>
      {SOURCE_LABELS[source]}
    </span>
  )
}

export function DuplicateBadge() {
  return (
    <span className={`${badgeBase} bg-orange-100 text-orange-800 ring-orange-300`}>
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-3 w-3">
        <path
          fillRule="evenodd"
          d="M9.257 3.099c.765-1.36 2.72-1.36 3.485 0l6.28 11.166c.75 1.334-.213 2.985-1.742 2.985H4.72c-1.53 0-2.492-1.65-1.743-2.985L9.257 3.1ZM10 7.5a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 10 7.5Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
          clipRule="evenodd"
        />
      </svg>
      Possible duplicate
    </span>
  )
}
