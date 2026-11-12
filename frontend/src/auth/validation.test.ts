import { describe, expect, it, vi } from 'vitest'
import { submitSignUp } from './signUpFlow'
import { parseBirthDate, validateSignUp, type SignUpForm } from './validation'

const TODAY = new Date(2026, 10, 12) // 12/11/2026, local time

const VALID: SignUpForm = {
  givenName: ' Anna-Maria ',
  familyName: "O'Neil",
  email: ' Anna@Example.COM ',
  password: 'Secret#123',
  confirmPassword: 'Secret#123',
  gender: 'F',
  birthDate: '29/02/2000',
  country: 'DE',
  height: '170',
  weight: '65',
}

function signUpMock() {
  return vi.fn().mockResolvedValue({
    isSignUpComplete: false,
    nextStep: { signUpStep: 'CONFIRM_SIGN_UP', codeDeliveryDetails: {} },
  })
}

describe('validateSignUp', () => {
  it('builds exactly the Cognito attributes of spec 04 for a valid form', () => {
    const result = validateSignUp(VALID, TODAY)
    expect(result).toEqual({
      ok: true,
      request: {
        username: 'anna@example.com',
        password: 'Secret#123',
        attributes: {
          email: 'anna@example.com',
          given_name: 'Anna-Maria',
          family_name: "O'Neil",
          gender: 'F',
          birthdate: '2000-02-29',
          'custom:country': 'DE',
          'custom:height': '170',
          'custom:weight': '65',
        },
      },
    })
  })

  it('accepts the range bounds', () => {
    const form = { ...VALID, height: '50', weight: '300', birthDate: '12/11/2013' }
    expect(validateSignUp(form, TODAY).ok).toBe(true)
    expect(validateSignUp({ ...VALID, height: '250', weight: '20', birthDate: '01/01/1900' }, TODAY).ok).toBe(true)
  })
})

// AC-04.4: each case is rejected and Cognito SignUp is never called
describe('AC-04.4 rejected without a Cognito call', () => {
  const cases: Array<[string, Partial<SignUpForm>, keyof SignUpForm]> = [
    ['empty first name', { givenName: '   ' }, 'givenName'],
    ['gender X', { gender: 'X' }, 'gender'],
    ['date 31/02/2000', { birthDate: '31/02/2000' }, 'birthDate'],
    ['date less than 13 years ago', { birthDate: '13/11/2013' }, 'birthDate'],
    ['height 49', { height: '49' }, 'height'],
    ['height 170.5', { height: '170.5' }, 'height'],
    ['weight 301', { weight: '301' }, 'weight'],
    ['mismatched password confirmation', { confirmPassword: 'Secret#124' }, 'confirmPassword'],
  ]

  it.each(cases)('%s', async (_label, change, field) => {
    const signUpFn = signUpMock()
    const outcome = await submitSignUp({ ...VALID, ...change }, signUpFn, TODAY)
    expect(outcome.kind).toBe('invalid')
    expect(outcome.kind === 'invalid' && outcome.errors[field]).toBeTruthy()
    expect(signUpFn).not.toHaveBeenCalled()
  })

  it('calls SignUp once for a valid form and asks for confirmation', async () => {
    const signUpFn = signUpMock()
    const outcome = await submitSignUp(VALID, signUpFn, TODAY)
    expect(outcome).toEqual({ kind: 'confirm', email: 'anna@example.com' })
    expect(signUpFn).toHaveBeenCalledTimes(1)
    expect(signUpFn.mock.calls[0][0].options.userAttributes.birthdate).toBe('2000-02-29')
  })
})

describe('field rules (spec 04 §Inputs, §Edge Cases)', () => {
  it.each([
    ['givenName', 'A'.repeat(51)],
    ['givenName', 'Anna1'],
    ['email', 'not-an-email'],
    ['email', `${'a'.repeat(250)}@x.io`],
    ['password', 'short1#A'.slice(0, 7)],
    ['password', 'nouppercase1#'],
    ['country', 'XX'],
    ['country', 'de'],
    ['height', '251'],
    ['height', '-5'],
    ['height', ''],
    ['weight', '19'],
    ['weight', 'abc'],
    ['gender', ''],
  ] as Array<[keyof SignUpForm, string]>)('%s = %j is rejected', (field, value) => {
    const form = { ...VALID, [field]: value }
    if (field === 'password') form.confirmPassword = value
    const result = validateSignUp(form, TODAY)
    expect(result.ok).toBe(false)
    expect(!result.ok && result.errors[field]).toBeTruthy()
  })

  it('accepts Unicode letters in names', () => {
    expect(validateSignUp({ ...VALID, givenName: 'Łukasz', familyName: 'Müller Ñúñez' }, TODAY).ok).toBe(true)
  })

  it.each(['2000-02-01', '1/2/2000', '01-02-2000', '31/12/1899', '13/11/2026', '32/01/2000', '29/02/2001'])(
    'birth date %j is rejected',
    (value) => {
      expect(parseBirthDate(value, TODAY).error).toBeTruthy()
    },
  )

  it('converts DD/MM/YYYY to YYYY-MM-DD', () => {
    expect(parseBirthDate('05/07/1985', TODAY)).toEqual({ value: '1985-07-05' })
  })
})
