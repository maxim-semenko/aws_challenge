import { useMutation, useQueryClient } from '@tanstack/react-query'
import { signIn } from 'aws-amplify/auth'
import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { errorName, signInErrorMessage } from '../auth/errors'
import { redirectTarget, sessionQueryKey } from '../auth/session'

interface SignInState {
  email?: unknown
  notice?: unknown
}

function stateString(state: unknown, key: keyof SignInState): string {
  const value = (state as SignInState | null)?.[key]
  return typeof value === 'string' ? value : ''
}

/** /sign-in: e-mail + password via SRP (Amplify default USER_SRP_AUTH); unconfirmed users go to /confirm. */
export function SignInPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState(() => stateString(location.state, 'email'))
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [unsupported, setUnsupported] = useState(false)
  const notice = stateString(location.state, 'notice')
  const target = redirectTarget(location.state)

  const mutation = useMutation({
    mutationFn: (values: { email: string; password: string }) =>
      signIn({ username: values.email, password: values.password }),
    onSuccess: async (result, values) => {
      const step = result.nextStep.signInStep
      if (step === 'DONE') {
        await queryClient.invalidateQueries({ queryKey: sessionQueryKey })
        navigate(target, { replace: true })
      } else if (step === 'CONFIRM_SIGN_UP') {
        navigate('/confirm', { state: { email: values.email } })
      } else {
        // e.g. a user created in the console with a temporary password; not part of spec 04
        setUnsupported(true)
      }
    },
    onError: (error, values) => {
      if (errorName(error) === 'UserNotConfirmedException') {
        navigate('/confirm', { state: { email: values.email } })
      }
    },
  })

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setUnsupported(false)
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

  const showError = mutation.error && errorName(mutation.error) !== 'UserNotConfirmedException'

  return (
    <section>
      <h1>Sign in</h1>
      {notice && <p role="status">{notice}</p>}
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
      {showError && (
        <p role="alert" className="error">
          {signInErrorMessage(mutation.error)}
        </p>
      )}
      {unsupported && (
        <p role="alert" className="error">
          This account needs a sign-in step the app does not support.
        </p>
      )}
      <p>
        No account yet? <Link to="/sign-up">Sign up</Link>
      </p>
    </section>
  )
}
