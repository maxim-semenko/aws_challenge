/**
 * Maps Amplify/Cognito errors (AuthError.name = Cognito exception name) to the user messages of spec 04
 * §Edge Cases. Raw error messages are never shown for sign-in (no user enumeration) and nothing is logged.
 */

export const MESSAGES = {
  accountExists: 'An account with this e-mail already exists',
  invalidCredentials: 'Incorrect e-mail or password',
  invalidCode: 'Invalid code',
  expiredCode: 'The code has expired, request a new one',
  tooManyAttempts: 'Too many attempts, try later',
  passwordPolicy: 'The password does not meet the password policy',
  alreadyConfirmed: 'This account cannot be confirmed (it may already be confirmed); try signing in',
  signUpFailed: 'Sign-up failed, try again later',
  signInFailed: 'Sign-in failed, try again later',
  confirmFailed: 'Confirmation failed, try again later',
  resendFailed: 'Could not send a new code, try again later',
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
  if (isThrottled(name)) return MESSAGES.tooManyAttempts
  return MESSAGES.signInFailed
}

export function confirmErrorMessage(error: unknown): string {
  const name = errorName(error)
  if (name === 'CodeMismatchException') return MESSAGES.invalidCode
  if (name === 'ExpiredCodeException') return MESSAGES.expiredCode
  if (name === 'NotAuthorizedException') return MESSAGES.alreadyConfirmed
  if (isThrottled(name)) return MESSAGES.tooManyAttempts
  return MESSAGES.confirmFailed
}

export function resendErrorMessage(error: unknown): string {
  return isThrottled(errorName(error)) ? MESSAGES.tooManyAttempts : MESSAGES.resendFailed
}
