export type SignInResult = 'signedIn' | 'notActivated' | 'unsupported'

/**
 * Maps Amplify `nextStep.signInStep` to what the sign-in page does (spec 04 Behaviour 5, §Edge Cases).
 * `CONFIRM_SIGN_UP` = the owner has not confirmed the user in the Cognito console yet (decision 2026-11-13).
 */
export function signInResult(signInStep: string): SignInResult {
  if (signInStep === 'DONE') return 'signedIn'
  if (signInStep === 'CONFIRM_SIGN_UP') return 'notActivated'
  // e.g. a user created in the console with a temporary password; not part of spec 04
  return 'unsupported'
}
