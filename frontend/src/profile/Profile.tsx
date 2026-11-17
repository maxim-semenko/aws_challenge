import { useQuery } from '@tanstack/react-query'
import { fetchUserAttributes } from 'aws-amplify/auth'
import { useGroups } from '../auth/session'
import { formatBirthdate, formatCountry, formatMeasure, formatText, selectRoleLine } from './format'

export const userAttributesQueryKey = ['user-attributes'] as const

/** Role line from the access token `cognito:groups` claim (spec 09, owner decision 2026-11-17; no API call). */
function RoleLine() {
  const groups = useGroups()
  const line = selectRoleLine(groups.status, groups.data)
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
      <RoleLine />
    </section>
  )
}
