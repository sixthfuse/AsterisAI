# Advisor v3 implementation and certification report

Date: 2026-09-10  
Certified build fingerprint: `1804d992c4b72f7c`  
Model boundary: `gpt-5.6-sol`, Medium reasoning  
Decision: ready for owner testing on `/app-v3`; do not promote to `/app` or `/advisor` yet.

## Outcome

An isolated advisor v3 is implemented end to end on `/advisor-v3` and `/app-v3`. It uses one turn pipeline:

`classify → strict semantic plan → referent resolution → typed operation compilation → deterministic execution → evidence-only synthesis → grounding → deterministic state transition`

Production `/advisor` and `/app` were not changed. The production public-path allowlist was not expanded, so the v3 experiment remains hidden by existing production middleware. No migration, database write, or catalog mutation was added or run.

## Discarded and retained

The pre-coding classification and reasons are in `outputs/ADVISOR_V3_ARCHITECTURE_RESET.md`.

Discarded: the v2 orchestrator, ordered keyword answer branches, overlapping compatibility intent fields as execution authority, prose-derived state updates, untyped candidate/offer memory, and handlers that bypass a common compiler.

Retained: authoritative PostgreSQL records; curated academic rules; the read-only `AdvisorV2Repository` capabilities behind a v3 adapter; `StudentProfileV2`; and the deterministic admission evaluator. These are low-level retrieval/evaluation primitives only. v3 never calls the v2 turn orchestrator.

## Files

- `advisor_v3.py`: v3 state, deterministic invariant classifier, plan normalization, read-only adapter, referent resolver, compiler, executor, typed evidence, fallback answers, grounding, transition, and developer trace.
- `advisor_v3_sol.py`: strict Sol plan and evidence-only synthesis schemas, pinned to GPT-5.6 Sol Medium with `store=False`.
- `main.py`: isolated v3 request/session plumbing, routes, diagnostics, build fingerprint, and usage logging.
- `static/advisor-v3.html`, `static/advisor-v3.js`: isolated lab UI using browser-equivalent `X-Session-ID` continuity and developer trace display.
- `test_advisor_v3.py`: real FastAPI-route integration tests with PostgreSQL and session continuity.
- `advisor_v3_certification.py`: bounded real-HTTP/browser-equivalent certification replay.
- `outputs/ADVISOR_V3_ARCHITECTURE_RESET.md`: required pre-implementation design note.

## Typed state and plan

`AdvisorV3State` contains:

- active program/course entities;
- up to eight recent durable result sets, each with a stable ID, authoritative entity IDs, bounded rows, task/category/filter metadata, total, and creation turn;
- unresolved references;
- student profile assertions and per-field provenance/supersession history;
- current task thread;
- prior answer intent and an immediately scoped typed offered action.

`V3SemanticPlan` contains:

- `speech_act`: new task, follow-up, confirmation, correction, clarification, or social;
- typed task, domain, entity/category;
- referent source/value;
- typed filters and prior-result reuse;
- clarification and answer shape;
- explicitly extracted student facts.

The Sol proposal is compiler input, not authority. Deterministically recognized constraints in the current utterance replace same-field model proposals. Exact ID, exact name, current result set, ordinal/credential selection, and active entity resolution precede fuzzy search. Assent is valid only against the immediately preceding typed offer. Social acknowledgement uses a no-op operation and preserves state.

## Operations, evidence, and grounding

The compiler emits a small typed graph including catalog filter, durable-set reuse, exact/fuzzy program resolution, program details, deterministic eligibility, campus directory, family/program international availability, course lookup, Red Seal rule-backed discovery, clarification, and no-op.

Evidence objects carry `evidence_id`, source, entity ID, exact fields, and status. Result sets retain IDs independently of prose. Retrieval is bounded to 100 stored rows per set; current acceptance sets are 44 or fewer and therefore complete.

Sol synthesis receives only the current question, validated plan, typed evidence, deterministic outcome, and fallback answer. Grounding rejects unknown evidence IDs, unsupported numbers, entity IDs, URLs, changed eligibility status, and unrequested links. Rejection returns the deterministic answer. State transition uses the plan, resolution, executed outputs, evidence, and evaluator result—never generated prose.

Every response includes the requested developer trace: build fingerprint, speech act, plan, referent resolution, compact state read, state write diff, operation graph, evidence IDs/count, evaluator result, planner/synthesis modes, grounding result, and fallback reason. It contains no hidden reasoning.

## Acceptance results

The final 11-turn real-HTTP replay used one browser-equivalent session against an actual Uvicorn server. `/app-v3`, its JavaScript, diagnostics, and every `/advisor-v3` request returned HTTP 200.

1. `computing`: 44 authoritative Computing & IT IDs; concise credential grouping.
2. `sure`: confirmation, `reuse_result_set`, exhaustive 44-item answer; no literal search.
3. `list all 44 programs`: same durable IDs, exhaustive 44-item answer.
4. Construction Management eligibility: resolved `8800BTECH`; deterministic status `unmet` (English 60 < 73, Foundations of Math 11 at 55 < 60, and 11 months < one year among the unmet modeled requirements).
5. broad master's request: fresh five-program credential-filtered result set; stale Construction Management entity cleared.
6. correction: remained a broad master's filter and returned the same five genuine master's-credential records.
7. computing master's: exactly one durable result, `M600MSC`, which became active.
8. `m600msc`: exact-ID resolution before search.
9. praise: social no-op; `M600MSC` and academic result state preserved.
10. campus count: five active campus-directory records.
11. nursing unavailable internationally: one evidence record, one durable ID (`8875BSN`), concise explicit unavailable status, and `8875BSN` active.

Additional deterministic real-route tests passed Construction Management same-name credential clarification, exact pasted nursing name, `this program` after selection, Engineering and aviation broad discovery, and rule-backed Red Seal discovery.

## Tests

- Full Python suite: **653 passed**, 0 failed, 761.544 seconds. Sol was disabled for this run to prevent bulk calls.
- Browser-state JavaScript suite: **6 passed**, 0 failed.
- Focused v3 integration suite is included in the 653 and drives the real route with browser headers and server-side session continuity; it does not test helpers alone.
- Final live actual-HTTP certification: **11/11 turns grounded and structurally accepted**.

## Live Sol usage and spend

Final certified replay, exact response usage:

- calls: **19**;
- input tokens: **22,764**;
- cached input tokens: **16,307** (included in the provider's input-token field);
- output tokens: **3,489**;
- model/reasoning: GPT-5.6 Sol / Medium.

The provider responses did not report monetary spend, and the project has no authoritative GPT-5.6 Sol price table, so:

- provider-reported spend: **unavailable**;
- computed cost: **not computed** (no price was guessed).

For full transparency, development also used one completed preliminary replay (19 calls; 22,554 input, 0 cached, 3,230 output) and one aborted replay (8 calls). The aborted replay exposed the now-fixed model-filter/result-bound defect; its first four completed turns reported 10,218 input, 0 cached, and 1,330 output tokens, while the failing fifth turn's two-call token usage was lost when the route raised before serialization. Therefore all-development token totals are a known lower bound, not falsely presented as exact: 55,536 input, 16,307 cached, and 8,049 output across 46 calls, plus the unrecorded failing turn's tokens.

## Gaps and recommendation

- v3 deliberately implements the smallest acceptance-complete capability graph. Rich multi-program comparison formatting and comprehensive course/curriculum advising are not yet feature-parity with production.
- Session storage is process-local and bounded; it is suitable for the isolated lab, not a multi-worker production promotion.
- Sol sometimes proposes an unrequested official URL; grounding correctly rejects it and uses the concise deterministic answer. This is visible in `fallback_reason`.
- The final live computing synthesis included a harmless `Status: found` prefix. It is grounded but could be polished later; it is not an architecture or correctness failure.
- Monetary spend cannot be certified until the provider exposes spend or an owner-approved price table is configured.
- The workspace is not a Git checkout, so no Git diff/commit status is available.

The owner should now test `/app-v3` with fresh sessions and adversarial natural follow-ups. Production `/app` and `/advisor` should remain untouched until that owner test and a separate promotion decision.
