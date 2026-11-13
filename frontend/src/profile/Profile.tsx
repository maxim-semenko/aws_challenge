import { useQuery } from '@tanstack/react-query'
import { fetchUserAttributes } from 'aws-amplify/auth'
import { useEffect } from 'react'
import { ApiError, endpoints, meQueryKey } from '../api/client'
import { useSignOut } from '../auth/session'
import { env } from '../config/amplify'
import { formatBirthdate, formatCountry, formatMeasure, formatText, roleLine } from './format'

export const userAttributesQueryKey = ['user-attributes'] as const

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/** Role line from GET /api/me; "Role: unavailable" on 5xx/network errors (spec 04). Mounted only with VITE_API_URL. */
function RoleLineView() {
  const signOutAndRedirect = useSignOut()
  const me = useQuery({
    queryKey: meQueryKey,
    queryFn: endpoints.me,
    retry: (failureCount, error) => !isUnauthorized(error) && failureCount < 1,
  })

  useEffect(() => {
    // 401: token expired and refresh failed → clear the session and go to /sign-in
    if (isUnauthorized(me.error)) void signOutAndRedirect()
  }, [me.error, signOutAndRedirect])

  if (me.isPending) return <p>Role: …</p>
  return <p>{roleLine(me.isSuccess ? me.data.groups : undefined)}</p>
}

/** Read-only profile of the signed-in user from Cognito attributes, shown on Home `/` (ADR-013, spec 04 §Outputs). */
export function Profile() {
  const attributes = useQuery({ queryKey: userAttributesQueryKey, queryFn: () => fetchUserAttributes() })

  if (attributes.isPending) return <p>Loading…</p>

  if (attributes.isError) {
    return (
      <section>
        <h1>My profile</h1>
        <p role="alert" className="error">
          Could not load your profile.
        </p>
        <button type="button" onClick={() => void attributes.refetch()} disabled={attributes.isFetching}>
          {attributes.isFetching ? 'Retrying…' : 'Retry'}
        </button>
      </section>
    )
  }

  const data = attributes.data
  const rows = [
    { label: 'First name', value: formatText(data.given_name) },
    { label: 'Last name', value: formatText(data.family_name) },
    { label: 'Email', value: formatText(data.email) },
    { label: 'Gender', value: formatText(data.gender) },
    { label: 'Date of birth', value: formatBirthdate(data.birthdate) },
    { label: 'Country', value: formatCountry(data['custom:country']) },
    { label: 'Height', value: formatMeasure(data['custom:height'], 'cm') },
    { label: 'Weight', value: formatMeasure(data['custom:weight'], 'kg') },
  ]

  return (
    <section>
      <h1>My profile</h1>
      <dl>
        {rows.map((row) => (
          <div key={row.label}>
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
      {/* Without VITE_API_URL the role line is not rendered and no request is made (owner decision 2026-11-13) */}
      {env.apiUrl && <RoleLineView />}
    </section>
  )
}
