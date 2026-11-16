import { describe, expect, it } from 'vitest'
import { ApiError, adminUsersPath, adminUsersQueryKey, isApiError, meQueryKey, retryApi } from './client'

describe('API client (spec 08, spec 09 Behaviour 1-3)', () => {
  it('requests a page of 20 with the default sort', () => {
    expect(adminUsersPath(0)).toBe('/api/admin/users?page=0&size=20')
    expect(adminUsersPath(3)).toBe('/api/admin/users?page=3&size=20')
  })

  it('uses the query keys of the spec', () => {
    expect(meQueryKey).toEqual(['me'])
    expect(adminUsersQueryKey(2)).toEqual(['admin', 'users', 2])
  })

  it('never retries 401, 403 or other 4xx', () => {
    for (const status of [400, 401, 403, 404, 429]) {
      expect(retryApi(0, new ApiError(status, String(status)))).toBe(false)
    }
  })

  it('retries 5xx and network errors once', () => {
    expect(retryApi(0, new ApiError(500, '500'))).toBe(true)
    expect(retryApi(1, new ApiError(502, '502'))).toBe(false)
    expect(retryApi(0, new TypeError('Failed to fetch'))).toBe(true)
    expect(retryApi(1, new TypeError('Failed to fetch'))).toBe(false)
  })

  it('recognises an API error by status', () => {
    expect(isApiError(new ApiError(401, '401'), 401)).toBe(true)
    expect(isApiError(new ApiError(403, '403'), 401)).toBe(false)
    expect(isApiError(new Error('x'), 401)).toBe(false)
  })
})
