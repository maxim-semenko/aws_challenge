/**
 * Maps Amplify/Cognito errors (AuthError.name = Cognito exception name) to the user messages of spec 04
 * §Edge Cases. Raw error messages are never shown for sign-in (no user enumeration) and nothing is logged.
 */

export const MESSAGES = {
  accountCreatedPending: 'Account created. It will be activated by an administrator; then you can sign in.',
  accountCreatedDone: 'Account created. You can sign in now.',
  accountExists: 'An account with this e-mail already exists',
  invalidCredentials: 'Incorrect e-mail or password',
  notActivated: 'Your account is not activated yet',
  tooManyAttempts: 'Too many attempts, try later',
  passwordPolicy: 'The password does not meet the password policy',
  signUpFailed: 'Sign-up failed, try again later',
  signInFailed: 'Sign-in failed, try again later',
} as const

export function errorName(error: unknown): string {
  return error instanceof Error ? error.name : ''
}

function isThrottled(name: string): boolean {
  return name === 'LimitExceededException' || name === 'TooManyRequestsException'
}

export function signUpErrorMessage(error: unknown): string {
  const name = errorName(error)
  if (name === 'UsernameExistsException') return MESSAGES.accountExists
  if (name === 'InvalidPasswordException') return MESSAGES.passwordPolicy
  if (isThrottled(name)) return MESSAGES.tooManyAttempts
  return MESSAGES.signUpFailed
}

export function signInErrorMessage(error: unknown): string {
  const name = errorName(error)
  if (name === 'NotAuthorizedException' || name === 'UserNotFoundException') return MESSAGES.invalidCredentials
  // The owner confirms users manually in the Cognito console (owner decision 2026-11-13)
  if (name === 'UserNotConfirmedException') return MESSAGES.notActivated
  if (isThrottled(name)) return MESSAGES.tooManyAttempts
  return MESSAGES.signInFailed
}
