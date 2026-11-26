import { NavLink, Navigate, Route, Routes } from 'react-router'
import { AnonymousOnly, RequireAuth } from './auth/guards'
import { useAuthEvents, useGroups, useSession, useSignOut } from './auth/session'
import { isApiConfigured, isAuthConfigured } from './config/amplify'
import { AdminPage } from './pages/AdminPage'
import { ChatPage } from './pages/ChatPage'
import { HomePage } from './pages/HomePage'
import { SignInPage } from './pages/SignInPage'
import { SignUpPage } from './pages/SignUpPage'
import './App.css'

/**
 * Header: Chat and Admin only when the access token `cognito:groups` claim contains `admin` (spec 09, spec 13;
 * display only, no API call); auth links only when Cognito is configured (AC-04.10). Without configuration
 * the session query is disabled, so everybody is anonymous.
 */
function Header() {
  const session = useSession()
  const signOut = useSignOut()
  const groups = useGroups()
  useAuthEvents()
  const signedIn = Boolean(session.data)
  const isAdmin = groups.data?.includes('admin') ?? false

  return (
    <header className="app-header">
      <div className="container">
        <nav>
          <NavLink to="/" end>
            Home
          </NavLink>
          {signedIn && isAdmin && (
            <>
              <NavLink to="/chat">Chat</NavLink>
              <NavLink to="/admin">Admin</NavLink>
            </>
          )}
        </nav>
        {isAuthConfigured && !session.isPending && (
          <div className="header-account">
            {signedIn ? (
              <>
                {session.data?.loginId && <span className="header-user">{session.data.loginId}</span>}
                <button type="button" onClick={() => void signOut()}>
                  Sign out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/sign-in">Sign in</NavLink>
                <NavLink to="/sign-up">Sign up</NavLink>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  )
}

export default function App() {
  return (
    <>
      <Header />
      <main className="container">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route
            path="/chat"
            element={isApiConfigured ? <RequireAuth><ChatPage /></RequireAuth> : <ChatPage />}
          />
          <Route
            path="/admin"
            element={isApiConfigured ? <RequireAuth><AdminPage /></RequireAuth> : <AdminPage />}
          />
          {isAuthConfigured && (
            <>
              <Route path="/sign-up" element={<AnonymousOnly><SignUpPage /></AnonymousOnly>} />
              <Route path="/sign-in" element={<AnonymousOnly><SignInPage /></AnonymousOnly>} />
            </>
          )}
          {/* /me and /confirm were removed (owner decision 2026-11-13); every unknown path goes to Home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  )
}
