import { NavLink, Navigate, Route, Routes } from 'react-router'
import { AnonymousOnly } from './auth/guards'
import { useAuthEvents, useSession, useSignOut } from './auth/session'
import { isAuthConfigured } from './config/amplify'
import { AdminPage } from './pages/AdminPage'
import { ChatPage } from './pages/ChatPage'
import { HomePage } from './pages/HomePage'
import { SignInPage } from './pages/SignInPage'
import { SignUpPage } from './pages/SignUpPage'
import './App.css'

/**
 * Header: Chat and Admin links only for a signed-in user; auth links only when Cognito is configured (AC-04.10).
 * Without configuration the session query is disabled, so everybody is anonymous.
 */
function Header() {
  const session = useSession()
  const signOut = useSignOut()
  useAuthEvents()
  const signedIn = Boolean(session.data)

  return (
    <header>
      <nav>
        <NavLink to="/" end>
          Home
        </NavLink>
        {signedIn && (
          <>
            <NavLink to="/chat">Chat</NavLink>
            <NavLink to="/admin">Admin</NavLink>
          </>
        )}
      </nav>
      {isAuthConfigured && !session.isPending && (
        <div className="row">
          {signedIn ? (
            <>
              {session.data?.loginId && <span>{session.data.loginId}</span>}
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
    </header>
  )
}

export default function App() {
  return (
    <>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/admin" element={<AdminPage />} />
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
