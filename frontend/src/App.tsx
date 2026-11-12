import { NavLink, Navigate, Route, Routes } from 'react-router'
import { AnonymousOnly, RequireAuth } from './auth/guards'
import { useAuthEvents, useSession, useSignOut } from './auth/session'
import { isAuthConfigured } from './config/amplify'
import { AdminPage } from './pages/AdminPage'
import { ChatPage } from './pages/ChatPage'
import { ConfirmPage } from './pages/ConfirmPage'
import { HomePage } from './pages/HomePage'
import { MePage } from './pages/MePage'
import { SignInPage } from './pages/SignInPage'
import { SignUpPage } from './pages/SignUpPage'
import './App.css'

/** Auth links in the header; rendered only when Cognito is configured (AC-04.10). */
function AuthNav() {
  const session = useSession()
  const signOut = useSignOut()
  useAuthEvents()

  if (session.isPending) return null
  if (!session.data) {
    return (
      <div className="row">
        <NavLink to="/sign-in">Sign in</NavLink>
        <NavLink to="/sign-up">Sign up</NavLink>
      </div>
    )
  }
  return (
    <div className="row">
      <NavLink to="/me">My page</NavLink>
      {session.data.loginId && <span>{session.data.loginId}</span>}
      <button type="button" onClick={() => void signOut()}>
        Sign out
      </button>
    </div>
  )
}

export default function App() {
  return (
    <>
      <header>
        <nav>
          <NavLink to="/">Home</NavLink>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/admin">Admin</NavLink>
        </nav>
        {isAuthConfigured && <AuthNav />}
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/admin" element={<AdminPage />} />
          {isAuthConfigured && (
            <>
              <Route path="/sign-up" element={<AnonymousOnly><SignUpPage /></AnonymousOnly>} />
              <Route path="/confirm" element={<AnonymousOnly><ConfirmPage /></AnonymousOnly>} />
              <Route path="/sign-in" element={<AnonymousOnly><SignInPage /></AnonymousOnly>} />
              <Route path="/me" element={<RequireAuth><MePage /></RequireAuth>} />
            </>
          )}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  )
}
