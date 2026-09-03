import type { PaginationMeta } from '../api/types'

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
    <div className="flex items-center justify-between text-sm text-slate-600">
      <p>
        {meta.total === 0
          ? 'No results'
          : `Showing ${start}–${end} of ${meta.total}`}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={meta.page <= 1}
          onClick={() => onPageChange(meta.page - 1)}
          className="rounded-md border border-slate-300 px-2.5 py-1 disabled:cursor-not-allowed disabled:opacity-40 hover:bg-slate-50"
        >
          Previous
        </button>
        <span className="tabular-nums">
          Page {meta.page} of {Math.max(meta.total_pages, 1)}
        </span>
        <button
          type="button"
          disabled={meta.page >= meta.total_pages}
          onClick={() => onPageChange(meta.page + 1)}
          className="rounded-md border border-slate-300 px-2.5 py-1 disabled:cursor-not-allowed disabled:opacity-40 hover:bg-slate-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}
