import { describe, expect, it } from 'vitest'
import type { Page, User } from '../api/client'
import { MISSING } from '../profile/format'
import { USER_COLUMNS, formatTimestampDate, paging, selectAdminView, userCells } from './view'

const user: User = {
  id: '0b6f2a8e-1111-4c1e-9d55-000000000001',
  email: 'ann@example.com',
  givenName: 'Ann',
  familyName: 'Lee',
  gender: 'female',
  country: 'DE',
  birthdate: '1990-02-03',
  heightCm: 170,
  weightKg: 60,
  createdAt: '2026-11-14T08:15:00Z',
  updatedAt: '2026-11-14T08:15:00Z',
}

const pageOf = (items: User[], total: number): Page<User> => ({ items, page: 0, size: 20, total })

describe('/admin state selection (spec 09 §Outputs)', () => {
  it('shows the placeholder without VITE_API_URL, whatever the query says', () => {
    expect(selectAdminView(false, { status: 'pending' })).toBe('unconfigured')
    expect(selectAdminView(false, { status: 'success', data: pageOf([user], 1) })).toBe('unconfigured')
  })

  it('loading, 403, 401, 5xx and network errors', () => {
    expect(selectAdminView(true, { status: 'pending' })).toBe('loading')
    expect(selectAdminView(true, { status: 'error', errorStatus: 403 })).toBe('forbidden')
    expect(selectAdminView(true, { status: 'error', errorStatus: 401 })).toBe('signing-out')
    expect(selectAdminView(true, { status: 'error', errorStatus: 500 })).toBe('error')
    expect(selectAdminView(true, { status: 'error', errorStatus: 502 })).toBe('error')
    expect(selectAdminView(true, { status: 'error' })).toBe('error')
  })

  it('an error is never shown with stale data as current', () => {
    expect(selectAdminView(true, { status: 'error', errorStatus: 500, data: pageOf([user], 1) })).toBe('error')
  })

  it('empty table and data', () => {
    expect(selectAdminView(true, { status: 'success', data: pageOf([], 0) })).toBe('empty')
    expect(selectAdminView(true, { status: 'success', data: pageOf([user], 1) })).toBe('data')
    // total shrank between pages: page beyond the end is an empty table, not "No users yet."
    expect(selectAdminView(true, { status: 'success', data: pageOf([], 5) })).toBe('data')
  })
})

describe('paging line (spec 09 §Outputs)', () => {
  it('total = 0: one page, both buttons disabled', () => {
    expect(paging(0, 0, 20)).toEqual({ text: 'Page 1 of 1 · 0 users', hasPrevious: false, hasNext: false })
  })

  it('first page of several', () => {
    expect(paging(0, 45, 20)).toEqual({ text: 'Page 1 of 3 · 45 users', hasPrevious: false, hasNext: true })
  })

  it('middle page', () => {
    expect(paging(1, 45, 20)).toEqual({ text: 'Page 2 of 3 · 45 users', hasPrevious: true, hasNext: true })
  })

  it('last page with fewer than 20 rows', () => {
    expect(paging(2, 45, 20)).toEqual({ text: 'Page 3 of 3 · 45 users', hasPrevious: true, hasNext: false })
  })

  it('exactly one full page; 21 users give two pages', () => {
    expect(paging(0, 20, 20)).toEqual({ text: 'Page 1 of 1 · 20 users', hasPrevious: false, hasNext: false })
    expect(paging(0, 21, 20)).toEqual({ text: 'Page 1 of 2 · 21 users', hasPrevious: false, hasNext: true })
  })

  it('page beyond the end keeps Previous enabled', () => {
    expect(paging(3, 21, 20)).toEqual({ text: 'Page 4 of 2 · 21 users', hasPrevious: true, hasNext: false })
  })
})

describe('user cells (spec 09 §Outputs)', () => {
  it('columns in the specified order', () => {
    expect(USER_COLUMNS).toEqual([
      'Email',
      'First name',
      'Last name',
      'Gender',
      'Date of birth',
      'Country',
      'Height (cm)',
      'Weight (kg)',
      'Registered',
    ])
  })

  it('formats dates as DD/MM/YYYY and the country as name + code', () => {
    expect(userCells(user)).toEqual([
      'ann@example.com',
      'Ann',
      'Lee',
      'female',
      '03/02/1990',
      'Germany (DE)',
      '170',
      '60',
      '14/11/2026',
    ])
  })

  it('null values show "—"', () => {
    const sparse: User = {
      ...user,
      givenName: null,
      familyName: null,
      gender: null,
      country: null,
      birthdate: null,
      heightCm: null,
      weightKg: null,
    }
    expect(userCells(sparse)).toEqual([
      'ann@example.com',
      MISSING,
      MISSING,
      MISSING,
      MISSING,
      MISSING,
      MISSING,
      MISSING,
      '14/11/2026',
    ])
  })

  it('odd values are shown as stored', () => {
    const odd: User = { ...user, country: 'Narnia', birthdate: '03.02.1990', heightCm: 999, weightKg: 0 }
    const cells = userCells(odd)
    expect(cells[4]).toBe('03.02.1990')
    expect(cells[5]).toBe('Narnia')
    expect(cells[6]).toBe('999')
    expect(cells[7]).toBe('0')
  })

  it('registration timestamp uses the UTC date', () => {
    expect(formatTimestampDate('2026-11-14T23:59:59Z')).toBe('14/11/2026')
    expect(formatTimestampDate('2026-11-14T23:59:59.123Z')).toBe('14/11/2026')
    expect(formatTimestampDate('yesterday')).toBe('yesterday')
    expect(formatTimestampDate(null)).toBe(MISSING)
  })
})
