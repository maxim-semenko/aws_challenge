import { Authenticator } from '@aws-amplify/ui-react'
import { NavLink, Navigate, Route, Routes } from 'react-router'
import { isAuthConfigured } from './config/amplify'
import { AdminPage } from './pages/AdminPage'
import { ChatPage } from './pages/ChatPage'
import { HomePage } from './pages/HomePage'
import './App.css'

function Layout({ email, onSignOut }: { email?: string; onSignOut?: () => void }) {
  return (
    <>
      <header>
        <nav>
          <NavLink to="/">Home</NavLink>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/admin">Admin</NavLink>
        </nav>
        {onSignOut && (
          <div className="row">
            <span>{email}</span>
            <button onClick={onSignOut}>Sign out</button>
          </div>
        )}
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  )
}

export default function App() {
  // Without Cognito settings (pure local dev against the "local" Spring profile) skip the login screen
  if (!isAuthConfigured) {
    return <Layout />
  }

  return (
    <Authenticator signUpAttributes={['email']} loginMechanisms={['email']}>
      {({ signOut, user }) => <Layout email={user?.signInDetails?.loginId} onSignOut={signOut} />}
    </Authenticator>
  )
}
