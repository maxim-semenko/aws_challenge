import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useSignOut } from '../auth/session'
import { isApiConfigured } from '../config/amplify'
import { adminUsersQueryKey, endpoints, isApiError, retryApi } from './client'

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

/** 401 from the API → sign-out and /sign-in (spa-api-client skill, spec 09 Behaviour 3). */
export function useSignOutOnUnauthorized(error: unknown): void {
  const signOut = useSignOut()
  const unauthorized = isApiError(error, 401)
  useEffect(() => {
    if (unauthorized) void signOut()
  }, [unauthorized, signOut])
}
