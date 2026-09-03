export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

/**
 * Formats a plain `YYYY-MM-DD` date (no time, no zone -- `date_of_birth`).
 * Parsed manually rather than via `new Date(iso)`: that parses as UTC
 * midnight, which `toLocaleDateString` can then roll back a day in any
 * timezone behind UTC.
 */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString(undefined, { dateStyle: 'medium' })
}
