import { useMutation, useQueryClient } from '@tanstack/react-query'
import { signIn } from 'aws-amplify/auth'
import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { MESSAGES, signInErrorMessage } from '../auth/errors'
import { redirectTarget, sessionQueryKey } from '../auth/session'
import { signInResult, type SignInResult } from '../auth/signInFlow'

function initialEmail(state: unknown): string {
  const value = (state as { email?: unknown } | null)?.email
  return typeof value === 'string' ? value : ''
}

const STEP_MESSAGES: Record<Exclude<SignInResult, 'signedIn'>, string> = {
  notActivated: MESSAGES.notActivated,
  unsupported: 'This account needs a sign-in step the app does not support.',
}

/**
 * /sign-in: e-mail + password via SRP (Amplify default USER_SRP_AUTH). An unconfirmed user stays here with
 * "Your account is not activated yet" — the owner confirms users in the Cognito console (decision 2026-11-13).
 */
export function SignInPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState(() => initialEmail(location.state))
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [stepMessage, setStepMessage] = useState('')
  const target = redirectTarget(location.state)

  const mutation = useMutation({
    mutationFn: (values: { email: string; password: string }) =>
      signIn({ username: values.email, password: values.password }),
    onSuccess: async (result) => {
      const outcome = signInResult(result.nextStep.signInStep)
      if (outcome === 'signedIn') {
        await queryClient.invalidateQueries({ queryKey: sessionQueryKey })
        navigate(target, { replace: true })
      } else {
        setStepMessage(STEP_MESSAGES[outcome])
      }
    },
  })

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setStepMessage('')
    const trimmedEmail = email.trim().toLowerCase()
    const nextErrors = {
      email: trimmedEmail ? undefined : 'Required',
      password: password ? undefined : 'Required',
    }
    setErrors(nextErrors)
    if (!nextErrors.email && !nextErrors.password) {
      mutation.mutate({ email: trimmedEmail, password })
    }
  }

  return (
    <section>
      <h1>Sign in</h1>
      <form onSubmit={onSubmit} noValidate>
        <p>
          <label htmlFor="email">Email</label>
          <br />
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.currentTarget.value)}
            aria-invalid={Boolean(errors.email)}
          />
          {errors.email && (
            <>
              <br />
              <small className="error">{errors.email}</small>
            </>
          )}
        </p>
        <p>
          <label htmlFor="password">Password</label>
          <br />
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
            aria-invalid={Boolean(errors.password)}
          />
          {errors.password && (
            <>
              <br />
              <small className="error">{errors.password}</small>
            </>
          )}
        </p>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      {mutation.error && (
        <p role="alert" className="error">
          {signInErrorMessage(mutation.error)}
        </p>
      )}
      {stepMessage && (
        <p role="alert" className="error">
          {stepMessage}
        </p>
      )}
      <p>
        No account yet? <Link to="/sign-up">Sign up</Link>
      </p>
    </section>
  )
}
