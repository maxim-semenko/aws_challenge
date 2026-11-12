import { describe, expect, it } from 'vitest'
import { MESSAGES, confirmErrorMessage, resendErrorMessage, signInErrorMessage, signUpErrorMessage } from './errors'

function cognitoError(name: string): Error {
  const error = new Error('raw Cognito message')
  error.name = name
  return error
}

describe('error mapping (spec 04 §Edge Cases)', () => {
  it('sign-up', () => {
    expect(signUpErrorMessage(cognitoError('UsernameExistsException'))).toBe(MESSAGES.accountExists)
    expect(signUpErrorMessage(cognitoError('LimitExceededException'))).toBe(MESSAGES.tooManyAttempts)
  })

  it('sign-in gives one generic message for wrong password and unknown e-mail', () => {
    expect(signInErrorMessage(cognitoError('NotAuthorizedException'))).toBe(MESSAGES.invalidCredentials)
    expect(signInErrorMessage(cognitoError('UserNotFoundException'))).toBe(MESSAGES.invalidCredentials)
    expect(signInErrorMessage(cognitoError('TooManyRequestsException'))).toBe(MESSAGES.tooManyAttempts)
  })

  it('confirm and resend', () => {
    expect(confirmErrorMessage(cognitoError('CodeMismatchException'))).toBe(MESSAGES.invalidCode)
    expect(resendErrorMessage(cognitoError('LimitExceededException'))).toBe(MESSAGES.tooManyAttempts)
    expect(resendErrorMessage(new Error('x'))).toBe(MESSAGES.resendFailed)
  })
})
