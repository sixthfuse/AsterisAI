# Advisor v2 — last incremental conversational-core correction

Date: 2026-09-10  
Decision: **GO for owner retest in `/app-v2`**  
Final browser build: `bcdd50ff8257fcd7`

## Outcome

The advisor no longer treats capability output as the answer. Each turn now has
an explicit task plan, context-first referent resolution, bounded evidence
selection, answer-shape policy, grounded Sol synthesis, and post-generation
validation with a deterministic fallback.

The 445-line owner transcript was the primary failure benchmark. Its systemic
failures are covered as reusable operation/state regressions rather than exact
transcript-string branches.

Production `/advisor` and `/app` were not changed. PostgreSQL remained read-only;
there were no migrations or database writes.

## Conversational core

1. **Task plan:** operation (`list`, `count`, `select`, `filter`, `compare`,
   `details`, `eligibility`, `clarify`, `follow_up`), subject/category,
   constraints, referent, answer shape, and correction flag are recorded on
   every turn.
2. **Durable result state:** recent result objects retain program IDs, names,
   credentials, delivery fields, URLs, and international status. The planner
   receives a bounded projection of these objects.
3. **Context-first resolution:** exact prior names/codes, ordinals, unique
   credentials, filtered prior results, and the active program ID are resolved
   before global fuzzy search.
4. **Necessary retrieval:** contextual selection reuses verified prior evidence;
   exact program international availability uses a one-program capability.
   Broad discovery preserves the full result set in state but sends a concise
   grouped answer rather than printing it.
5. **Answer shape:** broad Engineering/Computing requests use grouped summaries;
   explicit `all/every/complete` requests are exhaustive; a unique unavailable
   item is a single answer; normal international discovery is a short summary;
   exact details are bounded and include a URL only when requested.
6. **Grounded synthesis:** Sol writes natural prose only from compact evidence
   objects. Claim IDs, deterministic status preservation, number provenance,
   URL provenance, and requested-link policy are checked after generation.
   Failure returns the deterministic bounded answer.
7. **Eligibility authority:** the existing deterministic rule evaluator remains
   authoritative. Natural synthesis cannot change its status. The fallback now
   reports blockers and unresolved checks instead of dumping every passing rule.

## Observability

Each result records the task plan, referent source, selected evidence objects,
answer-shape decision, synthesis input/result/usage, grounding result, fallback
reason, retrieval capabilities, rule status, runtime build, and response source.
No hidden chain-of-thought is logged.

Runtime provenance was renamed to:

- route: `advisor-v2.conversational-core.v2`
- mode: `task_plan_context_first_grounded_synthesis`

## Regression coverage

Reusable variants cover:

- selecting the one unavailable nursing program from prior results;
- resolving `this program` after `8875bsn`;
- resolving the unique master's degree from Computing results;
- exact pasted result names beating fuzzy global matches;
- `follow up` not becoming a literal program search;
- grouped Engineering/Computing discovery versus explicit exhaustive listing;
- question-shaped international availability with no unsolicited URLs;
- deterministic, concise Construction Management eligibility;
- complete conversational-core observability.

Verification results:

- full Python suite: **649 passed**;
- final targeted conversational-core/runtime suite: **13 passed**;
- browser-state suite: **6 passed**.

## Real route and browser-equivalent validation

### Real HTTP `/advisor-v2`

A fresh Sol-enabled server replayed a nine-turn compressed equivalent of the
445-line failure sequence. Build `13c6c9e5d8e53193` passed every check on one
runtime with no synthesis fallback:

- Engineering returned a seven-line grouped summary, not 51 program rows;
- Nursing returned a concise availability summary with no URLs;
- `which one` selected only `8875BSN`;
- `this program` used the active program ID and one-program availability lookup;
- `the master's degree` resolved to `M600MSC`;
- the pasted Applied Computing name resolved to `M600MSC`;
- Construction Management used `evaluate_admission` and returned the exact
  deterministic `unmet` status in concise natural prose.

The only subsequent code changes were prior-evidence verification metadata and
the runtime provenance label; both were covered by the final targeted suite.

### Real `/app-v2` UI

The actual browser UI was exercised on final build `bcdd50ff8257fcd7`:

1. `As an international student, which nursing programs can I apply to?`
2. `Which one is unavailable to international applicants?`

The first answer was a concise four-example summary. The second answer contained
only the full-time BSN and the UI displayed `turn 2 · grounded`. The server trace
showed `reuse_prior_result` from durable conversation state. This demonstrates
the real page, JavaScript client, server session, route, evidence reuse, Sol
synthesis, and grounding status together.

## Live Sol usage and calculated spend

All implementation/certification live work in this correction:

- API calls: **69** (two model calls per normal turn, plus one isolated synthesis diagnostic)
- input tokens: **97,096**
- cached input tokens: **65,930**
- uncached input tokens: **31,166**
- output tokens: **16,329**

Using the official GPT-5.6 Sol rates current on 2026-09-10 — $4/M uncached
input, $0.40/M cached input, and $20/M output — calculated spend is:

- uncached input: **$0.124664**
- cached input: **$0.026372**
- output: **$0.326580**
- total calculated estimate: **$0.477616 USD**

Provider-reported actual dollar spend is not exposed by the response objects;
the token counts are actual response usage and the dollar figure is calculated.

The passing nine-turn core certification plus final-build two-turn browser run
used 22 calls, 31,763 input tokens (23,958 cached), and 5,246 output tokens,
for a calculated **$0.145723 USD**.

## Files changed

- `advisor_v2.py` — task/state model, referent resolution, evidence reuse,
  answer shaping, bounded fallbacks, one-program availability retrieval,
  observability, grounding integration.
- `advisor_v2_sol.py` — expanded task schema, natural evidence-bounded synthesis,
  deterministic grounding validator.
- `main.py` — accurate conversational-core runtime provenance.
- `test_advisor_v2_conversational_core.py` — reusable operation-level regressions.
- `test_advisor_v2_runtime_parity.py` — updated runtime identity assertion.
- `advisor_v2_conversational_acceptance.py` — compressed real-route certification replay.

## Known limitations

- Natural phrasing varies between Sol calls, while facts and status remain bounded.
- Broad taxonomy can contain surprising but database-authoritative category members;
  this layer groups them but does not rewrite institutional taxonomy.
- The validator is deliberately conservative for numbers, URLs, and deterministic
  statuses; unsupported free-form claims fall back rather than receive a second
  paid repair attempt.
- Final owner judgment is still needed for tone preferences, but not to substitute
  for technical validation.

## Go / no-go

**GO for owner retest of `/app-v2`.** The hard stopping criterion was not met:
the final real browser path did not dump the capability dataset, lose the
referent, let fuzzy matching beat context, choose the wrong answer shape, or let
capability formatting dictate the final answer. If owner retesting shows those
same systemic classes again, stop incremental repair and perform the radical
advisor-orchestration reset while preserving PostgreSQL, rules, and retrieval
primitives.
