# Advisor v2 Phase 2 implementation report

## Scope and isolation

Phase 2 adds an experimental browser at `/app-v2` and extends only the existing `/advisor-v2` path. The production `/app` and `/advisor` handlers and browser assets were not changed. Both v2 routes remain absent from `PUBLIC_PRODUCTION_PATHS`, so the existing production middleware hides them unless the internal-route policy authorizes access. There were no migrations, database writes, OpenAI calls, or model benchmarks.

## Conversation state

`AdvisorV2State` remains an explicit, serializable state object. It carries exactly one confidently resolved program or course, a discovery/ambiguity candidate set, the accumulated student assertions, the last question class, and a turn counter.

The experimental endpoint additionally keeps a process-local state cache keyed by an opaque hash of a valid `X-Session-ID`. It is bounded to 256 sessions, expires idle entries after two hours, and returns defensive copies. A request can still supply explicit state for deterministic callers. `reset_conversation` clears cached state, and the browser's **New session** button rotates its session ID.

Context policy:

- Explicit program names, course codes, broad discovery subjects, and unrelated questions reset the active entity before resolution.
- Pronouns and clearly elliptical follow-ups inherit only a previously confident single program or course.
- Discovery and ambiguous candidate sets remain sets; vague follow-ups ask for a program name instead of choosing silently.
- Student fact follow-ups can continue a preceding eligibility evaluation. Changed facts are applied, and conflicting fields are surfaced in diagnostics.
- A failed or unrelated new subject does not fall back to an older entity.

This store is intentionally for local proof-of-concept testing. It is not durable, shared between worker processes, or suitable as a production conversation store.

## Turn observability

Every response now includes an `observability` object, also shown under an expandable **Developer trace** beneath the student-facing answer. It records:

- detected intent and question class;
- entity kind, query, resolution status, candidate IDs/names, score, fuzzy ratio, token overlap, and exact-match flag when available;
- context action (`none`, `inherited`, `reset`, or `preserved_ambiguous`) and inherited entity IDs;
- every retrieval capability and its `found`, `not_found`, `ambiguous`, or `data_unavailable` status;
- deterministic rule-evaluation status;
- student-profile updates and conflicts;
- server/client state source; and
- final response path.

The `/advisor-v2` handler emits the same safe metadata as a structured `advisor_v2_turn` developer log. It does not log the question text or student profile.

## Fuzzy resolution guardrails

Program resolution retains exact-name and exact-ID priority. Weak one-token category inputs such as `technology`, `computing`, `business`, or `engineering` are treated as discovery rather than a single program. Low-relevance input returns `not_found`. Non-exact resolution requires a high score or fuzzy similarity plus separation from the runner-up. A strong misspelling such as `Technlogy Managment` resolves because Technology Management is overwhelmingly ahead. Ambiguous duplicate names such as Civil Technology remain candidate sets.

## Validation completed

- Focused advisor-v2 suite: 11 test methods passed, including the original regression corpus and a deterministic 28-turn torture conversation.
- Compatibility suites: 16 API and production-hardening tests passed.
- Existing browser conversation-state checks: 6 Node tests passed.
- JavaScript syntax validation passed for the new v2 browser client.
- Live PostgreSQL read-only smoke passed for Technology Management resolution, a server-held admission follow-up, admission-rule retrieval, ABOD 1202 course retrieval, and `/app-v2` delivery.
- Live guardrail smoke confirmed `technology` and `computing` stay discovery sets, `Technlogy Managment` resolves to `8350BTECH`, an unknown program is `not_found`, and no model usage is reported.

The longer legacy `test_conversation_state` suite was sampled during validation but not counted above because it did not complete within the validation window and was stopped. No failure was observed before it was stopped.

## Known limitations

- Natural-language interpretation is deliberately rule-based and English-focused; no model reasoning is integrated.
- Profile extraction recognizes a small set of common GPA, grade, credential, graduation, and experience statements. The explicit `student_profile` request object remains the precise input path.
- Candidate thresholds are deterministic heuristics and should be calibrated against a larger real-query set before any cutover.
- Institutional admission decisions are never inferred; these return `human_review_required`.
- Course lookup currently recognizes an explicit department-and-number code. Free-form course-name resolution remains limited.
- `data_unavailable` depends on a caught PostgreSQL error and is kept distinct from `not_found` throughout the answer and trace.

## Local launch and try steps

From `C:\Users\rdubo\Asteris`, with the existing local PostgreSQL settings available:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/app-v2`. Suggested sequence:

1. `Tell me about Technology Management`
2. `What are its admission requirements?`
3. `Am I eligible for it?`
4. `My GPA is 75% and I have 3 years of work experience`
5. `What computing programs are there?`
6. `What about it?`
7. `Tell me about Technlogy Managment`
8. `Tell me about ABOD 1202`

Expand **Developer trace** on each answer to inspect the state decision, resolution candidates, retrieval path, and evaluation status. Use **New session** to start without inherited server state.

Run the focused deterministic checks with:

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v test_advisor_v2
node --test test_conversation_ui.js
```
