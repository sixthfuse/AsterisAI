# Asteris security and operations

## Security boundary

The student browser uses only `POST /advisor`, static assets, and public liveness/readiness checks. In production, raw catalog, curriculum, rules, eligibility, progression, and advisor-engine endpoints are hidden unless the caller supplies the configured internal API key. This shared-key boundary is adequate for a controlled demo and operational diagnostics; it is not an institution role or account system.

Production disables OpenAPI/Swagger/ReDoc. Trusted hosts are explicit. CORS is off unless explicit origins are configured, and wildcard origins are rejected. Keep the application behind TLS and an ingress or reverse proxy. Do not expose Uvicorn directly to the internet.

Requests are limited to 64 KiB. Questions, history messages, history count, completed-course count, and identifiers have schema bounds. Advisor traffic has a per-session/IP sliding-window limit and a process-wide concurrency ceiling. These controls protect a single process. A multi-instance public service needs an ingress or shared-store rate limiter.

## Secrets and rotation

Secrets come from environment variables. `.env` is ignored and `.env.example` contains placeholders only. Logs never include bodies, questions, conversations, credentials, raw IP addresses, or internal keys.

To rotate a secret:

1. Create the replacement in the provider or deployment secret store.
2. Update the deployment secret without committing it to the project.
3. Restart one instance and verify `/health/ready` plus one authorized smoke request.
4. Complete the rollout, then revoke the old secret.
5. Review structured logs for authentication or dependency errors.

Rotate `OPENAI_API_KEY`, `DB_PASSWORD`, and `ASTERIS_INTERNAL_API_KEY` independently. A repository scan found environment lookups and field names, but no hardcoded OpenAI key or database password. The current local `.env` values were never printed. Because the project has no Git metadata in this directory, historical-secret exposure cannot be assessed here.

## Failure behavior

| Failure | Safe behavior |
|---|---|
| OpenAI timeout | HTTP 504, concise retry message, prior browser state retained |
| OpenAI quota/rate limit/unavailability | HTTP 503 with bounded retry guidance; no fabricated academic answer |
| PostgreSQL unavailable | Readiness becomes 503; data endpoints return a generic 503 |
| Malformed academic record | Existing deterministic evidence checks fail closed or mark evidence unavailable; no data was altered in Phase 9 |
| Missing optional evidence | Advisor states the evidence is unavailable and preserves the human-confirmation boundary |
| Browser loses connection | The current conversation remains in memory; retry is possible; a 35-second browser timeout prevents indefinite waiting |
| Server restarts | The stateless server can restart without corrupting session data; an in-flight call fails safely; browser-held state can be retried |

Conversation state exists in the browser and is submitted with each request. The service does not persist student conversations or student records. Structured logs contain opaque session hashes and operational metadata. A page refresh currently clears browser conversation state. A pilot must define retention, access, incident response, and legal/privacy requirements with BCIT; these technical controls do not establish regulatory compliance.

## PostgreSQL backup and recovery

Create an encrypted, access-controlled custom-format backup from a trusted operations host:

```powershell
pg_dump --format=custom --no-owner --no-acl --file asteris_YYYYMMDD.dump $env:ASTERIS_DATABASE_URL
pg_restore --list asteris_YYYYMMDD.dump
```

Validate restore only into a newly created disposable database, never the authoritative database:

```powershell
createdb asteris_restore_test
pg_restore --exit-on-error --clean --if-exists --no-owner --dbname asteris_restore_test asteris_YYYYMMDD.dump
psql --dbname asteris_restore_test --command "SELECT COUNT(*) FROM programs WHERE UPPER(status)='ACTIVE'; SELECT COUNT(*) FROM courses WHERE UPPER(status)='ACTIVE';"
```

Compare the restored counts and certification invariants with the release record, run focused catalog integrity tests, record the backup hash/date/operator/result, then delete the disposable database under the normal operations approval process. No destructive restore was run in Phase 9.

The numbered SQL files are ordered migration history, but the project lacks a complete migration runner/ledger and files 001–003 are absent from this directory. For a fresh public environment, provision a schema baseline, apply 004–024 in order, and record each checksum in a deployment-controlled migration ledger. Several historical SQL files do not contain explicit `BEGIN/COMMIT`; apply them only through a transaction-aware release procedure.

## Monitoring and rollback

Structured JSON logs record request ID, opaque session ID, endpoint, method, status, latency, outcome, model, token usage, and error class. Alert on readiness failures, repeated 429/503/504 responses, error-rate or latency increases, and unusual token use. Do not enable request-body logging at the proxy.

For rollback, restore the prior application artifact and configuration, verify readiness, and run the focused smoke gates. Database changes must use a separately reviewed forward migration or a verified backup in a disposable environment first. Phase 9 made no database or catalog changes.
