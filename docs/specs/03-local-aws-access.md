# Spec 03 — Local AWS access (CLI and SDK)

Requirements: [week-01](../requirements/week-01-environment.md) W1-G3 · Design: — (no feature design needed)
Tasks: T00-01, T01-06

## Purpose

A developer machine reaches the project AWS account with the AWS CLI and the AWS SDKs through one named profile,
without long-lived keys in the repository.

## Inputs

| Name | Type | Valid range | Required |
|---|---|---|---|
| AWS account | existing account | root user not used for daily work | yes |
| Profile name | string | `awsch` | yes |
| Region | string | value from Q-03 | yes |
| SDK scope | decision Q-11 | JS SDK v3 and/or Java SDK 2.x | yes |

## Outputs

| Output | Structure | Guarantees |
|---|---|---|
| CLI profile `awsch` | entry in `~/.aws/config` (SSO or IAM user with MFA) | resolves credentials for the project account |
| Budget alert | AWS Budgets, monthly, 80 % / 100 % to the owner's email | confirmed subscription |
| README section "Local AWS access" | profile, region, login command | no secrets |

## Behaviour

1. Owner creates the working identity (IAM Identity Center user or IAM user with MFA) and the budget alert.
2. Developer configures profile `awsch` and logs in.
3. `aws sts get-caller-identity --profile awsch` returns the project account.
4. Each SDK chosen in Q-11 calls STS `GetCallerIdentity` with the default credential chain and `AWS_PROFILE=awsch`
   and prints the same account id (one-off check, output recorded in the task).

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| SSO session expired | CLI/SDK report expired token; `aws sso login --profile awsch` fixes it |
| Default profile points to another account | checks use `--profile awsch` / `AWS_PROFILE`, never the default |
| Keys found in the repository | treated as an incident: revoke keys, clean history |

## Acceptance Criteria

- [ ] AC-03.1 `aws sts get-caller-identity --profile awsch` succeeds (account id may be masked in the record)
- [ ] AC-03.2 The SDK check(s) from Q-11 print the same account id
- [ ] AC-03.3 Budget alert exists and the email subscription is confirmed
- [ ] AC-03.4 README has the "Local AWS access" section; no credentials in the repository
