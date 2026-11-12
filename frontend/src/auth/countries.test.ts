import { describe, expect, it } from 'vitest'
import { COUNTRY_CODES, countryName, countryOptions, isCountryCode } from './countries'

describe('countries', () => {
  it('lists the 249 ISO 3166-1 alpha-2 codes, upper case, unique', () => {
    expect(COUNTRY_CODES).toHaveLength(249)
    expect(new Set(COUNTRY_CODES).size).toBe(249)
    expect(COUNTRY_CODES.every((code) => /^[A-Z]{2}$/.test(code))).toBe(true)
  })

  it('names come from Intl.DisplayNames', () => {
    expect(countryName('DE')).toBe('Germany')
    expect(countryOptions().find((option) => option.code === 'BY')?.name).toBe('Belarus')
  })

  it('rejects codes outside the list', () => {
    expect(isCountryCode('EU')).toBe(false)
    expect(isCountryCode('de')).toBe(false)
  })
})
