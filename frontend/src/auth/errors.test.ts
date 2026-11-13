import { describe, expect, it } from 'vitest'
import { MESSAGES, signInErrorMessage, signUpErrorMessage } from './errors'

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

  it('sign-in of an unconfirmed user says the account is not activated yet', () => {
    expect(signInErrorMessage(cognitoError('UserNotConfirmedException'))).toBe(MESSAGES.notActivated)
  })
})
