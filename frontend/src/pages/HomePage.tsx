import { Link } from 'react-router'
import { useSession } from '../auth/session'
import { isAuthConfigured } from '../config/amplify'
import { Profile } from '../profile/Profile'

/** Home `/`: the own profile for a signed-in user, a short intro with sign-in / sign-up links otherwise (spec 04). */
export function HomePage() {
  const session = useSession()

  if (isAuthConfigured && session.isPending) return <p className="status">Loading…</p>
  if (session.data) return <Profile />

  return (
    <section className="card card-centered">
      <h1>AWS Challenge</h1>
      <p className="muted">A serverless learning application on AWS.</p>
      {isAuthConfigured && (
        <>
          <p>Sign in to see your profile, or sign up for an account.</p>
          <div className="actions">
            <Link to="/sign-in" className="button button-primary">
              Sign in
            </Link>
            <Link to="/sign-up" className="button">
              Sign up
            </Link>
          </div>
        </>
      )}
    </section>
  )
}
