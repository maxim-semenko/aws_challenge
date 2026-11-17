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

/**
 * Group names from the `cognito:groups` claim of the access token payload (owner decision 2026-11-17: no API call).
 * The claim is absent when the user is in no group → []; non-string entries are ignored.
 */
export function groupsFromClaims(payload: { readonly [claim: string]: unknown } | undefined): string[] {
  const claim = payload?.['cognito:groups']
  return Array.isArray(claim) ? claim.filter((group): group is string => typeof group === 'string') : []
}

/** Role line from the token groups; undefined = the session could not be read. */
export function roleLine(groups: readonly string[] | undefined): RoleLine {
  if (!groups) return 'Role: unavailable'
  return groups.includes('admin') ? 'Role: administrator' : 'Role: user'
}

/** Role line for the state of the groups query: nothing while loading, "Role: unavailable" only if the session failed. */
export function selectRoleLine(status: 'pending' | 'error' | 'success', groups: readonly string[] | undefined): RoleLine | null {
  if (status === 'pending') return null
  if (status === 'error') return 'Role: unavailable'
  return roleLine(groups)
}
