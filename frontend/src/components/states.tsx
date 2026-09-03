import { ApiError } from '../api/client'
import { Button } from './Button'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white py-16 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
      {label}
    </div>
  )
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {description && <p className="text-sm text-slate-500">{description}</p>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof ApiError ? error.message : 'Something went wrong.'
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-red-200 bg-red-50 py-16 text-center">
      <p className="text-sm font-medium text-red-800">Couldn't load this.</p>
      <p className="max-w-sm text-sm text-red-700">{message}</p>
      {onRetry && (
        <Button variant="negative" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
