import { useQuery } from '@tanstack/react-query'
import { fetchUserAttributes } from 'aws-amplify/auth'
import { ApiError } from '../api/client'
import { useMe } from '../api/queries'
import { isApiConfigured } from '../config/amplify'
import { formatBirthdate, formatCountry, formatMeasure, formatText, selectRoleLine } from './format'

export const userAttributesQueryKey = ['user-attributes'] as const

/** Role line from GET /api/me (spec 09); mounted only when the API is configured, so no request otherwise. */
function RoleLine() {
  const me = useMe()
  const errorStatus = me.error instanceof ApiError ? me.error.status : undefined
  const line = selectRoleLine(me.status, me.data?.groups, errorStatus)
  return line ? <p className="badge">{line}</p> : null
}

/** Read-only profile of the signed-in user from Cognito attributes, shown on Home `/` (ADR-013, spec 04 §Outputs). */
export function Profile() {
  const attributes = useQuery({ queryKey: userAttributesQueryKey, queryFn: () => fetchUserAttributes() })

  if (attributes.isPending) return <p className="status">Loading…</p>

  if (attributes.isError) {
    return (
      <section className="card">
        <h1>My profile</h1>
        <p role="alert" className="message message-error">
          Could not load your profile.
        </p>
        <button
          type="button"
          className="button-block"
          onClick={() => void attributes.refetch()}
          disabled={attributes.isFetching}
        >
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
    <section className="card">
      <h1>My profile</h1>
      <dl className="profile-list">
        {rows.map((row) => (
          <div key={row.label} className="profile-row">
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
      {isApiConfigured && <RoleLine />}
    </section>
  )
}
