import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getCurrentUser, signOut } from 'aws-amplify/auth'
import { Hub } from 'aws-amplify/utils'
import { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router'
import { isAuthConfigured } from '../config/amplify'

export const sessionQueryKey = ['auth', 'session'] as const

export interface Session {
  userId: string
  loginId?: string
}

async function loadSession(): Promise<Session | null> {
  try {
    const user = await getCurrentUser()
    return { userId: user.userId, loginId: user.signInDetails?.loginId }
  } catch {
    // UserUnAuthenticatedException: nobody is signed in
    return null
  }
}

/** Current Amplify session (null = anonymous). Disabled when auth is not configured. */
export function useSession() {
  return useQuery({
    queryKey: sessionQueryKey,
    queryFn: loadSession,
    enabled: isAuthConfigured,
    staleTime: Infinity,
    retry: false,
  })
}

/** Re-reads the session when Amplify signs the user out or a token refresh fails. */
export function useAuthEvents(): void {
  const queryClient = useQueryClient()
  useEffect(() => {
    if (!isAuthConfigured) return undefined
    return Hub.listen('auth', ({ payload }) => {
      if (payload.event === 'signedIn' || payload.event === 'signedOut' || payload.event === 'tokenRefresh_failure') {
        void queryClient.invalidateQueries({ queryKey: sessionQueryKey })
      }
    })
  }, [queryClient])
}

/** Signs out, drops all cached user data and navigates to /sign-in (spec 04 Behaviour 7). */
export function useSignOut(): () => Promise<void> {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  return useCallback(async () => {
    try {
      await signOut()
    } finally {
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== sessionQueryKey[0] })
      await queryClient.invalidateQueries({ queryKey: sessionQueryKey })
      navigate('/sign-in', { replace: true })
    }
  }, [queryClient, navigate])
}

/** Target after sign-in: the page `RequireAuth` redirected from, else Home `/` (spec 04 Behaviour 5). */
export function redirectTarget(state: unknown): string {
  const from = (state as { from?: unknown } | null)?.from
  return typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') ? from : '/'
}
