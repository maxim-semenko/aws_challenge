import { describe, expect, it } from 'vitest'
import { MISSING, formatBirthdate, formatCountry, formatMeasure, formatText, roleLine, selectRoleLine } from './format'

describe('personal page display rules (spec 04 §Outputs, §Edge Cases)', () => {
  it('shows the birth date as DD/MM/YYYY, "—" when missing or unparseable', () => {
    expect(formatBirthdate('1985-07-05')).toBe('05/07/1985')
    expect(formatBirthdate(undefined)).toBe(MISSING)
    expect(formatBirthdate('05.07.1985')).toBe(MISSING)
  })

  it('shows the country as name + code; other stored values as they are', () => {
    expect(formatCountry('DE')).toBe('Germany (DE)')
    expect(formatCountry('Germany')).toBe('Germany')
    expect(formatCountry('')).toBe(MISSING)
  })

  it('shows out-of-range numbers as stored, missing ones as "—"', () => {
    expect(formatMeasure('999', 'cm')).toBe('999 cm')
    expect(formatMeasure(undefined, 'kg')).toBe(MISSING)
    expect(formatText('  ')).toBe(MISSING)
  })

  it('role line from groups', () => {
    expect(roleLine(['admin'])).toBe('Role: administrator')
    expect(roleLine([])).toBe('Role: user')
    expect(roleLine(undefined)).toBe('Role: unavailable')
  })

  it('role line from the /api/me query state (spec 09 §Outputs)', () => {
    expect(selectRoleLine('success', ['admin'])).toBe('Role: administrator')
    expect(selectRoleLine('success', ['user', 'admin'])).toBe('Role: administrator')
    expect(selectRoleLine('success', [])).toBe('Role: user')
    expect(selectRoleLine('pending', undefined)).toBeNull()
    expect(selectRoleLine('error', undefined, 500)).toBe('Role: unavailable')
    expect(selectRoleLine('error', undefined, 502)).toBe('Role: unavailable')
    expect(selectRoleLine('error', undefined)).toBe('Role: unavailable') // network error: no status
    expect(selectRoleLine('error', undefined, 401)).toBeNull() // signing out
  })
})
