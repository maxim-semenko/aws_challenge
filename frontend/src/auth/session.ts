import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchAuthSession, getCurrentUser, signOut } from 'aws-amplify/auth'
import { Hub } from 'aws-amplify/utils'
import { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router'
import { isAuthConfigured } from '../config/amplify'
import { groupsFromClaims } from '../profile/format'

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

/** Key of the token groups; first element is not 'auth', so useSignOut drops it; the user id separates sessions. */
export const groupsQueryKey = (userId: string | undefined) => ['groups', userId] as const

async function loadGroups(): Promise<string[]> {
  const { tokens } = await fetchAuthSession()
  if (!tokens?.accessToken) throw new Error('No access token in the session')
  return groupsFromClaims(tokens.accessToken.payload)
}

/**
 * Cognito groups of the signed-in user from the access token claim `cognito:groups` (no API call, owner decision
 * 2026-11-17). Display only — the API enforces the group. Enabled only with a session; read once per session.
 */
export function useGroups() {
  const session = useSession()
  const userId = session.data?.userId
  return useQuery({
    queryKey: groupsQueryKey(userId),
    queryFn: loadGroups,
    enabled: Boolean(userId),
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
