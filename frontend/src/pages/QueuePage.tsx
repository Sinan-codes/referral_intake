import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { listReferrals } from '../api/client'
import { Button } from '../components/Button'
import { DuplicateIcon } from '../components/badges'
import { Card } from '../components/Card'
import { Pagination } from '../components/Pagination'
import { QueueFilters } from '../components/QueueFilters'
import { QueueTable } from '../components/QueueTable'
import { EmptyState, ErrorState } from '../components/states'
import { hasActiveFilters, type QueueFiltersState } from '../lib/queueFilters'
import { useDebouncedValue } from '../lib/useDebouncedValue'
import { useDocumentTitle } from '../lib/useDocumentTitle'

const PAGE_SIZE = 20

const DEFAULT_FILTERS: QueueFiltersState = {
  status: '',
  source: '',
  urgency: '',
  q: '',
  sort: '-received_at',
}

export function QueuePage() {
  useDocumentTitle('Queue · Referral Intake')
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

  function clearFilters() {
    updateFilters({ status: '', source: '', urgency: '', q: '', sort: filters.sort })
  }

  const showEmpty = data && data.data.length === 0
  const showTable = isPending || (data && data.data.length > 0)

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Queue</p>
        <h1 className="text-xl font-semibold text-slate-900">Referrals</h1>
      </div>

      <QueueFilters filters={filters} onChange={updateFilters} />

      {data && (
        <div
          className={`flex flex-wrap items-center justify-between gap-3 ${isPlaceholderData ? 'opacity-60' : ''}`}
        >
          <p className="text-sm text-slate-500">
            <span className="font-medium text-slate-900">{data.meta.total}</span>{' '}
            {data.meta.total === 1 ? 'referral' : 'referrals'} found
          </p>

          <div className="flex items-center gap-4">
            {data.meta.duplicate_count > 0 && (
              <p className="inline-flex items-center gap-1.5 text-sm text-orange-700">
                <DuplicateIcon className="h-3.5 w-3.5" />
                <span className="font-medium">{data.meta.duplicate_count}</span>
                possible {data.meta.duplicate_count === 1 ? 'duplicate' : 'duplicates'}
              </p>
            )}
            <Button variant="ghost" disabled={!hasActiveFilters(filters)} onClick={clearFilters}>
              Clear filters
            </Button>
          </div>
        </div>
      )}

      {error && <ErrorState error={error} onRetry={() => refetch()} />}
      {showEmpty && <EmptyState title="No referrals match" description="Try widening your filters." />}

      {showTable && (
        <Card className={`transition-opacity ${isPlaceholderData ? 'opacity-60' : ''}`}>
          <div className="overflow-x-auto">
            <QueueTable referrals={data?.data ?? []} isLoading={isPending} />
          </div>
          {data && (
            <div className="border-t border-slate-200 px-4 py-3">
              <Pagination meta={data.meta} onPageChange={setPage} />
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
