# Asteris production-readiness checklist

## Controlled BCIT demo

- [x] Use `ASTERIS_ENV=production` for the demo service.
- [x] Keep secrets outside source control; `.env.example` contains placeholders.
- [x] Bind to `127.0.0.1` for a same-machine demo: `python -m uvicorn main:app --host 127.0.0.1 --port 8000`.
- [x] Set a random `ASTERIS_INTERNAL_API_KEY` of at least 24 characters.
- [x] Keep CORS empty for same-origin use; list exact origins if separation is required.
- [x] Verify `GET /health/live` and `GET /health/ready`.
- [x] Confirm production docs are disabled and internal endpoints return 404 without the internal key.
- [x] Confirm rate, body-size, concurrency, timeout, retry, and output-token limits.
- [x] Run focused Phase 9 tests and certified advisor gates.
- [ ] Before the event, make and verify a fresh PostgreSQL backup using the runbook.
- [ ] Confirm the demo network cannot reach raw Uvicorn except through the intended host/proxy.

## Limited pilot

- [ ] Put TLS and a managed ingress/reverse proxy in front of the app.
- [ ] Add shared/distributed rate limiting if more than one process or instance is used.
- [ ] Add PostgreSQL connection pooling sized to the deployment and database limit.
- [ ] Run a disposable-database restore drill and record recovery time/result.
- [ ] Configure centralized log collection, retention, alerts, and an incident owner.
- [ ] Define BCIT-approved student notice, retention, access, deletion, and incident procedures.
- [ ] Define data owner and refresh/re-certification cadence for academic and international facts.
- [ ] Establish a complete schema baseline and migration ledger for fresh environments.
- [ ] Execute load/concurrency testing with mocked OpenAI responses before setting pilot limits.

## Public production

- [ ] Replace the shared internal key with managed service authentication and least-privilege authorization.
- [ ] Use a durable session/account abuse boundary appropriate to public traffic.
- [ ] Add WAF/bot controls, global budget alerts, and provider-side spend caps.
- [ ] Establish high availability, automated encrypted backups, tested recovery objectives, and deployment rollback automation.
- [ ] Complete threat modeling, dependency/vulnerability scanning, penetration testing, privacy/legal review, accessibility review, and institutional operations approval.
- [ ] Define availability, support, incident response, data breach, and academic-content correction processes.

