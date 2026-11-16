import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useSession, useSignOut } from '../auth/session'
import { isApiConfigured } from '../config/amplify'
import { adminUsersQueryKey, endpoints, isApiError, meQueryKey, retryApi } from './client'

/**
 * GET /api/me once per session (spec 09 Behaviour 1): enabled only with VITE_API_URL and a session; the cache is
 * dropped on sign-out (useSignOut), so the next session reads it again.
 */
export function useMe() {
  const session = useSession()
  return useQuery({
    queryKey: meQueryKey,
    queryFn: endpoints.me,
    enabled: isApiConfigured && Boolean(session.data),
    staleTime: Infinity,
    retry: retryApi,
  })
}

/** GET /api/admin/users for one page; the previous page stays visible while the next one loads (Behaviour 2). */
export function useAdminUsers(page: number) {
  return useQuery({
    queryKey: adminUsersQueryKey(page),
    queryFn: () => endpoints.adminUsers(page),
    enabled: isApiConfigured,
    placeholderData: keepPreviousData,
    retry: retryApi,
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
