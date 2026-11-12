import { signUp } from 'aws-amplify/auth'
import { validateSignUp, type FieldErrors, type SignUpForm } from './validation'

export type SignUpOutcome =
  | { kind: 'invalid'; errors: FieldErrors }
  | { kind: 'confirm'; email: string }
  | { kind: 'done'; email: string }

/**
 * Validates the form and calls Cognito SignUp only when every field is valid (spec 04 Behaviour 1, AC-04.4).
 * `signUpFn` is injectable for tests; Cognito errors propagate to the caller.
 */
export async function submitSignUp(
  form: SignUpForm,
  signUpFn: typeof signUp = signUp,
  today: Date = new Date(),
): Promise<SignUpOutcome> {
  const validation = validateSignUp(form, today)
  if (!validation.ok) return { kind: 'invalid', errors: validation.errors }

  const { username, password, attributes } = validation.request
  const result = await signUpFn({ username, password, options: { userAttributes: { ...attributes } } })
  return result.nextStep.signUpStep === 'CONFIRM_SIGN_UP'
    ? { kind: 'confirm', email: username }
    : { kind: 'done', email: username }
}
