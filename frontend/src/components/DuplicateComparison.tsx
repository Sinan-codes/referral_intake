import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type {
  ReferralDetail,
  ReferralSource,
  ReferralStatus,
  ReferralSummary,
  Urgency,
} from '../api/types'
import { SourceBadge, StatusBadge, UrgencyBadge } from './badges'
import { formatDate, formatDateTime } from '../lib/format'

/** The subset of fields both the open referral and a `ReferralSummary`
 * peer can supply, normalized to one shape so a single table can render
 * either kind of row without a union type at every call site. */
interface ComparableReferral {
  id: string
  isCurrent: boolean
  source: ReferralSource
  patientName: string
  dateOfBirth: string | null
  urgency: Urgency
  status: ReferralStatus
  referringProvider: string | null
  reason: string | null
  receivedAt: string
}

interface Row {
  label: string
  render: (referral: ComparableReferral) => ReactNode
  /** The value diffed across columns to decide whether to highlight this
   * row -- not necessarily the same as what's rendered (badges render as
   * JSX, but compare on the plain enum value underneath). Omitted for rows
   * that are expected to differ regardless of whether this is a true
   * duplicate (source, workflow status, timestamp), so those don't light
   * up on every single comparison and drown out the fields that actually
   * carry signal. */
  value?: (referral: ComparableReferral) => string
}

const ROWS: Row[] = [
  {
    label: 'Patient name',
    render: (r) => r.patientName,
    value: (r) => r.patientName.trim().toLowerCase(),
  },
  {
    label: 'Date of birth',
    render: (r) => (r.dateOfBirth ? formatDate(r.dateOfBirth) : 'Unknown'),
    value: (r) => r.dateOfBirth ?? '',
  },
  {
    label: 'Referring provider',
    render: (r) => r.referringProvider ?? 'Unknown',
    value: (r) => (r.referringProvider ?? '').trim().toLowerCase(),
  },
  {
    label: 'Reason',
    render: (r) => r.reason ?? 'Not provided',
    value: (r) => (r.reason ?? '').trim().toLowerCase(),
  },
  {
    label: 'Urgency',
    render: (r) => <UrgencyBadge urgency={r.urgency} />,
    value: (r) => r.urgency,
  },
  {
    label: 'Source',
    render: (r) => <SourceBadge source={r.source} />,
  },
  {
    label: 'Status',
    render: (r) => <StatusBadge status={r.status} />,
  },
  {
    label: 'Received',
    render: (r) => formatDateTime(r.receivedAt),
  },
]

function fromDetail(referral: ReferralDetail): ComparableReferral {
  return {
    id: referral.id,
    isCurrent: true,
    source: referral.source,
    patientName: referral.patient_name.raw_full_name,
    dateOfBirth: referral.date_of_birth ?? null,
    urgency: referral.urgency,
    status: referral.status,
    referringProvider: referral.referring_provider ?? null,
    reason: referral.reason ?? null,
    receivedAt: referral.received_at,
  }
}

function fromSummary(peer: ReferralSummary): ComparableReferral {
  return {
    id: peer.id,
    isCurrent: false,
    source: peer.source,
    patientName: peer.patient_name,
    dateOfBirth: peer.date_of_birth ?? null,
    urgency: peer.urgency,
    status: peer.status,
    referringProvider: peer.referring_provider ?? null,
    reason: peer.reason ?? null,
    receivedAt: peer.received_at,
  }
}

/**
 * A field-by-field comparison table for a referral and its possible
 * duplicates, so a coordinator can judge a match without navigating away
 * and losing the record they started from. Rows where a field doesn't
 * agree across every column are highlighted -- that disagreement (a
 * different reason, a different provider) is exactly the signal that
 * decides whether a flagged pair is a real duplicate or a decoy.
 */
export function DuplicateComparison({ referral }: { referral: ReferralDetail }) {
  const peers = referral.duplicate_group ?? []
  if (peers.length === 0) {
    return <p className="text-sm text-orange-800">None found.</p>
  }

  const columns: ComparableReferral[] = [fromDetail(referral), ...peers.map(fromSummary)]

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr>
            <th className="w-36 border-b border-orange-200 pb-2 pr-4 text-xs font-medium uppercase tracking-wide text-orange-700">
              Field
            </th>
            {columns.map((column) => (
              <th key={column.id} className="border-b border-orange-200 px-4 pb-2 font-medium">
                {column.isCurrent ? (
                  <span className="text-orange-900">This referral</span>
                ) : (
                  <Link
                    to={`/referrals/${column.id}`}
                    className="inline-flex items-center gap-1 text-slate-700 hover:text-slate-900 hover:underline"
                  >
                    View record <span aria-hidden="true">→</span>
                  </Link>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => {
            const differs = row.value && new Set(columns.map(row.value)).size > 1
            return (
              <tr key={row.label} className={differs ? 'bg-amber-100/70' : undefined}>
                <td className="border-b border-orange-100 py-2 pr-4 text-xs font-medium uppercase tracking-wide text-orange-700">
                  {row.label}
                </td>
                {columns.map((column) => (
                  <td key={column.id} className="border-b border-orange-100 px-4 py-2 text-slate-900">
                    {row.render(column)}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
