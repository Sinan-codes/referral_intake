import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { listReferrals } from '../api/client'
import { DuplicateBadge, SourceBadge, StatusBadge, UrgencyBadge } from '../components/badges'
import { Pagination } from '../components/Pagination'
import { QueueFilters, type QueueFiltersState } from '../components/QueueFilters'
import { EmptyState, ErrorState, LoadingState } from '../components/states'
import { formatDateTime } from '../lib/format'
import { useDebouncedValue } from '../lib/useDebouncedValue'

const PAGE_SIZE = 20

const DEFAULT_FILTERS: QueueFiltersState = {
  status: '',
  source: '',
  urgency: '',
  q: '',
  sort: '-received_at',
}

export function QueuePage() {
  const [filters, setFilters] = useState<QueueFiltersState>(DEFAULT_FILTERS)
  const [page, setPage] = useState(1)
  const debouncedQuery = useDebouncedValue(filters.q, 300)

  const params = {
    status: filters.status || undefined,
    source: filters.source || undefined,
    urgency: filters.urgency || undefined,
    q: debouncedQuery || undefined,
    sort: filters.sort,
    page,
    page_size: PAGE_SIZE,
  }

  const { data, error, isPending, isPlaceholderData, refetch } = useQuery({
    queryKey: ['referrals', params] as const,
    queryFn: () => listReferrals(params),
    placeholderData: (previous) => previous,
  })

  function updateFilters(next: QueueFiltersState) {
    setFilters(next)
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Queue</h1>

      <QueueFilters filters={filters} onChange={updateFilters} />

      {isPending && <LoadingState label="Loading referrals…" />}
      {error && <ErrorState error={error} onRetry={() => refetch()} />}

      {data && data.data.length === 0 && (
        <EmptyState title="No referrals match" description="Try widening your filters." />
      )}

      {data && data.data.length > 0 && (
        <div
          className={`flex flex-col gap-3 transition-opacity ${isPlaceholderData ? 'opacity-60' : ''}`}
        >
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Patient</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                  <th className="px-4 py-3 font-medium">Urgency</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Received</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.data.map((referral) => (
                  <tr key={referral.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link
                        to={`/referrals/${referral.id}`}
                        className="font-medium text-slate-900 hover:underline"
                      >
                        {referral.patient_name.raw_full_name}
                      </Link>
                      {referral.possible_duplicate && (
                        <div className="mt-1">
                          <DuplicateBadge />
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <SourceBadge source={referral.source} />
                    </td>
                    <td className="px-4 py-3">
                      <UrgencyBadge urgency={referral.urgency} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={referral.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-500">{formatDateTime(referral.received_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination meta={data.meta} onPageChange={setPage} />
        </div>
      )}
    </div>
  )
}
