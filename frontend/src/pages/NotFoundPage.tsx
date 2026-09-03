import { Link } from 'react-router-dom'
import { useDocumentTitle } from '../lib/useDocumentTitle'

export function NotFoundPage() {
  useDocumentTitle('Not found · Referral Intake')
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center">
      <p className="text-sm font-medium text-slate-700">Page not found</p>
      <Link to="/" className="text-sm text-slate-500 hover:text-slate-700 hover:underline">
        ← Back to queue
      </Link>
    </div>
  )
}
