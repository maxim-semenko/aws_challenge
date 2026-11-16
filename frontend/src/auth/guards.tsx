import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { redirectTarget, useSession } from './session'

/**
 * Signed-in routes: anonymous visitors go to /sign-in and come back after sign-in. Used by /admin when the API is
 * configured (spec 09); needs auth configured, otherwise the disabled session query stays pending.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const session = useSession()
  const location = useLocation()
  if (session.isPending) return <p>Loading…</p>
  if (!session.data) {
    return <Navigate to="/sign-in" replace state={{ from: `${location.pathname}${location.search}` }} />
  }
  return children
}

/** Anonymous-only routes (/sign-up, /sign-in): a signed-in user goes to the requested page or Home `/`. */
export function AnonymousOnly({ children }: { children: ReactNode }) {
  const session = useSession()
  const location = useLocation()
  if (session.isPending) return <p>Loading…</p>
  if (session.data) return <Navigate to={redirectTarget(location.state)} replace />
  return children
}
