import type { Page, User } from '../api/client'
import { MISSING, formatBirthdate, formatCountry, formatText } from '../profile/format'

/** States of the /admin page (spec 09 §Outputs). `signing-out` = 401, the user is being sent to /sign-in. */
export type AdminViewState = 'unconfigured' | 'loading' | 'signing-out' | 'forbidden' | 'error' | 'empty' | 'data'

export interface AdminQueryState {
  status: 'pending' | 'error' | 'success'
  /** HTTP status of an ApiError; undefined for a network error */
  errorStatus?: number
  data?: Page<User>
}

/** Errors win over (placeholder) data, so a failed page is never shown as current. */
export function selectAdminView(apiConfigured: boolean, query: AdminQueryState): AdminViewState {
  if (!apiConfigured) return 'unconfigured'
  if (query.status === 'error') {
    if (query.errorStatus === 401) return 'signing-out'
    if (query.errorStatus === 403) return 'forbidden'
    return 'error'
  }
  if (query.status === 'pending' || !query.data) return 'loading'
  return query.data.total === 0 ? 'empty' : 'data'
}

export interface Paging {
  text: string
  hasPrevious: boolean
  hasNext: boolean
}

/** "Page <page+1> of <max(1, ceil(total/size))> · <total> users"; a page beyond the end keeps Previous enabled. */
export function paging(page: number, total: number, size: number): Paging {
  const pageCount = Math.max(1, Math.ceil(total / size))
  return {
    text: `Page ${page + 1} of ${pageCount} · ${total} users`,
    hasPrevious: page > 0,
    hasNext: page + 1 < pageCount,
  }
}

export const USER_COLUMNS = [
  'Email',
  'First name',
  'Last name',
  'Gender',
  'Date of birth',
  'Country',
  'Height (cm)',
  'Weight (kg)',
  'Registered',
] as const

const ISO_DATE_PREFIX = /^(\d{4}-\d{2}-\d{2})T/

/** ISO-8601 UTC timestamp → DD/MM/YYYY of its UTC date; anything else as stored, missing → "—". */
export function formatTimestampDate(value: string | null): string {
  if (!value?.trim()) return MISSING
  const match = ISO_DATE_PREFIX.exec(value.trim())
  return match ? formatBirthdate(match[1]) : value
}

function formatNumber(value: number | null): string {
  return value === null || value === undefined ? MISSING : String(value)
}

/** Birthdate `YYYY-MM-DD` → DD/MM/YYYY; other stored values as they are (spec 09: shown as stored). */
function formatStoredDate(value: string | null): string {
  if (!value?.trim()) return MISSING
  const formatted = formatBirthdate(value)
  return formatted === MISSING ? value : formatted
}

/** Cell texts of one user row, in the order of USER_COLUMNS. */
export function userCells(user: User): string[] {
  return [
    formatText(user.email ?? undefined),
    formatText(user.givenName ?? undefined),
    formatText(user.familyName ?? undefined),
    formatText(user.gender ?? undefined),
    formatStoredDate(user.birthdate),
    formatCountry(user.country ?? undefined),
    formatNumber(user.heightCm),
    formatNumber(user.weightKg),
    formatTimestampDate(user.createdAt),
  ]
}
