import type { PaginationMeta } from '../api/types'
import { Button } from './Button'

export function Pagination({
  meta,
  onPageChange,
}: {
  meta: PaginationMeta
  onPageChange: (page: number) => void
}) {
  const start = (meta.page - 1) * meta.page_size + 1
  const end = Math.min(meta.page * meta.page_size, meta.total)

  return (
    <div className="flex items-center justify-between gap-4 text-sm text-slate-600">
      <p className="tabular-nums">
        {meta.total === 0 ? 'No results' : `Showing ${start}–${end} of ${meta.total}`}
      </p>
      <div className="flex items-center gap-3">
        <Button
          variant="neutral"
          disabled={meta.page <= 1}
          onClick={() => onPageChange(meta.page - 1)}
        >
          Previous
        </Button>
        <span className="tabular-nums">
          Page {meta.page} of {Math.max(meta.total_pages, 1)}
        </span>
        <Button
          variant="neutral"
          disabled={meta.page >= meta.total_pages}
          onClick={() => onPageChange(meta.page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
