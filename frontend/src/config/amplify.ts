import { Amplify } from 'aws-amplify'

/**
 * Public Cognito identifiers and the API base URL come only from Vite env vars (names: spec 04 §Inputs,
 * values: docs/ENVIRONMENT.md). Locally they go to .env.local; in Amplify Hosting they are environment variables.
 * Every value may be empty: then the auth UI is hidden and the home page still renders (AC-04.10).
 */
export const env = {
  region: (import.meta.env.VITE_AWS_REGION ?? '').trim(),
  userPoolId: (import.meta.env.VITE_USER_POOL_ID ?? '').trim(),
  userPoolClientId: (import.meta.env.VITE_USER_POOL_CLIENT_ID ?? '').trim(),
  apiUrl: (import.meta.env.VITE_API_URL ?? '').trim().replace(/\/$/, ''),
}

export const isAuthConfigured = Boolean(env.region && env.userPoolId && env.userPoolClientId)

/**
 * The SPA calls the API only when VITE_API_URL is set; every route needs a Cognito access token, so auth must be
 * configured too. Otherwise no API request is made at all (AC-04.10, spec 09 Behaviour 4).
 */
export const isApiConfigured = Boolean(env.apiUrl) && isAuthConfigured

/** Configures Amplify Auth once at start-up; a no-op without configuration. Sign-in uses the default USER_SRP_AUTH. */
export function configureAmplify(): void {
  if (!isAuthConfigured) {
    return
  }
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: env.userPoolId,
        userPoolClientId: env.userPoolClientId,
        loginWith: { email: true },
        signUpVerificationMethod: 'code',
      },
    },
  })
}
