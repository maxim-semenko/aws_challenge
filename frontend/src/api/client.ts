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

/** One row of GET /admin (owner decision 2026-11-17: the API has only GET /admin and, from Week 5, POST /chat). */
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
  return `/admin?page=${page}&size=${ADMIN_USERS_PAGE_SIZE}`
}

export const adminUsersQueryKey = (page: number) => ['admin', 'users', page] as const

// ---- POST /chat (field names: spec 12 §Inputs / §Outputs) ----

/** The only field the SPA sends (spec 12 §Inputs); `query` is the trimmed text, 1…500 characters. */
export interface ChatRequest {
  query: string
}

export type ChatCell = string | number | boolean | null

export interface ChatResponse {
  mode: 'sql' | 'vector'
  columns: string[]
  rows: ChatCell[][]
  rowCount: number
  truncated: boolean
  sql: string | null
  timings: { embedMs: number | null; llmMs: number | null; dbMs: number; totalMs: number }
  tokens: { input: number; output: number }
  modelId: string
}

export const chatQueryKey = (query: string) => ['chat', query] as const

function chat(query: string): Promise<ChatResponse> {
  const body: ChatRequest = { query }
  return api<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify(body) })
}

/** Endpoints used by the SPA. */
export const endpoints = {
  adminUsers: (page: number) => api<Page<User>>(adminUsersPath(page)),
  chat,
}
