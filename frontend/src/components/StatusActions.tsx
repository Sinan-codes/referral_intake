import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError, updateReferralStatus } from '../api/client'
import type { Referral, ReferralDetailResponse, ReferralStatus } from '../api/types'
import { STATUS_LABELS, nextStatuses } from '../lib/statusWorkflow'

/**
 * Renders one button per status the server's workflow allows from the
 * referral's current status. A rejected transition (e.g. a stale client
 * offering a move that's since become invalid) surfaces the server's
 * `ApiError` message inline rather than failing silently or throwing.
 */
export function StatusActions({ referral }: { referral: Referral }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const options = nextStatuses(referral.status)

  const mutation = useMutation({
    mutationFn: (status: ReferralStatus) => updateReferralStatus(referral.id, status),
    onMutate: () => setError(null),
    onSuccess: (response) => {
      queryClient.setQueryData<ReferralDetailResponse>(['referral', referral.id], (prev) =>
        prev ? { data: { ...prev.data, ...response.data } } : prev,
      )
      void queryClient.invalidateQueries({ queryKey: ['referrals'] })
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : 'Something went wrong updating the status.')
    },
  })

  if (options.length === 0) {
    return <p className="text-sm text-slate-500">This referral's status is final.</p>
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {options.map((status) => (
          <button
            key={status}
            type="button"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate(status)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Move to {STATUS_LABELS[status]}
          </button>
        ))}
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </div>
  )
}
