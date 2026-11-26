---
id: T05-01
title: "LLM model check, chatbot role (Bedrock + RDS), chatbot configuration, POST /chat integration timeout 29 s (console runbook)"
phase: P5-semantic-search
status: Done
agent: devops
skills: [cloud-architect, http-api-jwt, bedrock-embeddings]
depends_on: []
blocked_by: []
design: ../../design/semantic-search.md
spec: ../../specs/12-chat-api.md
acceptance: [AC-12.4, AC-12.5]
---
# T05-01 — Bedrock access and configuration of `aws-challenge-chatbot`

## // BUSINESS CONTEXT

Week 5 S2/S3: the Chatbot Lambda answers `POST /chat` with Bedrock (Titan V2 embedding or an LLM writing SQL) and
PostgreSQL. The Week 1 function is a placeholder with 3 s timeout, 128 MB, no env and a logs-only role. This task gives
it exactly the permissions and settings the code of T05-02 needs, and sets the curriculum timeouts (API Gateway 29 s,
Lambda 30 s), all without a Bedrock call and without the paid endpoint.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes; owner evidence (account id masked).
  Shared corporate account: touch only resources named in this task (never the foreign endpoint listed in ENVIRONMENT.md §Vectorisation).
- Model per Q-22 (owner, 2026-11-25: Amazon Nova Micro through the EU geo inference profile `eu.amazon.nova-micro-v1:0`;
  destination regions for source eu-west-1: eu-central-1, eu-north-1, eu-west-1, eu-west-3 — model card 2026-11-25).
  Step 1 of the runbook: the owner confirms in the Bedrock console (eu-west-1) the inference profile id, its
  destination regions and that the model is *Active* and usable (no Marketplace, no form for an Amazon model). If the
  console shows a different id or region set, stop and report (ARCH updates spec 12 first).
- Role of `aws-challenge-chatbot` (name reported by the owner, recorded in ENVIRONMENT.md): add inline policies only —
  `rds-db:connect` on the proxy `dbuser` ARN (same resource as `aws-challenge-sync-rds-connect`), and
  `bedrock:InvokeModel` on exactly: the Titan V2 foundation-model ARN (eu-west-1); the inference-profile ARN
  `arn:aws:bedrock:eu-west-1:<account-id>:inference-profile/eu.amazon.nova-micro-v1:0`; the foundation-model ARN
  `amazon.nova-micro-v1:0` in each destination region with condition `bedrock:InferenceProfileArn` = that profile ARN
  (design §Security). `AWSLambdaVPCAccessExecutionRole` must be present (VPC function). No `bedrock:*`,
  no `bedrock:InvokeAgent`, no `aws-marketplace:*`, no managed Bedrock policy.
- Function configuration: runtime Python 3.12, handler `lambda_function.lambda_handler`, timeout **30 s**, memory
  **512 MB**, env `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_USER` with the same values as `sync` (ENVIRONMENT.md) and no
  other env var; VPC unchanged (same subnets and SGs as `sync`, so the endpoint SG already admits it); log group
  `/aws/lambda/aws-challenge-chatbot` retention 14 days. No code upload (T05-03).
- HTTP API `aws-challenge-api`: integration of `POST /chat` (id in ENVIRONMENT.md §HTTP API) → timeout **29 000 ms**, payload 2.0, target
  `aws-challenge-chatbot` (verify); routes, authorizer and CORS unchanged.
- No endpoint, NAT, new SG, new route, new function. Cost line: $0 (design §Cost).

## // SCOPE

**Implement**
- Runbook: (1) model / inference-profile check; (2) chatbot role: VPC policy check + two inline policies
  (`aws-challenge-chatbot-rds-connect`, `aws-challenge-chatbot-bedrock-invoke`); (3) function configuration (runtime,
  handler, timeout, memory, env); (4) log retention; (5) `POST /chat` integration timeout; rollback; evidence table
- ENVIRONMENT.md: chatbot settings, role and policy names, model / profile id, integration timeout; skill
  `bedrock-embeddings` "as built" (chatbot IAM incl. inference-profile pattern), skill `http-api-jwt` (integration
  timeout)

**Exclude**
- Code upload, endpoint session, Bedrock calls (T05-03); Bedrock Agent resources (none — Q-21 A, ADR-021); any change to `sync`, `admin`, the authorizer or CORS

**Interfaces that must match**
- Model id = the code constant of T05-02 / spec 12; env names = shared `db.py`; route `POST /chat` (ADR-018).

## Definition of Done

- [ ] Runbook executed; evidence in Notes (profile page, role permissions + both policy JSONs, configuration page,
  env vars, retention, integration timeout — account id masked)
- [ ] ENVIRONMENT.md and skills updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Runbook (owner executes in the AWS console, region **eu-west-1 / Europe (Ireland)**)

≈ 30 min, no Bedrock call, no code upload, no endpoint (all $0). Check the region selector on every page. Steps are
independent; do step 1 first (if it fails, stop).

| Placeholder / value | Value (home: ENVIRONMENT.md) |
|---|---|
| Function | `aws-challenge-chatbot` |
| Chatbot role | `aws-challenge-chatbot-role-…` (console-created in Week 1; name read in step 2.1) |
| Proxy resource id / DB user | `prx-019d0caac664f7be9` / `postgres` |
| Proxy endpoint / DB name / DB user (env) | `proxy-1793961665875-aws-challenge-db.proxy-cbk4syqsq9pn.eu-west-1.rds.amazonaws.com` / `postgres` / `postgres` (same as `sync`) |
| Inference profile | `eu.amazon.nova-micro-v1:0`; destinations eu-central-1, eu-north-1, eu-west-1, eu-west-3 |
| API / `POST /chat` integration | `aws-challenge-api` (`o6cpz238i3`) / `dyujbqp` |
| `<ACCOUNT_ID>` | 12 digits (console top right). Type it only into the IAM JSON editor (step 2); mask it in every screenshot |
| Tags | optional: `project` = `aws-challenge`, `env` = `dev`, `owner` = `max` |

### Step 1 — Nova Micro and the EU inference profile (Bedrock; 5 min)

1. Amazon Bedrock → left menu **Cross-region inference** (under *Infer* / *Inference and assessment*; layouts differ)
   → tab **System-defined inference profiles** → search `nova micro` → open **EU Nova Micro**.
2. Check on the profile page:
   - **Inference profile ID** exactly `eu.amazon.nova-micro-v1:0`; **Status** *Active*;
   - **ARN** = `arn:aws:bedrock:eu-west-1:<ACCOUNT_ID>:inference-profile/eu.amazon.nova-micro-v1:0`;
   - **Destination regions / Models** table: `amazon.nova-micro-v1:0` in exactly **eu-central-1, eu-north-1,
     eu-west-1, eu-west-3**.
3. **Model catalog** → Provider *Amazon* → **Nova Micro**: Model ID `amazon.nova-micro-v1:0`; no *Subscribe* /
   Marketplace button, no use-case form. If a *Model access* page exists: Nova Micro *Access granted* (else **Modify
   model access** → tick only Nova Micro → Submit).
4. **Stop and report** if the id, status or region list differs (more or fewer regions): the policy of step 2 and spec
   12 are updated first.
- **Report:** screenshots of the profile page (id, status, ARN masked, regions) and the Nova Micro model page.

### Step 2 — Role of `aws-challenge-chatbot` (IAM; 10 min)

1. Lambda → `aws-challenge-chatbot` → **Configuration → Permissions** → click the role name → IAM, tab
   **Permissions**. Expected: `AWSLambdaBasicExecutionRole-<uuid>` and `AWSLambdaVPCAccessExecutionRole-<uuid>`
   (customer managed, Week 1). Open the VPC one → JSON contains `ec2:CreateNetworkInterface`,
   `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface`. If missing: **Add permissions → Attach policies** →
   `AWSLambdaVPCAccessExecutionRole` (AWS managed).
2. **Add permissions → Create inline policy → JSON** → replace everything →
   **Next** → name **`aws-challenge-chatbot-rds-connect`** → **Create policy**:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "ConnectToRdsProxyAsPostgres",
         "Effect": "Allow",
         "Action": "rds-db:connect",
         "Resource": "arn:aws:rds-db:eu-west-1:<ACCOUNT_ID>:dbuser:prx-019d0caac664f7be9/postgres"
       }
     ]
   }
   ```

3. Again **Create inline policy → JSON** → name **`aws-challenge-chatbot-bedrock-invoke`**. `Converse` has no IAM action
   of its own; it is authorised by `bedrock:InvokeModel`. A call through the profile is checked twice: on the profile ARN
   and on the foundation model in the region Bedrock routes to — the condition allows those models **only** through
   this profile. `<ACCOUNT_ID>` appears twice; foundation-model ARNs have an empty account field (`::`).

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "InvokeTitanTextEmbeddingsV2",
         "Effect": "Allow",
         "Action": "bedrock:InvokeModel",
         "Resource": "arn:aws:bedrock:eu-west-1::foundation-model/amazon.titan-embed-text-v2:0"
       },
       {
         "Sid": "InvokeNovaMicroEuProfile",
         "Effect": "Allow",
         "Action": "bedrock:InvokeModel",
         "Resource": "arn:aws:bedrock:eu-west-1:<ACCOUNT_ID>:inference-profile/eu.amazon.nova-micro-v1:0"
       },
       {
         "Sid": "InvokeNovaMicroOnlyThroughEuProfile",
         "Effect": "Allow",
         "Action": "bedrock:InvokeModel",
         "Resource": [
           "arn:aws:bedrock:eu-central-1::foundation-model/amazon.nova-micro-v1:0",
           "arn:aws:bedrock:eu-north-1::foundation-model/amazon.nova-micro-v1:0",
           "arn:aws:bedrock:eu-west-1::foundation-model/amazon.nova-micro-v1:0",
           "arn:aws:bedrock:eu-west-3::foundation-model/amazon.nova-micro-v1:0"
         ],
         "Condition": {
           "StringEquals": {
             "bedrock:InferenceProfileArn": "arn:aws:bedrock:eu-west-1:<ACCOUNT_ID>:inference-profile/eu.amazon.nova-micro-v1:0"
           }
         }
       }
     ]
   }
   ```

   The editor must show no errors or warnings.
4. Final *Permissions* list exactly: logs policy, VPC policy, the two inline policies. Nothing with `bedrock:*`,
   `aws-marketplace:*`, `secretsmanager:*`, no `AmazonBedrock…` managed policy.
- **Report:** role name; screenshot of the policy list; both inline JSONs (account id masked); whether the VPC policy
  existed.

### Step 3 — Function configuration (Lambda; 5 min)

Lambda → `aws-challenge-chatbot`:

1. **Configuration → General configuration → Edit**: Memory **512** MB, Ephemeral storage 512 MB (unchanged), SnapStart
   None, Timeout **0 min 30 sec**, role unchanged → **Save**.
2. **Configuration → Environment variables → Edit**: exactly these three; remove any other (do not add `AWS_REGION`):

   | Key | Value |
   |---|---|
   | `DB_PROXY_ENDPOINT` | `proxy-1793961665875-aws-challenge-db.proxy-cbk4syqsq9pn.eu-west-1.rds.amazonaws.com` |
   | `DB_NAME` | `postgres` |
   | `DB_USER` | `postgres` |

3. **Code → Runtime settings → Edit**: Runtime **Python 3.12**, Handler **`lambda_function.lambda_handler`**,
   Architecture x86_64 → **Save**. Do not touch the code (upload is T05-03; never the inline *Deploy*).
4. **Configuration → VPC**: no change; check `aws-challenge-vpc`, subnets `subnet-0158cc34af19a05c3`,
   `subnet-0686f4fa10f9d139a`, SGs `sg-09356f785149eeb60`, `sg-01f3496b63a8a0e7e`.
- **Report:** screenshots of General configuration, Environment variables, Runtime settings, VPC.

### Step 4 — Log retention (CloudWatch; 2 min)

1. CloudWatch → **Log groups** → `/aws/lambda/aws-challenge-chatbot` → **Actions → Edit retention setting** →
   **2 weeks (14 days)** → **Save**.
2. If the log group does not exist (function never invoked): **Create log group** → name
   `/aws/lambda/aws-challenge-chatbot`, retention **2 weeks** → **Create** (log class *Standard*).
- **Report:** the log group row showing *Retention 2 weeks*.

### Step 5 — `POST /chat` integration timeout 29 s (API Gateway; 3 min)

1. API Gateway → `aws-challenge-api` → **Develop → Integrations** → select route **`POST /chat`** → integration
   `dyujbqp` → **Manage integration → Edit** (or *Edit* on the integration details).
2. Check: Integration type **Lambda function**, region eu-west-1, function **`aws-challenge-chatbot`**.
3. **Advanced settings**: Payload format version **2.0** (set it if 1.0); **Timeout** **29000** ms (default 30000) →
   **Save**. Stage `$default` deploys automatically.
4. Check without changing: **Routes** list is exactly `GET /admin` and `POST /chat`; `POST /chat` → *Authorization*
   `cognito-jwt-authorizer` (JWT). Lambda → `aws-challenge-chatbot` → **Configuration → Permissions → Resource-based
   policy statements**: principal `apigateway.amazonaws.com`, `SourceArn` of API `o6cpz238i3` — just report it.
- **Report:** screenshots of the integration details (target, payload 2.0, timeout 29000), the Routes list, the
  `POST /chat` route details and the resource-based policy statement (account id masked).

### Verify (no token needed)

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" -X POST "https://o6cpz238i3.execute-api.eu-west-1.amazonaws.com/chat"
```

Expected `401` (authorizer unchanged). The functional checks (403/400/200, timings) are T05-03 / T05-05.

### Rollback

- IAM: remove the two inline policies from the chatbot role.
- Lambda: memory 128 MB, timeout 3 s, delete the three env vars (Week 1 values per step 3 screenshots).
- Log group: retention back to *Never expire* (or delete the group if step 4.2 created it).
- API: integration timeout 30000 ms.

### Evidence (account id masked, no tokens)

| # | Evidence | Step | AC / DoD |
|---|---|---|---|
| E1 | Profile page (id, Active, ARN, destination regions) + Nova Micro model page | 1 | DoD; confirms spec 12 model id |
| E2 | Role name, policy list, JSON of both inline policies, VPC policy present | 2 | **AC-12.4** (role part) |
| E3 | General configuration (512 MB, 30 s), env vars (3), runtime/handler, VPC | 3 | **AC-12.4** (config part; zip from Git — T05-03) |
| E4 | Log group retention 2 weeks | 4 | **AC-12.4** (retention) |
| E5 | Integration (chatbot, payload 2.0, 29000 ms), Routes list, route authorizer, resource policy; `curl` 401 | 5, verify | **AC-12.5** |

After the evidence devops records it in Notes and updates ENVIRONMENT.md (chatbot settings, role and policy names,
profile id, integration timeout) and the skills `bedrock-embeddings` and `http-api-jwt`.

### Cost

No new always-on resource → **$0/month**. IAM policies, retention setting and integration timeout are free; 512 MB is
billed only per invocation (≈ $0 at learning volume); the existing on-demand Bedrock endpoint is not used here.

## Notes

- 2026-11-25: created by Week 5 planning; `Blocked` by Q-21 (an agent would add agent resources and a second endpoint)
  and Q-22 (model id and IAM ARNs). Runbook written by devops after the owner's answers.
- 2026-11-25: owner answered Q-21 A (direct `Converse`, no agent) and Q-22 (Nova Micro, `eu.amazon.nova-micro-v1:0`);
  design semantic-search `Accepted` → `Todo`, startable.
- 2026-11-25 (devops): status `In progress`; runbook written (steps 1–5, verify, rollback, evidence E1–E5, cost $0).
  `Converse` is authorised by `bedrock:InvokeModel` (no separate action); Nova Micro foundation-model ARNs listed per
  destination region (no wildcard) with the `bedrock:InferenceProfileArn` condition. PLAN.md not changed (coordinator).
  Waiting for the owner to execute it.
- 2026-11-25 (owner screenshot, step 1): Bedrock → Infer → Inference profiles → System-defined: **EU Nova Micro**, model Nova Micro, ID `eu.amazon.nova-micro-v1:0`, ARN `arn:aws:bedrock:eu-west-…`, regions eu-west-3, eu-west-1, eu-central-1, eu-north-1 — matches spec 12 and the policy (E1, profile part). In the 2026 console the menu is "Infer → Inference profiles", not "Cross-region inference".
- 2026-11-25 (owner): role `aws-challenge-chatbot-role-3euwe6l7` (created 2026-11-12) — had `AWSLambdaBasicExecutionRole-ab760b8d-…` and `AWSLambdaVPCAccessExecutionRole-c74f9e98-…` (screenshot); owner added the two inline policies `aws-challenge-chatbot-rds-connect` and `aws-challenge-chatbot-bedrock-invoke` → 4 policies, and set the function config (512 MB, 30 s, env DB_*) — owner statement, no screenshot. `POST /chat` integration `dyujbqp` (route id `2r7hjw2`) → `aws-challenge-chatbot`, payload 2.0 ✔ (screenshot); timeout was 30000 ms → owner asked to set 29000 ms.
- 2026-11-25 (owner statement): `POST /chat` integration timeout set to 29000 ms; `/aws/lambda/aws-challenge-chatbot` retention 2 weeks. All runbook steps done → `Review` (evidence partly by owner statement).
- 2026-11-26: set to `Done` by the owner (Week 5 closed).
