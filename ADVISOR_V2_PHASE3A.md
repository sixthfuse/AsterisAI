# Advisor v2 Phase 3A implementation report

## Scope and route isolation

Phase 3A changes only the experimental `/advisor-v2` and `/app-v2` path. The
production `/advisor` and `/app` handlers and assets are unchanged. The v2 paths
remain excluded from `PUBLIC_PRODUCTION_PATHS`. No migration, database write, or
cutover is included.

The runtime pipeline is:

1. a bounded GPT-5.6 Sol structured interpretation;
2. deterministic program/course confirmation and PostgreSQL retrieval;
3. deterministic admission-rule evaluation; and
4. a bounded GPT-5.6 Sol presentation plan rendered from exact deterministic
   answer lines.

`ASTERIS_ADVISOR_V2_SOL=0` disables the language boundary and returns exact Phase
2 behavior. The language layer also remains disabled when no usable API key is
configured.

## Model configuration and schemas

Both calls use the Responses API structured parsing surface with
`gpt-5.6-sol`, medium reasoning, `store=False`, no tools, bounded output, and the
existing timeout/retry settings.

The interpretation schema is strict (`extra=forbid`) and carries:

- intent and question class;
- proposed program, subject-area, and course references;
- only current-message grades, credentials, work experience, high-school state,
  and international/domestic status that the student explicitly supplied;
- follow-up/reference behavior, including an optional candidate ordinal; and
- whether clarification is needed and why.

The model sees only the current message plus a compact state projection: active
kind, confirmed program/course IDs, at most ten candidate IDs, and the last
question class. It does not receive a transcript, rule corpus, or database dump.
An explicit newly interpreted subject prevents old context from being inherited.

The synthesis schema contains only an allow-listed opening, the complete ordered
set of deterministic fact-line IDs, and an allow-listed closing. The renderer
rejects missing, duplicated, invented, or reordered fact IDs. It inserts the
exact deterministic lines rather than model-written factual prose. Ungrounded
responses cannot receive a “verified records” opening, and status-sensitive
closings are accepted only for matching deterministic paths.

## Authority and guardrails

Model program and course strings are proposals. `resolve_program`,
`get_course_facts`, or an exact candidate-ID facts lookup must confirm them from
the repository before they become active context. Discovery and ambiguity remain
sets; the model cannot silently select an entity except for an explicit ordinal
within the deterministic candidate list, which is then confirmed by facts lookup.

Extracted student assertions are merged into `StudentProfileV2`, with changed
fields and conflicts exposed in the trace. They are inputs to the existing rule
tree evaluator. The evaluator remains the sole authority for `met`, `unmet`,
`missing_student_information`, `human_review_required`, and evidence-unavailable
outcomes. International status is retained as a user assertion but does not
create an unstored eligibility rule.

Retrieval statuses (`found`, `not_found`, `ambiguous`, and `data_unavailable`),
verification evidence, rule results, and the deterministic response path are not
modifiable by synthesis.

## Failure behavior

Interpretation timeout, transport error, refusal, parse error, or schema failure
runs the exact Phase 2 deterministic turn and skips synthesis. A synthesis error,
schema failure, disallowed closing, or fact-set mismatch returns the exact
deterministic answer already produced. Errors are exposed only by safe exception
class in the trace; hidden reasoning is never requested or logged.

## Observability

The `/app-v2` developer trace includes the compact interpretation payload and
strict result, entity proposals beside deterministic confirmation, inherited or
reset context, retrieval actions and statuses, profile updates/conflicts,
evaluator outcome, structured synthesis inputs and plan, final deterministic
path, and final response source. Operational logs retain safe structured metadata
and aggregate token counts, not the student message, profile, prompts, model
reasoning, or full trace.

## Regression coverage and model footprint

`advisor_v2_phase3a_golden.json` contains 50 questions across messy language,
discovery, exact lookup, misspellings, ordinary/ordinal/diploma follow-ups, abrupt
switches, partial and conflicting facts, international and course questions,
misinformation, exceptions, ambiguity, unknowns, clarification, retrieval
failure, and model failure.

`test_advisor_v2_phase3a.py` validates the golden schema and categories plus the
full mocked boundary: Sol/medium pinning, structured parse, no response storage,
proposal confirmation, ordinal confirmation, context reset, deterministic
evaluation, conflict capture, safe synthesis, and both fallback stages. It makes
no live OpenAI calls.

## Local use

From `C:\Users\rdubo\Asteris`, configure PostgreSQL and a local `OPENAI_API_KEY`,
then run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/app-v2` and expand **Developer trace** after a turn.
Set `ASTERIS_ADVISOR_V2_SOL=0` before launch to exercise deterministic fallback.

Run the focused tests with:

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v test_advisor_v2_phase3a test_advisor_v2
node --test test_conversation_ui.js
```

Each model-enabled v2 turn normally makes two calls: one interpretation and one
synthesis plan. Aggregate token usage is returned and logged. No paid/live calls
were needed for implementation or regression validation.

## Limitations

- The synthesis stage intentionally cannot paraphrase factual lines; safety is
  favored over stylistic freedom.
- Model-extracted facts are assertions, not verified student records.
- Candidate ordinal handling depends on the bounded prior candidate list.
- The in-process session store remains non-durable and non-shared.
- Model quality has been tested with mocks and a manual golden corpus, not a paid
  live benchmark.
