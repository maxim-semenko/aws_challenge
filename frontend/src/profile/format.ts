import { countryName, isCountryCode } from '../auth/countries'

/**
 * Display rules of the personal page (spec 04 §Outputs, §Edge Cases): missing or unparseable values show "—";
 * values stored outside the SPA ranges (Q-14 C) are shown as they are.
 */

export const MISSING = '—'

const ISO_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/

export function formatText(value: string | undefined): string {
  const trimmed = value?.trim()
  return trimmed ? trimmed : MISSING
}

/** Cognito `birthdate` YYYY-MM-DD → DD/MM/YYYY. */
export function formatBirthdate(value: string | undefined): string {
  const match = value ? ISO_DATE_PATTERN.exec(value.trim()) : null
  if (!match) return MISSING
  const [, yyyy, mm, dd] = match
  return `${dd}/${mm}/${yyyy}`
}

/** `custom:country` → "Name (CODE)" for a known ISO alpha-2 code, otherwise the stored value as is. */
export function formatCountry(value: string | undefined): string {
  const trimmed = value?.trim()
  if (!trimmed) return MISSING
  return isCountryCode(trimmed) ? `${countryName(trimmed)} (${trimmed})` : trimmed
}

export function formatMeasure(value: string | undefined, unit: string): string {
  const trimmed = value?.trim()
  return trimmed ? `${trimmed} ${unit}` : MISSING
}

export type RoleLine = 'Role: administrator' | 'Role: user' | 'Role: unavailable'

/** Role line from `groups` of GET /api/me; undefined = API not configured or failed. */
export function roleLine(groups: readonly string[] | undefined): RoleLine {
  if (!groups) return 'Role: unavailable'
  return groups.includes('admin') ? 'Role: administrator' : 'Role: user'
}

/**
 * Role line for the state of the /api/me query (spec 09 §Outputs): nothing while loading or while a 401 signs the user
 * out; "Role: unavailable" on any other error (5xx, network). Not rendered at all without VITE_API_URL (caller).
 */
export function selectRoleLine(
  status: 'pending' | 'error' | 'success',
  groups: readonly string[] | undefined,
  errorStatus?: number,
): RoleLine | null {
  if (status === 'pending') return null
  if (status === 'error') return errorStatus === 401 ? null : 'Role: unavailable'
  return roleLine(groups)
}
