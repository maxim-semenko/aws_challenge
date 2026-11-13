import { isCountryCode } from './countries'

/**
 * Sign-up field validation. The SPA is the only place where these ranges are enforced (Q-14 C);
 * the rules mirror spec 04 §Inputs exactly — change them there first.
 */

export interface SignUpForm {
  givenName: string
  familyName: string
  email: string
  password: string
  confirmPassword: string
  gender: string
  birthDate: string
  country: string
  height: string
  weight: string
}

export type SignUpField = keyof SignUpForm
export type FieldErrors = Partial<Record<SignUpField, string>>

/** Exactly the attributes sent to Cognito SignUp (spec 04 §Inputs, column "Sent as"). */
export interface SignUpAttributes {
  email: string
  given_name: string
  family_name: string
  gender: string
  birthdate: string
  'custom:country': string
  'custom:height': string
  'custom:weight': string
}

export interface SignUpRequest {
  username: string
  password: string
  attributes: SignUpAttributes
}

export type SignUpValidation = { ok: true; request: SignUpRequest } | { ok: false; errors: FieldErrors }

export const EMPTY_SIGN_UP_FORM: SignUpForm = {
  givenName: '',
  familyName: '',
  email: '',
  password: '',
  confirmPassword: '',
  gender: '',
  birthDate: '',
  country: '',
  height: '',
  weight: '',
}

const NAME_MAX_LENGTH = 50
const NAME_PATTERN = /^[\p{L} '-]+$/u
const EMAIL_MAX_LENGTH = 254
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PASSWORD_MIN_LENGTH = 8
const DATE_PATTERN = /^(\d{2})\/(\d{2})\/(\d{4})$/
const EARLIEST_BIRTHDATE = '1900-01-01'
const MIN_AGE_YEARS = 13
const INTEGER_PATTERN = /^\d+$/
export const HEIGHT_RANGE = { min: 50, max: 250 } as const
export const WEIGHT_RANGE = { min: 20, max: 300 } as const

const REQUIRED = 'Required'

type Result = { value: string; error?: undefined } | { value?: undefined; error: string }

export function validateName(input: string): Result {
  const value = input.trim()
  if (!value) return { error: REQUIRED }
  if ([...value].length > NAME_MAX_LENGTH) return { error: `At most ${NAME_MAX_LENGTH} characters` }
  if (!NAME_PATTERN.test(value)) return { error: 'Only letters, spaces, hyphens and apostrophes' }
  return { value }
}

export function validateEmail(input: string): Result {
  const value = input.trim().toLowerCase()
  if (!value) return { error: REQUIRED }
  if (value.length > EMAIL_MAX_LENGTH) return { error: `At most ${EMAIL_MAX_LENGTH} characters` }
  if (!EMAIL_PATTERN.test(value)) return { error: 'Enter a valid e-mail address' }
  return { value }
}

/** Cognito default password policy (ARCHITECTURE §3.4): ≥ 8 characters, upper, lower, digit, symbol. */
export function validatePassword(input: string): Result {
  if (!input) return { error: REQUIRED }
  const ok =
    input.length >= PASSWORD_MIN_LENGTH &&
    /[a-z]/.test(input) &&
    /[A-Z]/.test(input) &&
    /\d/.test(input) &&
    /[^A-Za-z0-9]/.test(input)
  if (!ok) return { error: 'At least 8 characters with upper- and lower-case letters, a digit and a symbol' }
  return { value: input }
}

function pad(value: number, length: number): string {
  return String(value).padStart(length, '0')
}

function isoDate(date: Date): string {
  return `${pad(date.getFullYear(), 4)}-${pad(date.getMonth() + 1, 2)}-${pad(date.getDate(), 2)}`
}

/** Parses DD/MM/YYYY into YYYY-MM-DD: a real calendar date from 1900-01-01 to today minus 13 years. */
export function parseBirthDate(input: string, today: Date = new Date()): Result {
  const match = DATE_PATTERN.exec(input.trim())
  if (!match) return { error: 'Use the format DD/MM/YYYY' }
  const [, dd, mm, yyyy] = match
  const day = Number(dd)
  const month = Number(mm)
  const year = Number(yyyy)
  const date = new Date(Date.UTC(year, month - 1, day))
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) {
    return { error: 'Not a real calendar date' }
  }
  const value = `${yyyy}-${mm}-${dd}`
  if (value < EARLIEST_BIRTHDATE) return { error: 'Must be 01/01/1900 or later' }
  if (value > isoDate(today)) return { error: 'Date is in the future' }
  const cutoff = `${pad(today.getFullYear() - MIN_AGE_YEARS, 4)}-${pad(today.getMonth() + 1, 2)}-${pad(today.getDate(), 2)}`
  if (value > cutoff) return { error: `You must be at least ${MIN_AGE_YEARS} years old` }
  return { value }
}

export function validateInteger(input: string, range: { min: number; max: number }): Result {
  const value = input.trim()
  if (!value) return { error: REQUIRED }
  if (!INTEGER_PATTERN.test(value)) return { error: 'Enter a whole number' }
  const number = Number(value)
  if (number < range.min || number > range.max) return { error: `Between ${range.min} and ${range.max}` }
  return { value: String(number) }
}

export function validateGender(input: string): Result {
  return input === 'F' || input === 'M' ? { value: input } : { error: 'Select F or M' }
}

export function validateCountry(input: string): Result {
  return isCountryCode(input) ? { value: input } : { error: 'Select a country' }
}

/** Validates every field; returns the exact SignUp request only when all fields are valid. */
export function validateSignUp(form: SignUpForm, today: Date = new Date()): SignUpValidation {
  const results: Record<SignUpField, Result> = {
    givenName: validateName(form.givenName),
    familyName: validateName(form.familyName),
    email: validateEmail(form.email),
    password: validatePassword(form.password),
    confirmPassword: !form.confirmPassword
      ? { error: REQUIRED }
      : form.confirmPassword !== form.password
        ? { error: 'Passwords do not match' }
        : { value: form.confirmPassword },
    gender: validateGender(form.gender),
    birthDate: parseBirthDate(form.birthDate, today),
    country: validateCountry(form.country),
    height: validateInteger(form.height, HEIGHT_RANGE),
    weight: validateInteger(form.weight, WEIGHT_RANGE),
  }

  const errors: FieldErrors = {}
  for (const field of Object.keys(results) as SignUpField[]) {
    const error = results[field].error
    if (error) errors[field] = error
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors }

  const value = (field: SignUpField): string => results[field].value ?? ''
  return {
    ok: true,
    request: {
      username: value('email'),
      password: value('password'),
      attributes: {
        email: value('email'),
        given_name: value('givenName'),
        family_name: value('familyName'),
        gender: value('gender'),
        birthdate: value('birthDate'),
        'custom:country': value('country'),
        'custom:height': value('height'),
        'custom:weight': value('weight'),
      },
    },
  }
}
