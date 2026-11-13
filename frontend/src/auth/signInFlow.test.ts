import { describe, expect, it } from 'vitest'
import { signInResult } from './signInFlow'

describe('signInResult (spec 04 Behaviour 5, §Edge Cases)', () => {
  it.each([
    ['DONE', 'signedIn'],
    ['CONFIRM_SIGN_UP', 'notActivated'],
    ['CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED', 'unsupported'],
  ])('%s -> %s', (step, expected) => {
    expect(signInResult(step)).toBe(expected)
  })
})
