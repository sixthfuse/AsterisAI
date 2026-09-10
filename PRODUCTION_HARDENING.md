# Asteris Phase 9 — Production Hardening & Deployment Readiness

## Decision

**Asteris Production Hardening — READY FOR CONTROLLED BCIT DEMO PREPARATION**

The read-only audit found no exposed hardcoded credential in source and no existing cloud deployment target. It found three HIGH risks for any network-exposed build: unlimited model spend, unsafe dependency failures, and unprotected internal endpoints. Those risks are closed for a controlled single-process BCIT demo by the Phase 9 controls below.

## Architecture and startup audit

Asteris is a single FastAPI application serving a static browser client and synchronous PostgreSQL-backed academic tools. `/advisor` routes through `ai_advisor.py`, whose deterministic resolver narrows tool access and whose structured `TopicState` is returned to the browser. The browser retains conversation and state in memory and sends at most ten messages. PostgreSQL is the academic source of truth. The OpenAI Responses API is used only after deterministic/direct-answer paths do not answer the request.

The repository contains pinned runtime dependencies and numbered SQL migrations 004–024. There is no Docker, hosted target, CI deployment definition, universal migration runner, pool, backup automation, external metrics backend, account system, or institutional admin UI. Development remains `python -m uvicorn main:app --host 127.0.0.1 --port 8000`. Production mode fails fast on missing credentials or an inadequate internal key.

## Changes

- Added validated development/test/production configuration and a placeholder-only `.env.example`.
- Added safe request IDs, opaque session identifiers, structured JSON logs, model/token fields, and liveness/readiness endpoints.
- Added 64 KiB body limits, schema bounds, 20 requests/minute default rate limit, four-request advisor concurrency ceiling, 30-second OpenAI timeout, one retry, and 1,200 output-token ceiling.
- Added safe OpenAI quota/timeout/transport/status and PostgreSQL error responses. Failed calls do not advance the browser's saved conversation state and never fabricate an academic answer.
- Hid internal catalog/rules/eligibility/progression/engine endpoints behind a production-only internal key. Production docs are disabled. Trusted hosts and explicit non-wildcard CORS are enforced.
- Reduced raw history replay from 4,000 to 2,400 characters with per-message bounds while retaining durable structured session state. Runtime token usage is now measurable.
- Added focused security/resilience tests and operational, backup, restore, rotation, rollback, privacy, and deployment checklists.

## Severity-ranked residual risks

| Severity | Risk | Owner/action | Blocks |
|---|---|---|---|
| HIGH | Process-local rate limiter does not coordinate multiple instances | Deployment owner: shared/ingress limiter | Multi-instance pilot, public production |
| HIGH | Shared internal key is not role-based authorization | Security/app owner: managed service auth and least privilege | Public production |
| HIGH | Fresh schema baseline and migration ledger are incomplete | Database owner: baseline plus checksum ledger | New pilot environment, public production |
| MEDIUM | PostgreSQL connections are not pooled | Deployment/database owner: size and add pool | Sustained/public traffic |
| MEDIUM | Restore drill not executed in Phase 9 | Database owner: disposable restore verification | Pilot, public production |
| MEDIUM | TLS ingress, WAF, centralized alerts, and budget alarms need a deployment target | Operations owner: configure at target selection | Pilot, public production |
| MEDIUM | Institutional privacy/legal/retention/incident posture is not approved | BCIT owners: complete review | Pilot, public production |
| LOW | Browser state is lost on page refresh | Product owner: decide on recovery UX | Does not block demo |

## Answers to the release questions

1. **Controlled demo blockers:** no known CRITICAL or HIGH blocker remains in the single-process localhost/demo boundary, subject to final tests and a pre-event backup.
2. **Limited pilot:** choose a TLS deployment target; add shared rate limits and a database pool; create a full migration baseline; verify restore; configure centralized monitoring/budget alerts; and complete BCIT privacy/operations review.
3. **Public production:** also replace the shared internal key with managed authentication/authorization, add durable abuse controls and HA/recovery, and complete threat, vulnerability, penetration, privacy/legal, accessibility, and institutional reviews.
4. **Secrets/config:** runtime secrets are environment-driven, ignored by source control rules, validated in production, and excluded from responses/logs. Git history could not be audited because this directory has no `.git` metadata.
5. **Internal endpoints:** hidden by default in production and available with the internal key. This is adequate for the demo; public production needs managed auth.
6. **Dependency failures:** OpenAI and database failures return concise 503/504 responses. Readiness reflects database loss. Browser state survives failed calls and server restarts while the page remains open.
7. **Cost reduction:** no live Phase 9 API spend. Frozen evidence estimates 33.5% less replayed history across representative comparison and long-session follow-ups; first-turn queries are unchanged. Output and retries are bounded without changing the model or academic evidence.
8. **Operations:** privacy-conscious JSON logs, liveness/readiness, model usage fields, backup/restore and rotation runbooks, monitoring expectations, and rollback steps now exist. Target-specific infrastructure remains pending.
9. **Certification regression:** none. Phase 3B blockers pass 17/17, Phase 2C long-memory passes 12/12, the full Python suite passes 574/574, and browser state passes 5/5. The database remains 374 active programs and 3,976 active courses.
10. **Next phase:** yes. Asteris is ready to move to Demo/UI + BCIT Presentation Prep within the controlled-demo boundary.

## Final validation

- Focused Phase 9 security/resilience/configuration: **10/10**.
- Phase 3B release-blocker tests: **17/17**.
- Phase 2C long-memory tests: **12/12**.
- Full Python regression: **574/574**.
- Browser-state suite: **5/5**.
- Production smoke: liveness **200**, readiness **200**, docs **404**, internal endpoint without key **404**, with key **200**.
- Phase 9 live OpenAI usage: **0 requests, 0 tokens, $0**.
- Work/Codex credit use: unavailable; not estimated.
