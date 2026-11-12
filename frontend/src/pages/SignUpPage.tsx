import { useMutation } from '@tanstack/react-query'
import { useMemo, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { countryOptions } from '../auth/countries'
import { MESSAGES, signUpErrorMessage } from '../auth/errors'
import { submitSignUp } from '../auth/signUpFlow'
import { EMPTY_SIGN_UP_FORM, type FieldErrors, type SignUpField, type SignUpForm } from '../auth/validation'

interface FieldProps {
  name: SignUpField
  label: string
  form: SignUpForm
  errors: FieldErrors
  onChange: (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void
  type?: string
  autoComplete?: string
  inputMode?: 'numeric' | 'email' | 'text'
  placeholder?: string
}

function TextField({ name, label, form, errors, onChange, type = 'text', autoComplete, inputMode, placeholder }: FieldProps) {
  const errorId = `${name}-error`
  return (
    <p>
      <label htmlFor={name}>{label}</label>
      <br />
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
        aria-describedby={errors[name] ? errorId : undefined}
      />
      {errors[name] && (
        <>
          <br />
          <small id={errorId} className="error">
            {errors[name]}
          </small>
        </>
      )}
    </p>
  )
}

/** /sign-up: all fields of spec 04 §Inputs, validated in the browser before any Cognito call (AC-04.4). */
export function SignUpPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<SignUpForm>(EMPTY_SIGN_UP_FORM)
  const [errors, setErrors] = useState<FieldErrors>({})
  const countries = useMemo(() => countryOptions(), [])

  const mutation = useMutation({
    mutationFn: (values: SignUpForm) => submitSignUp(values),
    onSuccess: (outcome) => {
      if (outcome.kind === 'invalid') {
        setErrors(outcome.errors)
      } else if (outcome.kind === 'confirm') {
        navigate('/confirm', { state: { email: outcome.email } })
      } else {
        navigate('/sign-in', { state: { email: outcome.email } })
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

  const exists = mutation.error ? signUpErrorMessage(mutation.error) === MESSAGES.accountExists : false
  const field = { form, errors, onChange }

  return (
    <section>
      <h1>Sign up</h1>
      <form onSubmit={onSubmit} noValidate>
        <TextField name="givenName" label="First name" autoComplete="given-name" {...field} />
        <TextField name="familyName" label="Last name" autoComplete="family-name" {...field} />
        <TextField name="email" label="Email" type="email" inputMode="email" autoComplete="email" {...field} />
        <TextField name="password" label="Password" type="password" autoComplete="new-password" {...field} />
        <TextField
          name="confirmPassword"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          {...field}
        />
        <p>
          <label htmlFor="gender">Gender</label>
          <br />
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
          {errors.gender && (
            <>
              <br />
              <small id="gender-error" className="error">
                {errors.gender}
              </small>
            </>
          )}
        </p>
        <TextField
          name="birthDate"
          label="Date of birth (DD/MM/YYYY)"
          inputMode="numeric"
          autoComplete="bday"
          placeholder="DD/MM/YYYY"
          {...field}
        />
        <p>
          <label htmlFor="country">Country of living</label>
          <br />
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
          {errors.country && (
            <>
              <br />
              <small id="country-error" className="error">
                {errors.country}
              </small>
            </>
          )}
        </p>
        <TextField name="height" label="Height, cm" inputMode="numeric" {...field} />
        <TextField name="weight" label="Weight, kg" inputMode="numeric" {...field} />
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Signing up…' : 'Sign up'}
        </button>
      </form>
      {mutation.error && (
        <p role="alert" className="error">
          {signUpErrorMessage(mutation.error)}
          {exists && (
            <>
              {' '}
              — <Link to="/sign-in">sign in</Link>
            </>
          )}
        </p>
      )}
      <p>
        Already registered? <Link to="/sign-in">Sign in</Link>
      </p>
    </section>
  )
}
