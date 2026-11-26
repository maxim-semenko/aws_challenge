import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useSignOut } from '../auth/session'
import { isApiConfigured } from '../config/amplify'
import { adminUsersQueryKey, chatQueryKey, endpoints, isApiError, retryApi } from './client'

/** GET /admin for one page; the previous page stays visible while the next one loads (Behaviour 2). */
export function useAdminUsers(page: number) {
  return useQuery({
    queryKey: adminUsersQueryKey(page),
    queryFn: () => endpoints.adminUsers(page),
    enabled: isApiConfigured,
    placeholderData: keepPreviousData,
    retry: retryApi,
  })
}

/** Same text within 60 s is answered from the cache (spec 13 Behaviour 4). */
export const CHAT_CACHE_MS = 60_000

/**
 * POST /chat for the last sent text (null = nothing sent yet). No retry and no refetch on focus/reconnect — each call
 * may cost LLM tokens; the previous result stays visible while the next one loads (spec 13 Behaviour 4).
 */
export function useChat(query: string | null) {
  return useQuery({
    queryKey: chatQueryKey(query ?? ''),
    queryFn: () => endpoints.chat(query ?? ''),
    enabled: isApiConfigured && query !== null,
    placeholderData: keepPreviousData,
    staleTime: CHAT_CACHE_MS,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
}

/** 401 from the API → sign-out and /sign-in (spa-api-client skill, spec 09 Behaviour 3). */
export function useSignOutOnUnauthorized(error: unknown): void {
  const signOut = useSignOut()
  const unauthorized = isApiError(error, 401)
  useEffect(() => {
    if (unauthorized) void signOut()
  }, [unauthorized, signOut])
}
