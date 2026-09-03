import { Link } from 'react-router-dom'
import type { Referral } from '../api/types'
import { formatDateTime } from '../lib/format'
import { DuplicateIcon, SourceBadge, StatusBadge, UrgencyBadge } from './badges'

const SKELETON_ROWS = 8

/**
 * One <table> stays mounted for both the loading skeleton and the real
 * rows, sharing a single <colgroup>. Two separate tables (skeleton vs.
 * loaded) would each auto-size their own columns from their own content and
 * visibly jump widths on swap -- keeping one table avoids that entirely.
 */
export function QueueTable({
  referrals,
  isLoading,
}: {
  referrals: Referral[]
  isLoading: boolean
}) {
  return (
    <table className="w-full min-w-[720px] table-fixed text-left text-sm">
      <colgroup>
        <col className="w-[38%]" />
        <col className="w-[16%]" />
        <col className="w-[12%]" />
        <col className="w-[14%]" />
        <col className="w-[20%]" />
      </colgroup>
      <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
        <tr>
          <th className="px-4 py-3">Patient</th>
          <th className="px-4 py-3 text-center">Source</th>
          <th className="px-4 py-3 text-center">Urgency</th>
          <th className="px-4 py-3 text-center">Status</th>
          <th className="px-4 py-3">Received</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {isLoading
          ? Array.from({ length: SKELETON_ROWS }).map((_, row) => <SkeletonRow key={row} />)
          : referrals.map((referral) => <ReferralRow key={referral.id} referral={referral} />)}
      </tbody>
    </table>
  )
}

function ReferralRow({ referral }: { referral: Referral }) {
  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-3">
        <Link
          to={`/referrals/${referral.id}`}
          className="inline-flex items-center gap-1.5 font-medium text-slate-900 hover:underline"
        >
          {referral.patient_name.raw_full_name}
          {referral.possible_duplicate && (
            <span title="Possible duplicate — see duplicate group on the detail page">
              <DuplicateIcon className="h-3.5 w-3.5 shrink-0 text-orange-500" />
            </span>
          )}
        </Link>
      </td>
      <td className="px-4 py-3 text-center">
        <SourceBadge source={referral.source} />
      </td>
      <td className="px-4 py-3 text-center">
        <UrgencyBadge urgency={referral.urgency} />
      </td>
      <td className="px-4 py-3 text-center">
        <StatusBadge status={referral.status} />
      </td>
      <td className="px-4 py-3 tabular-nums text-slate-500">{formatDateTime(referral.received_at)}</td>
    </tr>
  )
}

function SkeletonRow() {
  return (
    <tr>
      <td className="px-4 py-3">
        <div className="h-4 w-36 animate-pulse rounded bg-slate-200" />
      </td>
      <td className="px-4 py-3">
        <div className="mx-auto h-5 w-16 animate-pulse rounded-full bg-slate-200" />
      </td>
      <td className="px-4 py-3">
        <div className="mx-auto h-5 w-16 animate-pulse rounded-full bg-slate-200" />
      </td>
      <td className="px-4 py-3">
        <div className="mx-auto h-5 w-16 animate-pulse rounded-full bg-slate-200" />
      </td>
      <td className="px-4 py-3">
        <div className="h-4 w-28 animate-pulse rounded bg-slate-200" />
      </td>
    </tr>
  )
}
