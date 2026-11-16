import { fetchAuthSession } from 'aws-amplify/auth'
import { env, isAuthConfigured } from '../config/amplify'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function isApiError(error: unknown, status: number): boolean {
  return error instanceof ApiError && error.status === status
}

/**
 * TanStack Query retry rule (spa-api-client skill): 4xx (401, 403, 400, 404) is never retried; 5xx and network
 * errors are retried once.
 */
export function retryApi(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) return false
  return failureCount < 1
}

/**
 * fetch() wrapper: adds "Authorization: Bearer <Cognito access token>" for the API Gateway JWT authorizer (ADR-004).
 * Amplify refreshes expired tokens automatically inside fetchAuthSession().
 */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (isAuthConfigured) {
    const { tokens } = await fetchAuthSession()
    const accessToken = tokens?.accessToken?.toString()
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`)
    }
  }

  const response = await fetch(`${env.apiUrl}${path}`, { ...init, headers })
  if (!response.ok) {
    throw new ApiError(response.status, `${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

// ---- API types (field names: spec 08 §Outputs) ----

/** GET /api/me → 200. */
export interface MeResponse {
  id: string
  username: string | null
  groups: string[]
  /** ISO-8601 UTC */
  expiresAt: string
}

/** One row of GET /api/admin/users. */
export interface User {
  id: string
  email: string
  givenName: string | null
  familyName: string | null
  gender: string | null
  country: string | null
  /** YYYY-MM-DD */
  birthdate: string | null
  heightCm: number | null
  weightKg: number | null
  /** ISO-8601 UTC */
  createdAt: string
  /** ISO-8601 UTC */
  updatedAt: string
}

/** Paginated response (CLAUDE.md §6). */
export interface Page<T> {
  items: T[]
  page: number
  size: number
  total: number
}

/** Page size of the admin table (spec 09); the default sort `createdAt,desc` is left to the API. */
export const ADMIN_USERS_PAGE_SIZE = 20

export function adminUsersPath(page: number): string {
  return `/api/admin/users?page=${page}&size=${ADMIN_USERS_PAGE_SIZE}`
}

export const meQueryKey = ['me'] as const
export const adminUsersQueryKey = (page: number) => ['admin', 'users', page] as const

/** Endpoints used by the SPA (spec 08); later endpoints are added with their specs. */
export const endpoints = {
  me: () => api<MeResponse>('/api/me'),
  adminUsers: (page: number) => api<Page<User>>(adminUsersPath(page)),
}
