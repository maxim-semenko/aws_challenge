import { Link } from 'react-router'
import { useSession } from '../auth/session'
import { isAuthConfigured } from '../config/amplify'
import { Profile } from '../profile/Profile'

/** Home `/`: the own profile for a signed-in user, a short intro with sign-in / sign-up links otherwise (spec 04). */
export function HomePage() {
  const session = useSession()

  if (isAuthConfigured && session.isPending) return <p>Loading…</p>
  if (session.data) return <Profile />

  return (
    <section>
      <h1>AWS Challenge</h1>
      <p>A serverless learning application on AWS.</p>
      {isAuthConfigured && (
        <p>
          <Link to="/sign-in">Sign in</Link> to see your profile, or <Link to="/sign-up">sign up</Link> for an account.
        </p>
      )}
    </section>
  )
}
