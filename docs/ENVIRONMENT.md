# ENVIRONMENT.md — AWS resources as built

Single home of the identifiers and settings of the resources the owner created manually in the AWS console
(agents have no AWS access, CLAUDE.md §3.11). Every task that creates or changes a resource adds its values here;
other documents link to this file instead of copying values. Single environment, names `aws-challenge-<name>`
(CLAUDE.md §7). Never record the account id, passwords, secrets or tokens here — only public identifiers.

## Network (Week 1, T01-01)

Source: the owner's VPC console screenshot, 2026-11-12 (evidence for T01-06).

| Item | Value |
|---|---|
| Region | `eu-west-1` (ADR-009); AZs `eu-west-1a`, `eu-west-1b` |
| VPC | `aws-challenge-vpc` (`vpc-0ef5bbc86c0dd7f68`), CIDR `10.0.0.0/16`, DNS resolution and DNS hostnames enabled |
| Subnets | public: `aws-challenge-subnet-public1-eu-west-1a`, `aws-challenge-subnet-public2-eu-west-1b`; private: `aws-challenge-subnet-private1-eu-west-1a`, `aws-challenge-subnet-private2-eu-west-1b` |
| Route tables | `aws-challenge-rtb-public`, `aws-challenge-rtb-private1-eu-west-1a`, `aws-challenge-rtb-private2-eu-west-1b`, plus the main route table |
| Internet gateway | `aws-challenge-igw` |
| VPC endpoints | `aws-challenge-vpce-s3` (S3 gateway endpoint) |
| NAT gateway | **none shown** on the network map — to be confirmed by the owner ([R-09](RISKS.md#2-risk-register)) |

## Compute (Week 1, T01-04)

| Item | Value |
|---|---|
| Lambda functions | `aws-challenge-admin`, `aws-challenge-chatbot`, `aws-challenge-sync` — by the naming convention; exact names to be confirmed by the owner. Runtime Python. Code in Git under [`lambdas/`](../lambdas/) |

## Authentication (Week 2, T02-01)

Source: the owner, 2026-11-12. Both ids are public (they ship in the SPA bundle).

| Item | Value |
|---|---|
| Cognito User Pool id | `eu-west-1_MhEy7LlVv` |
| User Pool name | `aws-challenge-users` |
| Feature plan | Essentials |
| Self-registration | enabled |
| Deletion protection | active; encryption with the AWS managed key |
| Sign-in | email; password only (passwordless inactive); MFA off; devices not remembered |
| Attributes | required: `given_name`, `family_name`, `gender`, `birthdate`; custom: `country` (String), `height` (Number), `weight` (Number), Cognito default bounds, mutable (Q-14 C) |
| App client | `aws-challenge-frontend-spa`, id `384mpdjvmjpb1s9ddqjcbg79hg`, no client secret |
| App client auth flows | choice-based sign-in (`ALLOW_USER_AUTH`), SRP (`ALLOW_USER_SRP_AUTH`), refresh (`ALLOW_REFRESH_TOKEN_AUTH`) |
| Token validity | access 60 min, ID 60 min, refresh 5 days, auth session 3 min; token revocation on; prevent user existence errors on |
| Cognito domain (managed login, not used by the SPA — ADR-014) | `https://eu-west-1mhey7llvv.auth.eu-west-1.amazoncognito.com` |
| Issuer (for the JWT authorizer, T02-03) | `https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_MhEy7LlVv` |

## Amplify Hosting (Week 1 T01-05, Week 2)

Source: the owner's console screenshots, 2026-11-12. App `aws_challenge`, all branches. Domain (branch `main`):
`https://main.d67fa9mmezz1k.amplifyapp.com` — the SPA origin for CORS (T02-03).

| Environment variable | Value |
|---|---|
| `AMPLIFY_DIFF_DEPLOY` | `false` |
| `AMPLIFY_MONOREPO_APP_ROOT` | `frontend` |
| `AMPLIFY_MONOREPO_APP_ROOT_frontend` | `frontend` |
| `VITE_AWS_REGION` | `eu-west-1` |
| `VITE_USER_POOL_ID` | User Pool id above |
| `VITE_USER_POOL_CLIENT_ID` | App client id above |
| `VITE_API_URL` | HTTP API endpoint below |

The SPA reads exactly these names (`frontend/src/config/amplify.ts`, aligned by T02-04; no default region).

## HTTP API (Week 2)

Source: the owner's console screenshots, 2026-11-13; unauthenticated probes of the public endpoint the same day
(`/admin` without a token → 401; CORS preflight from the Amplify origin → 204).

| Item | Value |
|---|---|
| API | `aws-challenge-api`, id `o6cpz238i3`, HTTP API, stage `$default` |
| Endpoint | `https://o6cpz238i3.execute-api.eu-west-1.amazonaws.com` |
| Authorizer | `cognito-jwt-authorizer` (id `fvppl3`), JWT; identity source `$request.header.Authorization`; issuer = Issuer above; audience = App client id above |
| Routes | `GET /admin` (JWT), `POST /chat` (JWT, integration `dyujbqp`); no authorization scopes. Changed from `ANY` on 2026-11-13 because `ANY` caught the CORS preflight (T02-03 Notes) |
| CORS | origin `https://main.d67fa9mmezz1k.amplifyapp.com`; headers `authorization`, `content-type`; methods `*`; max age 0; credentials no |

## Not recorded yet

Supplied by the owner when a task needs them: security groups, RDS instance class and PostgreSQL minor version, RDS
Proxy endpoint and settings, function memory/timeout/role, Amplify app id.
