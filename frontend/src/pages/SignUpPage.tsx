import { useMutation } from '@tanstack/react-query'
import { useMemo, useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router'
import { countryOptions } from '../auth/countries'
import { MESSAGES, signUpErrorMessage } from '../auth/errors'
import { submitSignUp, type SignUpOutcome } from '../auth/signUpFlow'
import { EMPTY_SIGN_UP_FORM, type FieldErrors, type SignUpField, type SignUpForm } from '../auth/validation'

type ChangeHandler = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void

interface FieldProps {
  name: SignUpField
  label: string
  form: SignUpForm
  errors: FieldErrors
  onChange: ChangeHandler
  type?: string
  autoComplete?: string
  inputMode?: 'numeric' | 'email' | 'text'
  placeholder?: string
}

/** Label above the control, field error under it (linked by aria-describedby). */
function FieldShell({ name, label, error, children }: { name: SignUpField; label: string; error?: string; children: ReactNode }) {
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      {children}
      {error && (
        <small id={`${name}-error`} className="field-error">
          {error}
        </small>
      )}
    </div>
  )
}

function TextField({ name, label, form, errors, onChange, type = 'text', autoComplete, inputMode, placeholder }: FieldProps) {
  return (
    <FieldShell name={name} label={label} error={errors[name]}>
      <input
        id={name}
        name={name}
        type={type}
        value={form[name]}
        onChange={onChange}
        autoComplete={autoComplete}
        inputMode={inputMode}
        placeholder={placeholder}
        aria-invalid={Boolean(errors[name])}
        aria-describedby={errors[name] ? `${name}-error` : undefined}
      />
    </FieldShell>
  )
}

type Created = Exclude<SignUpOutcome, { kind: 'invalid' }>

/** Shown after a successful SignUp; the owner activates new users in the Cognito console (decision 2026-11-13). */
function AccountCreated({ outcome }: { outcome: Created }) {
  return (
    <section className="card">
      <h1>Sign up</h1>
      <p role="status" className="message message-info">
        {outcome.kind === 'pendingActivation' ? MESSAGES.accountCreatedPending : MESSAGES.accountCreatedDone}
      </p>
      <p className="card-footer">
        <Link to="/sign-in" state={{ email: outcome.email }}>
          Go to sign in
        </Link>
      </p>
    </section>
  )
}

/** /sign-up: all fields of spec 04 §Inputs, validated in the browser before any Cognito call (AC-04.4). */
export function SignUpPage() {
  const [form, setForm] = useState<SignUpForm>(EMPTY_SIGN_UP_FORM)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [created, setCreated] = useState<Created | null>(null)
  const countries = useMemo(() => countryOptions(), [])

  const mutation = useMutation({
    mutationFn: (values: SignUpForm) => submitSignUp(values),
    onSuccess: (outcome) => {
      if (outcome.kind === 'invalid') {
        setErrors(outcome.errors)
      } else {
        setCreated(outcome)
      }
    },
  })

  function onChange(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = event.currentTarget
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({})
    mutation.mutate(form)
  }

  if (created) return <AccountCreated outcome={created} />

  const exists = mutation.error ? signUpErrorMessage(mutation.error) === MESSAGES.accountExists : false
  const field = { form, errors, onChange }

  return (
    <section className="card card-wide">
      <h1>Sign up</h1>
      <form className="form" onSubmit={onSubmit} noValidate>
        <div className="form-grid">
          <TextField name="givenName" label="First name" autoComplete="given-name" {...field} />
          <TextField name="familyName" label="Last name" autoComplete="family-name" {...field} />
        </div>
        <TextField name="email" label="Email" type="email" inputMode="email" autoComplete="email" {...field} />
        <TextField name="password" label="Password" type="password" autoComplete="new-password" {...field} />
        <TextField
          name="confirmPassword"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          {...field}
        />
        <FieldShell name="gender" label="Gender" error={errors.gender}>
          <select
            id="gender"
            name="gender"
            value={form.gender}
            onChange={onChange}
            aria-invalid={Boolean(errors.gender)}
            aria-describedby={errors.gender ? 'gender-error' : undefined}
          >
            <option value="">Select…</option>
            <option value="F">F</option>
            <option value="M">M</option>
          </select>
        </FieldShell>
        <TextField
          name="birthDate"
          label="Date of birth (DD/MM/YYYY)"
          inputMode="numeric"
          autoComplete="bday"
          placeholder="DD/MM/YYYY"
          {...field}
        />
        <FieldShell name="country" label="Country of living" error={errors.country}>
          <select
            id="country"
            name="country"
            value={form.country}
            onChange={onChange}
            aria-invalid={Boolean(errors.country)}
            aria-describedby={errors.country ? 'country-error' : undefined}
          >
            <option value="">Select…</option>
            {countries.map((country) => (
              <option key={country.code} value={country.code}>
                {country.name} ({country.code})
              </option>
            ))}
          </select>
        </FieldShell>
        <div className="form-grid">
          <TextField name="height" label="Height, cm" inputMode="numeric" {...field} />
          <TextField name="weight" label="Weight, kg" inputMode="numeric" {...field} />
        </div>
        <button type="submit" className="button-primary button-block" disabled={mutation.isPending}>
          {mutation.isPending ? 'Signing up…' : 'Sign up'}
        </button>
      </form>
      {mutation.error && (
        <p role="alert" className="message message-error">
          {signUpErrorMessage(mutation.error)}
          {exists && (
            <>
              {' '}
              — <Link to="/sign-in">sign in</Link>
            </>
          )}
        </p>
      )}
      <p className="card-footer">
        Already registered? <Link to="/sign-in">Sign in</Link>
      </p>
    </section>
  )
}
