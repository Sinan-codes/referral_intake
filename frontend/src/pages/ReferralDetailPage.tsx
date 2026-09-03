import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ApiError, getReferral } from '../api/client'
import { SourceBadge, StatusBadge, UrgencyBadge } from '../components/badges'
import { EmptyState, ErrorState, LoadingState } from '../components/states'
import { StatusActions } from '../components/StatusActions'
import { formatDate, formatDateTime } from '../lib/format'

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-900">{value}</dd>
    </div>
  )
}

export function ReferralDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['referral', id] as const,
    queryFn: () => getReferral(id!),
    enabled: Boolean(id),
    retry: (failureCount, err) => !(err instanceof ApiError && err.status === 404) && failureCount < 3,
  })

  return (
    <div className="flex flex-col gap-4">
      <Link to="/" className="text-sm text-slate-500 hover:text-slate-700 hover:underline">
        ← Back to queue
      </Link>

      {isPending && <LoadingState label="Loading referral…" />}

      {error &&
        (error instanceof ApiError && error.status === 404 ? (
          <EmptyState title="Referral not found" description="It may have been removed." />
        ) : (
          <ErrorState error={error} onRetry={() => refetch()} />
        ))}

      {data && (
        <div className="flex flex-col gap-6">
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="text-xl font-semibold text-slate-900">
                  {data.data.patient_name.raw_full_name}
                </h1>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <SourceBadge source={data.data.source} />
                  <UrgencyBadge urgency={data.data.urgency} />
                  <StatusBadge status={data.data.status} />
                </div>
              </div>
            </div>

            <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Field
                label="Date of birth"
                value={data.data.date_of_birth ? formatDate(data.data.date_of_birth) : 'Unknown'}
              />
              <Field label="Referring provider" value={data.data.referring_provider ?? 'Unknown'} />
              <Field label="Received" value={formatDateTime(data.data.received_at)} />
              <Field label="Reason" value={data.data.reason ?? 'Not provided'} />
              <Field label="Source record ID" value={data.data.source_record_id} />
            </dl>

            <div className="mt-6 border-t border-slate-100 pt-6">
              <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Update status
              </h2>
              <div className="mt-2">
                <StatusActions referral={data.data} />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-orange-200 bg-orange-50 p-6">
            <h2 className="text-sm font-semibold text-orange-900">Possible duplicates</h2>
            {data.data.duplicate_group.length === 0 ? (
              <p className="mt-1 text-sm text-orange-800">None found.</p>
            ) : (
              <ul className="mt-3 flex flex-col gap-2">
                {data.data.duplicate_group.map((peer) => (
                  <li key={peer.id}>
                    <Link
                      to={`/referrals/${peer.id}`}
                      className="flex flex-wrap items-center gap-2 rounded-md border border-orange-200 bg-white px-3 py-2 text-sm hover:border-orange-400"
                    >
                      <span className="font-medium text-slate-900">{peer.patient_name}</span>
                      <SourceBadge source={peer.source} />
                      <StatusBadge status={peer.status} />
                      <span className="text-slate-500">{formatDateTime(peer.received_at)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
