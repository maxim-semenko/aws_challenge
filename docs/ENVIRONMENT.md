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
| Lambda functions | `aws-challenge-admin`, `aws-challenge-chatbot`, `aws-challenge-sync` (names confirmed 2026-11-16); zip, **Python 3.12** (ADR-015 revised 2026-11-16: 3.12 is the target, no runtime switch); no `aws-challenge-migrate` (never created; runner lives in `sync`, ADR-017 revised); API Gateway trigger on `admin` and `chatbot`. Code in Git under [`lambdas/`](../lambdas/) |
| `aws-challenge-sync` settings (2026-11-16, before T03-03) | 128 MB, timeout 3 s, x86_64, handler `lambda_function.lambda_handler`, no env vars, no layers; role `aws-challenge-sync-role-q8b1jajy` with `AWSLambdaBasicExecutionRole-…` (logs only). `admin` and `chatbot` are configured the same way, each with its own console-created role (owner) |
| Lambda VPC config (all three) | `aws-challenge-vpc`; subnets `subnet-0158cc34af19a05c3` (`aws-challenge-subnet-private1-eu-west-1a`, 10.0.128.0/20), `subnet-0686f4fa10f9d139a` (`aws-challenge-subnet-private2-eu-west-1b`, 10.0.144.0/20); security groups `sg-09356f785149eeb60` (default) + `sg-01f3496b63a8a0e7e` (`aws-challenge-db-sg`) |
| RDS instance endpoint | `aws-challenge-db.cbk4syqsq9pn.eu-west-1.rds.amazonaws.com:5432` (owner, 2026-11-16; used by the Week 1 TCP probe) |
| Week 1 `admin` probe | TCP connect to the instance endpoint on 5432 only — no driver, no credentials, not through RDS Proxy (T03-03 Notes) |

## Database (Week 1, T01-02)

Source: the owner's console screenshots, 2026-11-16.

| Item | Value |
|---|---|
| DB instance | `aws-challenge-db`, PostgreSQL 14.18, `db.t4g.micro` (2 vCPU, 1 GB), `eu-west-1a`, single-AZ; gp2 20 GiB, autoscaling on; encrypted (`aws/rds`); RDS Extended Support disabled (R-14) |
| Master user / DB name | `postgres` / none set at creation (the default database `postgres` exists) |
| IAM DB authentication (instance) | not enabled |
| RDS Proxy | `proxy-1793961665875-aws-challenge-db` (`prx-019d0caac664f7be9`), engine family PostgreSQL |
| Proxy endpoint | `proxy-1793961665875-aws-challenge-db.proxy-cbk4syqsq9pn.eu-west-1.rds.amazonaws.com` (read/write) |
| Proxy settings | Require TLS: **enabled** (2026-11-16, T03-03); idle client timeout 30 min; enhanced logging off; IAM role `rds-proxy-role-1793961664993`; security group `sg-01f3496b63a8a0e7e`; subnets `subnet-0158cc34af19a05c3`, `subnet-0686f4fa10f9d139a` |
| Proxy authentication | secret `rds-db-credentials/…/postgres` (RDS-managed master secret), client auth SCRAM SHA 256, **IAM authentication: Required** (2026-11-16, T03-03) |
| Proxy target group | `default` → `aws-challenge-db`, **Available** since 2026-11-16 (was Unavailable until the self-referencing SG rule below was added) |
| Security group `aws-challenge-db-sg` (`sg-01f3496b63a8a0e7e`) | created by the RDS console; inbound: TCP 5432 from itself (`sg-01f3496b63a8a0e7e`, "proxy and lambdas to db", added 2026-11-16) and TCP 5432 from `185.53.96.139/32` (one external IP, not needed — the DB has no public access); outbound: all traffic to `0.0.0.0/0` (owner evidence 2026-11-16, T03-03 step 1); attached to the proxy, the DB instance (assumed) and all three Lambdas |
| Default security group | `sg-09356f785149eeb60`: inbound all traffic from itself; attached to all three Lambdas |

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
| Groups | `admin` (created 2026-11-16, T03-01): no IAM role, no precedence; members: `test@gmail.com` |
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

Rewrites and redirects (since 2026-11-16, T03-09): one rule — source `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>` → `/index.html`, type `200 (Rewrite)` (replaced the default `/<*>` 404-rewrite).

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
| CORS | origins `https://main.d67fa9mmezz1k.amplifyapp.com` and `http://localhost:5173` (added 2026-11-17, T03-07); headers `authorization`, `content-type`; methods `*`; max age 600; credentials no (verified by unauthenticated preflight probes 2026-11-17) |

## Sync chain (Week 3, T03-05)

Source: the owner's console screenshots, 2026-11-17.

| Item | Value |
|---|---|
| Event bus | `aws-challenge-events` — **Classic** bus type (the new "Custom" bus type has no rules; ARN `event-bus/aws-challenge-events`) |
| Rule | `aws-challenge-user-confirmed`: pattern `{"source":["aws-challenge.cognito"],"detail-type":["UserConfirmed"]}` → `aws-challenge-sync`; max event age 1 h, 5 retries, no DLQ; no tags |
| Trigger function | `aws-challenge-post-confirmation`: Python 3.12, x86_64, no VPC, 256 MB, 5 s, env `EVENT_BUS_NAME=aws-challenge-events`; role `aws-challenge-post-confirmation-role` (inline `aws-challenge-post-confirmation-policy`: `events:PutEvents` on the bus, own log stream writes); log group retention 2 weeks |
| Cognito trigger | Post confirmation → `aws-challenge-post-confirmation` (fires on the console "Confirm account" too) |
| `aws-challenge-sync` | 256 MB, 60 s, env `DB_PROXY_ENDPOINT`/`DB_NAME=postgres`/`DB_USER=postgres`; role adds inline `aws-challenge-sync-rds-connect` (`rds-db:connect` on `prx-019d0caac664f7be9/postgres`); schema V1 applied 2026-11-16 |
| Back-fill | not done (owner, 2026-11-17): users confirmed before the trigger are not in `users` |

## Not recorded yet

Supplied by the owner when a task needs them: DB instance security groups (Connectivity & security → Security section), function memory/timeout/role, Amplify app id.
