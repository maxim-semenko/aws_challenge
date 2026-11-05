# INF-01 — Environment configuration

> **BLOCKED** by [Q-03](../RISKS.md#q-03), [Q-07](../RISKS.md#q-07). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | INF — infrastructure as code |
| Milestone | M1 |
| Role | OPS |
| Size | S |
| Depends on | [INF-00](INF-00.md) |
| Blocked by | [Q-03](../RISKS.md#q-03), [Q-07](../RISKS.md#q-07) |
| Unblocks | [INF-02](INF-02.md), [INF-04](INF-04.md) |
| Risks watched | — |
| Goals | — |
| References | ARCH-03 conventions |

## Goal

Account, region and environment name come from configuration, never from code.

## Scope

**In scope**

- CDK context/config for account, region, env
- Naming helper `awsch-<env>-<name>`
- Global tags

**Out of scope**

- Multi-account setup

## Plan

- [ ] Define the config model
- [ ] Apply naming and tags in a base construct

## Definition of Done

- [ ] Switching env/region needs no code change
- [ ] All resources carry the mandatory tags
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
