import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError, updateReferralStatus } from '../api/client'
import type { Referral, ReferralDetailResponse, ReferralStatus } from '../api/types'
import { STATUS_LABELS, nextStatuses } from '../lib/statusWorkflow'
import { Button, type ButtonVariant } from './Button'

// Echoes the color language of StatusBadge: accepting/scheduling reads as
// progress, rejecting reads as a stop, review is neutral.
const ACTION_VARIANT: Record<ReferralStatus, ButtonVariant> = {
  new: 'neutral',
  in_review: 'neutral',
  accepted: 'positive',
  rejected: 'negative',
  scheduled: 'positive',
}

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
          <Button
            key={status}
            variant={ACTION_VARIANT[status]}
            disabled={mutation.isPending}
            onClick={() => mutation.mutate(status)}
          >
            Move to {STATUS_LABELS[status]}
          </Button>
        ))}
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </div>
  )
}
