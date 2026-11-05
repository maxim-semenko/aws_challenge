import { Amplify } from 'aws-amplify'

/**
 * Cognito settings come from Vite env vars (VITE_*), see .env.example.
 * In Amplify Hosting set them under App settings -> Environment variables.
 */
export const env = {
  region: import.meta.env.VITE_AWS_REGION ?? 'us-east-1',
  userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID ?? '',
  userPoolClientId: import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID ?? '',
  // Empty = same origin (Vite dev proxy forwards /api to Spring Boot on :8080)
  apiUrl: (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, ''),
}

export const isAuthConfigured = Boolean(env.userPoolId && env.userPoolClientId)

export function configureAmplify() {
  if (!isAuthConfigured) {
    console.warn('Cognito is not configured: set VITE_COGNITO_USER_POOL_ID / VITE_COGNITO_USER_POOL_CLIENT_ID')
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
