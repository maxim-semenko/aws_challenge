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
 * fetch() wrapper: adds "Authorization: Bearer <Cognito ID token>" for the API Gateway JWT authorizer.
 * Amplify refreshes expired tokens automatically inside fetchAuthSession().
 */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (isAuthConfigured) {
    const { tokens } = await fetchAuthSession()
    const idToken = tokens?.idToken?.toString()
    if (idToken) {
      headers.set('Authorization', `Bearer ${idToken}`)
    }
  }

  const response = await fetch(`${env.apiUrl}${path}`, { ...init, headers })
  if (!response.ok) {
    throw new ApiError(response.status, `${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

// ---- API types (mirror the Spring DTOs) ----

export interface CurrentUser {
  sub: string
  email: string
  groups: string[]
}

export interface DocumentSearchResult {
  id: number
  title: string
  content: string
  distance: number
}

export interface UserDto {
  id: number
  email: string
  username: string | null
  createdAt: string
}

export interface PageResponse<T> {
  items: T[]
  page: number
  size: number
  total: number
}

export const endpoints = {
  health: () => api<{ status: string }>('/api/health'),
  me: () => api<CurrentUser>('/api/me'),
  search: (query: string, limit = 5) =>
    api<DocumentSearchResult[]>('/api/chat/search', {
      method: 'POST',
      body: JSON.stringify({ query, limit }),
    }),
  users: (page = 0, size = 20) => api<PageResponse<UserDto>>(`/api/admin/users?page=${page}&size=${size}`),
}
