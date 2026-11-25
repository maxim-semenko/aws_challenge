---
id: T04-01
title: "Bedrock Titan V2 access check, on-demand bedrock-runtime endpoint, sync IAM permission (console runbook)"
phase: P4-vectorisation
status: Done
agent: devops
skills: [cloud-architect]
depends_on: []
blocked_by: []
design: ../../design/vectorisation.md
spec: ../../specs/10-embeddings.md
acceptance: [AC-10.6]
---
# T04-01 — Bedrock access and on-demand network path for `aws-challenge-sync`

## // BUSINESS CONTEXT

W4-G2, S2: the Sync Lambda must call Amazon Bedrock to compute embeddings, but it runs in private subnets without
egress (R-09). This task gives it exactly one private path to Bedrock — an interface endpoint that the owner creates
only for working sessions (ADR-020, cost) — and exactly one permission, so the code of T04-02 can run on AWS.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes; owner evidence (account id masked).
- Model: Amazon Titan Text Embeddings V2, model id `amazon.titan-embed-text-v2:0`, region eu-west-1, in-region
  (ADR-019). Amazon model: no Marketplace subscription; the function role gets no `aws-marketplace:*` permission.
- Permanent (free) resources: security group `aws-challenge-vpce-sg` in `aws-challenge-vpc` (inbound TCP 443 only from
  the Lambda default security group, values in ENVIRONMENT.md; no other inbound rule); inline policy
  `aws-challenge-sync-bedrock-invoke` on the sync role with `bedrock:InvokeModel` on
  `arn:aws:bedrock:eu-west-1::foundation-model/amazon.titan-embed-text-v2:0` only.
- On-demand resource (ADR-020): interface endpoint `com.amazonaws.eu-west-1.bedrock-runtime` named
  `aws-challenge-vpce-bedrock-runtime`, one subnet `aws-challenge-subnet-private1-eu-west-1a`, private DNS on, policy
  *Full access*, security group `aws-challenge-vpce-sg` only. The runbook has two reusable procedures — **Create
  endpoint** (with verify: status *Available*, private DNS names) and **Delete endpoint** (with verify: gone from the
  list) — that every later Bedrock session (T04-03, Week 5) runs at its start and end. In this task the owner runs
  Create, verifies, then Delete (minutes, < $0.01).
- No change of the function's code, timeout, memory, env or VPC. No NAT gateway.
- Tags per CLAUDE.md §7 on the endpoint and the security group. Cost line in the runbook (design §Cost: ≈ $0.011/h
  while the endpoint exists).

## // SCOPE

**Implement**
- Runbook: (1) model check in the Bedrock console, eu-west-1 — Titan Text Embeddings V2 listed, access available,
  model id shown (screenshot); (2) security group; (3) inline policy on the sync role; (4) procedure **Create
  endpoint**; (5) procedure **Delete endpoint**; rollback (delete endpoint and SG, remove the policy)
- ENVIRONMENT.md: Bedrock model id, SG id, policy name, endpoint "on demand — created per session" (no stable id);
  skill `bedrock-embeddings` section "as built" (T04-02 creates the skill)

**Exclude**
- Code upload, migration, Bedrock test calls from `sync` (T04-03); NAT gateway; Bedrock Agent endpoint (Week 5)

**Interfaces that must match**
- Model id = the code constant of T04-02 (`amazon.titan-embed-text-v2:0`); endpoint service name `bedrock-runtime`
  (the code uses boto3's default endpoint, resolved by private DNS).

## Definition of Done

- [ ] Runbook executed; evidence in Notes (model page, SG rules, inline policy JSON, endpoint *Available* with private
  DNS, endpoint deleted afterwards — account id masked)
- [ ] ENVIRONMENT.md updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Runbook (owner executes in the AWS console, region **eu-west-1 / Europe (Ireland)**)

Check the region selector (top right) on every page. Total ≈ 30 min. The order matters only for step 4 (needs the SG
of step 2). Steps 1–3 are done once; steps 4 and 5 are the **reusable session procedures**.

| Placeholder / value | Value (home: ENVIRONMENT.md) |
|---|---|
| VPC | `aws-challenge-vpc` (`vpc-0ef5bbc86c0dd7f68`) |
| Endpoint subnet | `aws-challenge-subnet-private1-eu-west-1a` (`subnet-0158cc34af19a05c3`) — this one only |
| Lambda default SG (source of the inbound rule) | `sg-09356f785149eeb60` (*default*, attached to all three Lambdas) |
| Sync role | `aws-challenge-sync-role-q8b1jajy` |
| Model id | `amazon.titan-embed-text-v2:0` |
| Model ARN (no account id — foundation models are AWS-owned) | `arn:aws:bedrock:eu-west-1::foundation-model/amazon.titan-embed-text-v2:0` |
| Tags (optional; skip if you prefer) | `project` = `aws-challenge`, `env` = `dev`, `owner` = `max` |

No step needs the account id. Mask it in every screenshot where the console shows it (ARNs, top-right menu).

### Step 1 — Model check: Titan Text Embeddings V2 (Bedrock; 5 min, once)

1. Amazon Bedrock → left menu **Model catalog** (under *Discover*; older layout: *Foundation models → Base models*).
2. Filter **Provider = Amazon** (or search `Titan Text Embeddings V2`) → open **Titan Text Embeddings V2**.
3. Look for, on the model page:
   - **Model ID** `amazon.titan-embed-text-v2:0` (exactly; not `amazon.titan-embed-text-v1`, not `…-v2:0:8k`);
   - inference type **On-demand** / serverless available in eu-west-1 (no "provisioned throughput only" note);
   - no *Subscribe* / Marketplace button (Amazon model).
4. Access:
   - **Current console (no *Model access* page in the menu):** serverless models are enabled by default; access is
     controlled only by IAM (step 3). Nothing to enable.
   - **If a *Model access* page exists** (Bedrock configurations → Model access): find *Titan Text Embeddings V2* →
     status must be **Access granted**. If not: **Modify model access** (or *Enable specific models*) → tick only
     *Titan Text Embeddings V2* → **Next** → **Submit**; Amazon models are granted within a minute; refresh.
5. Optional Playground check: Bedrock playgrounds (Chat / Text / Image) do not run embedding models, so an *Open in
   playground* button that is missing or greyed out for this model is expected — skip it. (A console test would use
   the public endpoint anyway, not the VPC path; the real call is tested in T04-03.)
- **Report:** screenshot of the model page with the Model ID; screenshot of the *Model access* row if that page exists
  (or the sentence "no Model access page").

### Step 2 — Security group `aws-challenge-vpce-sg` (EC2 / VPC; 5 min, once, permanent, free)

Why a new SG instead of reusing one: attaching the default SG `sg-09356f785149eeb60` to the endpoint would also work
(it admits all traffic from its members), but it makes the endpoint a member of a group that allows *all ports* between
members, so the endpoint's network interface could open connections to the Lambdas and every future member of the
default group would get full access to it. `aws-challenge-db-sg` is for PostgreSQL 5432 only. A dedicated group with
one rule (443 from the Lambdas) is free and exact.

1. EC2 → **Network & Security → Security Groups** (or VPC → *Security → Security groups*) → **Create security group**.
2. Security group name `aws-challenge-vpce-sg`; Description `Bedrock runtime endpoint: HTTPS from Lambdas`; VPC
   **`aws-challenge-vpc`** (not the default VPC).
3. **Inbound rules → Add rule:** Type **HTTPS** (TCP 443 is filled in); Source **Custom** → start typing `sg-0935` →
   pick `sg-09356f785149eeb60` (*default*); Description `Lambdas (default SG) to bedrock-runtime`. This is the only
   inbound rule.
4. **Outbound rules:** delete the pre-filled *All traffic → 0.0.0.0/0* rule (**Delete**), so the list is empty. An
   interface endpoint only answers connections; it never opens one, and replies to allowed inbound traffic pass
   anyway (security groups are stateful).
5. Tags: optional (the three tags above). → **Create security group**.
6. No change on the Lambda side: the Lambdas' SGs already allow all outbound traffic (`aws-challenge-db-sg` outbound
   *All traffic → 0.0.0.0/0*, ENVIRONMENT.md), which covers 443 to the endpoint.
- **Report:** the SG id (`sg-…`); screenshots of the *Inbound rules* tab (one rule: HTTPS, 443, source
  `sg-09356f785149eeb60`) and the *Outbound rules* tab (empty).

### Step 3 — Inline policy `aws-challenge-sync-bedrock-invoke` on the sync role (IAM; 5 min, once, free)

1. IAM → **Roles** → search `aws-challenge-sync-role-q8b1jajy` → open it.
2. **Add permissions → Create inline policy** → switch the editor to **JSON** → replace everything with:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "InvokeTitanTextEmbeddingsV2",
         "Effect": "Allow",
         "Action": "bedrock:InvokeModel",
         "Resource": "arn:aws:bedrock:eu-west-1::foundation-model/amazon.titan-embed-text-v2:0"
       }
     ]
   }
   ```

   The ARN has **two colons** after `eu-west-1` (empty account field) — keep it exactly like that. The policy editor
   must show no errors or warnings (a warning about the resource means a typo).
3. **Next** → Policy name `aws-challenge-sync-bedrock-invoke` → **Create policy**.
4. Expected *Permissions* tab of the role: `AWSLambdaBasicExecutionRole-…` (managed), `aws-challenge-sync-rds-connect`
   (inline, T03-05) and `aws-challenge-sync-bedrock-invoke` (inline) — nothing else; in particular no
   `AmazonBedrockFullAccess`, no `bedrock:*`, no `aws-marketplace:*`.
- **Report:** screenshot of the role's *Permissions* tab (three policies) and of the new policy's JSON (account id
  masked if shown anywhere on the page).

### Step 4 — Procedure **Create endpoint** (VPC; 5 min + 2–5 min wait; at the START of every Bedrock session)

Reused by T04-03 and Week 5. Cost starts now: ≈ $0.011/h while the endpoint exists — run step 5 at the end of the
session.

1. VPC → left menu **PrivateLink and Lattice → Endpoints** (older layout: *Virtual private cloud → Endpoints*) →
   **Create endpoint**.
2. **Name tag** `aws-challenge-vpce-bedrock-runtime`.
3. **Type** (*Service category*): **AWS services**.
4. **Services:** search `bedrock-runtime` → select the row **`com.amazonaws.eu-west-1.bedrock-runtime`**, Type
   **Interface**. Not `…bedrock` (control plane), not `…bedrock-agent-runtime` (Week 5), not `…bedrock-runtime-fips`,
   not `…bedrock-mantle` or any other variant.
5. **Network settings:** VPC **`aws-challenge-vpc`**. Open **Additional settings**: **Enable DNS name — ticked**
   (private DNS); DNS record IP type **IPv4**; *Enable private DNS only for inbound endpoint* — **unticked**.
6. **Subnets:** tick **only** the AZ **eu-west-1a** → subnet **`aws-challenge-subnet-private1-eu-west-1a`**
   (`subnet-0158cc34af19a05c3`); leave eu-west-1b unticked. IP address type **IPv4**; *Designate IP addresses*: leave
   empty (automatic).
7. **Security groups:** tick **only `aws-challenge-vpce-sg`**; untick anything pre-selected (often the *default* SG).
8. **Policy:** **Full access** (the sync role's inline policy is the limit).
9. Tags: the Name tag is already set; the other three are optional. → **Create endpoint**.
10. Wait until **Status** turns from *Pending* to **Available** (refresh; usually 2–5 min). Do not run the T04-03
    Bedrock tests before that.
11. **Verify** on the endpoint's pages:
    - *Details:* Status **Available**; Service name `com.amazonaws.eu-west-1.bedrock-runtime`; Endpoint type
      *Interface*; **Private DNS names enabled: Yes**; *DNS names* include `bedrock-runtime.eu-west-1.amazonaws.com`
      (the private DNS name) besides the `vpce-…` names;
    - *Subnets:* exactly one row, `subnet-0158cc34af19a05c3`, eu-west-1a, one private IPv4 address from
      `10.0.128.0/20`;
    - *Security groups:* exactly `aws-challenge-vpce-sg`;
    - *Policy:* Full access.
    If *Private DNS names enabled* is *No*: delete the endpoint (step 5) and create it again with **Enable DNS name**
    ticked (4.5).
- **Report** (first run only, for this task): the endpoint id (`vpce-…`, changes every session — recorded only as
  evidence, not in ENVIRONMENT.md); screenshots of *Details* (Available, private DNS Yes, DNS names), *Subnets* and
  *Security groups*. Later sessions: just the *Available* status line in that task's Notes.

### Step 5 — Procedure **Delete endpoint** (VPC; 2 min; at the END of every Bedrock session)

1. VPC → **PrivateLink and Lattice → Endpoints** → tick **`aws-challenge-vpce-bedrock-runtime`** (check the name: never
   tick `aws-challenge-vpce-s3`, the permanent S3 gateway endpoint).
2. **Actions → Delete VPC endpoints** → type `delete` in the confirmation box → **Delete**.
3. Status *Deleting* → refresh after 1–2 min until the row is **gone**.
4. **Verify:** the Endpoints list shows only `aws-challenge-vpce-s3` (Gateway). The SG `aws-challenge-vpce-sg` and the
   inline policy stay (permanent, free).
- **Report:** screenshot of the Endpoints list without the Bedrock endpoint, with the time of deletion.

**Reminder:** a forgotten endpoint costs ≈ $0.26/day (≈ $8/month). Before closing the console at the end of any
session that ran step 4, open the Endpoints list and confirm the Bedrock endpoint is gone. While it is absent, a
Bedrock call from `sync` fails fast and the row is stored without a vector (design §4; filled later by
`embed-missing`).

### In this task

Run steps 1, 2, 3, then step 4 (verify), then step 5 right away (no Bedrock call from `sync` in this task — that is
T04-03). Endpoint lifetime: minutes, < $0.01.

### Rollback (if the change has to be undone)

1. Step 5 (delete the endpoint, if it exists).
2. EC2 → Security Groups → `aws-challenge-vpce-sg` → **Actions → Delete security groups** (works only when no endpoint
   uses it).
3. IAM → Roles → `aws-challenge-sync-role-q8b1jajy` → *Permissions* → tick `aws-challenge-sync-bedrock-invoke` →
   **Remove**.
4. Model access (step 1): nothing to undo (enabling access has no cost and grants nothing without IAM).

### Evidence (report back; account id masked)

| # | Evidence | Step | AC / DoD |
|---|---|---|---|
| E1 | Model page: Titan Text Embeddings V2, Model ID `amazon.titan-embed-text-v2:0`, on-demand; *Model access* row *Access granted* or "no Model access page" | 1 | DoD (model page); confirms the model id of design §1 |
| E2 | SG id; *Inbound rules* (HTTPS 443 from `sg-09356f785149eeb60` only); *Outbound rules* (empty) | 2 | DoD (SG rules) |
| E3 | Sync role *Permissions* tab (three policies) + JSON of `aws-challenge-sync-bedrock-invoke` | 3 | **AC-10.6** (permission part; the log-content part of AC-10.6 is checked in T04-03) |
| E4 | Endpoint id; *Details* (Available, Private DNS names enabled Yes, DNS names), *Subnets* (one, eu-west-1a), *Security groups* (`aws-challenge-vpce-sg` only) | 4 | DoD (endpoint Available with private DNS) |
| E5 | Endpoints list without `aws-challenge-vpce-bedrock-runtime`, time of deletion | 5 | DoD (endpoint deleted) |

After the evidence: devops records it below and updates ENVIRONMENT.md (model id, SG id, policy name, endpoint "on
demand — created per session", the create/delete procedures referenced from here); the skill `bedrock-embeddings`
(created by T04-02) gets its "as built" section.

### Cost (eu-west-1; re-check on the AWS pricing pages)

| Resource | Always on? | Cost |
|---|---|---|
| Security group `aws-challenge-vpce-sg` | yes | $0 |
| Inline policy `aws-challenge-sync-bedrock-invoke` | yes | $0 |
| Model access Titan V2 | yes | $0 (pay per token only when called) |
| Interface endpoint `aws-challenge-vpce-bedrock-runtime`, one AZ | **no — on demand** (ADR-020) | ≈ $0.011/h + $0.01/GB processed; this task (minutes) < $0.01; a 3-hour session ≈ $0.03; forgotten for a month ≈ $8 |

No new always-on resource with a monthly cost.

## Notes

- 2026-11-17: created by Week 4 planning; `Blocked` by Q-15 and Q-20.
- 2026-11-18: unblocked — owner answered Q-15 (Titan V2, 1024, ADR-019) and Q-20 (endpoint on demand, ADR-020);
  design vectorisation `Accepted`. Scope re-cut to the on-demand endpoint (create/delete procedures). → `Todo`.
- 2026-11-18: devops wrote the runbook (steps 1–5, rollback, evidence E1–E5, cost); dedicated SG chosen over reusing
  the default SG (reason in step 2). Waiting for the owner to execute it. → `In progress`.
- 2026-11-18 (owner screenshot, step 1 partial): Bedrock Model catalog eu-west-1, provider Amazon — 6 models: Nova 2 Lite, Nova Micro, Nova Lite, Nova Pro, "Titan Text Embedding…" (output vector size 1024 default, 512, 256; Serverless) and Titan Multimodal Embeddings. No 1536-dim Titan (G1) in the region — confirms ADR-019. Model ID on the model page still to confirm (`amazon.titan-embed-text-v2:0`).
- 2026-11-18 (owner screenshot): model page — Model ID `amazon.titan-embed-text-v2:0` ✔, last version v2.0, Serverless, output 1024 (default)/512/256, max input 8k tokens, text → embedding. Step 1 done (E1).
- 2026-11-18 (owner screenshots, steps 2–3): SG `aws-challenge-vpce-sg` ("Bedrock endpoint", VPC `aws-challenge-vpc`) — inbound HTTPS 443 from `sg-09356f785149eeb60`, no outbound rules, no tags (id to be reported) ✔ (E2); role `aws-challenge-sync-role-q8b1jajy` now has 4 policies: inline `aws-challenge-sync-bedrock-invoke` (created), inline `aws-challenge-sync-rds-connect`, `AWSLambdaBasicExecutionRole-7acc4596-…`, `AWSLambdaVPCAccessExecutionRole-c4201b87-…` ✔ (E3). Endpoint create/delete (steps 4–5) moved into the T04-03 session to avoid a separate paid run.
- 2026-11-25: endpoint created (T04-03 step 6, `vpce-0a78d07830b28e951`, Available) and deleted at the end of the session (owner) — create/delete procedures proven (E4/E5 by owner statement). Status → `Review`.
- 2026-11-25: set to `Done` by the owner (Week 4 closed).
