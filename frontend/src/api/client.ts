import { fetchAuthSession } from 'aws-amplify/auth'
import { env, isAuthConfigured } from '../config/amplify'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
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

// ---- API types ----

/** GET /api/me → 200, exactly spec 05 §Outputs. */
export interface MeResponse {
  id: string
  username: string | null
  groups: string[]
  /** ISO-8601 UTC */
  expiresAt: string
}

export const meQueryKey = ['me'] as const

/** Week 2 endpoints used by the SPA (spec 05); later endpoints are added with their specs. */
export const endpoints = {
  me: () => api<MeResponse>('/api/me'),
}
