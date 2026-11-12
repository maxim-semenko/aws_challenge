import { useMutation } from '@tanstack/react-query'
import { confirmSignUp, resendSignUpCode } from 'aws-amplify/auth'
import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { confirmErrorMessage, resendErrorMessage } from '../auth/errors'
import { validateConfirmationCode, validateEmail } from '../auth/validation'

function initialEmail(state: unknown): string {
  const email = (state as { email?: unknown } | null)?.email
  return typeof email === 'string' ? email : ''
}

/** /confirm: e-mail (pre-filled, editable) + 6-digit code; "Resend code" (spec 04 §Inputs, Behaviour 3). */
export function ConfirmPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState(() => initialEmail(location.state))
  const [code, setCode] = useState('')
  const [errors, setErrors] = useState<{ email?: string; code?: string }>({})
  const [notice, setNotice] = useState('')

  const confirm = useMutation({
    mutationFn: (values: { email: string; code: string }) =>
      confirmSignUp({ username: values.email, confirmationCode: values.code }),
    onSuccess: (_result, values) => {
      navigate('/sign-in', { state: { email: values.email, notice: 'E-mail confirmed. Sign in to continue.' } })
    },
  })

  const resend = useMutation({
    mutationFn: (value: string) => resendSignUpCode({ username: value }),
    onSuccess: () => setNotice('A new code was sent to your e-mail.'),
  })

  function onConfirm(event: FormEvent) {
    event.preventDefault()
    setNotice('')
    const emailResult = validateEmail(email)
    const codeResult = validateConfirmationCode(code)
    setErrors({ email: emailResult.error, code: codeResult.error })
    if (emailResult.value && codeResult.value) {
      resend.reset()
      confirm.mutate({ email: emailResult.value, code: codeResult.value })
    }
  }

  function onResend() {
    setNotice('')
    const emailResult = validateEmail(email)
    setErrors({ email: emailResult.error })
    if (emailResult.value) {
      confirm.reset()
      resend.mutate(emailResult.value)
    }
  }

  return (
    <section>
      <h1>Confirm your e-mail</h1>
      <p>Enter the 6-digit code sent to your e-mail.</p>
      <form onSubmit={onConfirm} noValidate>
        <p>
          <label htmlFor="email">Email</label>
          <br />
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
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
          <label htmlFor="code">Code</label>
          <br />
          <input
            id="code"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(event) => setCode(event.currentTarget.value)}
            aria-invalid={Boolean(errors.code)}
          />
          {errors.code && (
            <>
              <br />
              <small className="error">{errors.code}</small>
            </>
          )}
        </p>
        <button type="submit" disabled={confirm.isPending}>
          {confirm.isPending ? 'Confirming…' : 'Confirm'}
        </button>{' '}
        <button type="button" onClick={onResend} disabled={resend.isPending}>
          {resend.isPending ? 'Sending…' : 'Resend code'}
        </button>
      </form>
      {confirm.error && (
        <p role="alert" className="error">
          {confirmErrorMessage(confirm.error)}
        </p>
      )}
      {resend.error && (
        <p role="alert" className="error">
          {resendErrorMessage(resend.error)}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      <p>
        <Link to="/sign-in">Back to sign in</Link>
      </p>
    </section>
  )
}
