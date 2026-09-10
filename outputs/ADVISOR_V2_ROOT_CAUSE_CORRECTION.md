# Advisor v2 root-cause isolation and architecture correction

Date: 2026-09-10  
Scope: experimental `/advisor-v2` and `/app-v2` only. Production `/advisor` and `/app` were not changed. No database writes or migrations were made.

## 1. Common root causes

The failures share three architectural causes.

1. **The old route classified before it understood.** Lexical checks for words such as `programs`, `requirements`, `eligible`, `Red Seal`, and one-token subjects could select a path before the model's semantic proposal was used. Even when Sol ran first in the hybrid wrapper, the inner deterministic router could overwrite or weaken that interpretation. A named program plus student facts phrased as “do I have the requirements” therefore became a requirement summary or Red Seal search instead of eligibility evaluation.
2. **Broad academic discovery searched titles instead of BCIT's taxonomy.** The database already has `programs.area_id -> areas_of_study`. The old v2 code loaded all 374 active programs, scored only title tokens, added a small “computing” synonym set, and returned at most 12. This made one title match look like the institution's complete offering and could never correctly answer an area-of-study request.
3. **Context and response handlers had too much authority.** Memory and special-case handlers could reject an explicit new topic. The current message must establish scope first; memory may only supply a candidate referent for a genuine follow-up. Unsupported broad handlers also caused international nursing, campus, catalog-count, and Red Seal questions to fall into generic program search.

The uploaded transcript also has an important provenance issue. Its exact phrases (“offers … matching programs,” “published Red Seal admission evidence,” “saved topic applies”) occur in `ai_advisor.py`, and its exact timeout text comes from `static/app.js`, which posts to `/advisor` and aborts after 35 seconds. The current `static/advisor-v2.js` posts to `/advisor-v2` and has no client abort. Therefore the uploaded transcript is proven to match the legacy `/app` -> `/advisor` execution path, not the current v2 client. Browser network history was not available, so this is source-level attribution rather than a captured request log.

## 2. Evidence for each failed turn

The read-only before trace is `outputs/advisor_v2_acceptance_before.json`. Before correction, current deterministic v2 treated “Hello” and both campus turns as program resolution; capped computing and engineering discovery at 12; could not resolve broad Red Seal; treated the detailed Construction Management question as requirements and failed entity resolution; rejected Spanish engineering; and routed international nursing to generic title search. Its slowest PostgreSQL-only turn was 361 ms, so the two uploaded 35-second timeouts were not reproduced in current v2 and are attributable to the legacy client/model path, not SQL volume.

Live pre-correction Sol sampling proved that the language model was not the weak link:

- technology -> `program_discovery`, subject `technology`;
- detailed Construction Management profile -> `admission_eligibility`, correct program proposal, grades, credential, and 11 months;
- Spanish `ingenieria` -> engineering program discovery;
- international nursing -> nursing discovery plus international student fact.

The deterministic layer then discarded area scope, used title search, or selected the wrong capability. This is why adding more keywords would have treated symptoms rather than the cause.

## 3. Components removed, bypassed, or rebuilt

- Rebuilt the v2 semantic plan to describe intent, scope, proposed program/course/area, requested facts, explicit student facts, and reference behavior.
- Made a successful Sol plan authoritative for capability selection. Lexical interpretation is now one bounded fallback used only when Sol is unavailable or fails.
- Bypassed title/fuzzy search for broad institutional areas. `list_programs_by_area` confirms a semantic proposal against `areas_of_study` and follows `programs.area_id` in one read-only query, bounded to 100 rows.
- Added read-only capabilities for catalog counts, campus directory, Red Seal admission evidence, and explicit international availability.
- Relegated title search to specific program families or unstructured search after interpretation.
- Rebuilt specific entity confirmation to use both canonical title and credential words, so “Construction Management bachelor’s degree” deterministically selects `8800BTECH` rather than tying with the diploma. Possessive normalization is generic.
- Expanded explicit profile extraction for Red Seal trade, credential average, and months of experience. Red Seal evaluation now checks the stored accepted-trade set rather than treating any non-empty trade as accepted.
- Made the eligibility answer expose the relevant stored pathway and each decisive condition instead of only aggregate counts.
- Expanded v2 observability with per-call model inputs, structured outputs, token usage, phase latency, one-query retrieval timing, row counts, and final response path.

## 4. Why this is a fundamental correction

The correction changes the authority order:

`current message -> Sol semantic plan -> deterministic entity/category confirmation -> one authoritative retrieval/evaluation capability -> PostgreSQL/rule execution -> constrained grounded synthesis`

No transcript sentence has its own answer branch. Spanish works because Sol supplies meaning and the repository confirms the institutional category. Computing works because it follows taxonomy. Construction Management works because question type and named target select eligibility before keywords are considered. Memory never overrides an explicit new subject. The same capability contracts cover paraphrases, objections, repetition, and multilingual wording.

## 5. Exact transcript acceptance results

The finalized uninterrupted live trace is `outputs/advisor_v2_acceptance_final_live.json`. Every turn had successful Sol interpretation and successful constrained synthesis; there were no model fallbacks.

| Turn | First semantic plan | Confirmed execution | Result |
|---:|---|---|---|
| 1 | greeting | no retrieval | bounded greeting |
| 2 | campus directory / count | `get_campus_directory` | 5 campuses and all names |
| 3 | campus directory / details | `get_campus_directory` | all five addresses and descriptions |
| 4 | institution count / technology ambiguity | `get_catalog_counts` | 374 active programs; 8 Bachelor of Technology credentials |
| 5 | institution / program and course counts | `get_catalog_counts` | 374 programs; 3,973 courses |
| 6 | Computing program area | `list_programs_by_area` | all 44 taxonomy-linked programs |
| 7 | institution / Red Seal pathways | `find_red_seal_programs` | 4 programs, credentials, official URLs, caveat about other requirements |
| 8 | Construction Management bachelor eligibility | resolve `8800BTECH`, facts, `evaluate_admission` | `unmet`; English, electrician Red Seal and 70% certificate are met; Math 55% is below 60%; 11 months is below one year; pre-entry assessment/applicability details remain explicit |
| 9 | Construction Management bachelor requirements | resolve `8800BTECH`, `get_admission_rules` | all stored common requirements and four routes |
| 10 | Spanish Engineering program area | `list_programs_by_area` | all 51 Engineering taxonomy rows |
| 11 | Engineering program area | `list_programs_by_area` | all 51 rows |
| 12-17 | Computing & IT program area, including objection and repeats | `list_programs_by_area` each time | all 44 rows every time; no stale-context rejection and no timeout |
| 18 | international availability / nursing family | `get_international_availability` | 15 published available and 1 published unavailable active nursing-family program |

The current database count is 3,973 active courses, not the earlier reported 3,976. The active-program count remains 374. The result intentionally reports current PostgreSQL authority rather than preserving an older claim.

One data-quality observation is preserved rather than hidden: the current `COMP` taxonomy includes `Advanced Forensic Nurse Examiner`. V2 correctly reports the curated relation; changing that classification was outside this no-write architecture pass.

## 6. Automated tests

- Added `advisor_v2_failed_acceptance.json` with every uploaded user turn in order.
- Added five permanent tests covering the complete sequence, weak-keyword eligibility hijacking, an explicit Spanish topic switch, a multilingual Sol-style semantic plan without language packs or model fact authority, bounded taxonomy retrieval, one-query tracing, and latency.
- Focused v2 suite: 45 tests passed.
- Full repository: **636 tests passed** in 760.683 seconds.
- Browser state suite: **6 tests passed**.
- Production isolation remains enforced: `/advisor-v2` and `/app-v2` are not public production paths; `/advisor` and `/app` were unchanged.

## 7. Live Sol telemetry and spend

Final uninterrupted acceptance run:

- model: `gpt-5.6-sol`, reasoning `medium`, strict structured outputs, `store=False`;
- 36 calls (18 interpretation + 18 constrained synthesis);
- 40,645 input tokens, of which 37,176 were cached; 5,932 output tokens;
- estimated cost: **US$0.147386**;
- mean complete-turn latency: 9.142 s; maximum: 15.254 s;
- maximum interpretation phase: 12.230 s; maximum synthesis phase: 5.217 s;
- no fallback, refusal, timeout, or schema failure.

All successful live validation performed during this investigation, including pre-change isolation samples, schema smoke tests, the first acceptance run, the focused live retest, and the final run:

- 81 successful calls;
- 89,881 input tokens, of which 72,009 were cached; 13,573 output tokens;
- 17,872 uncached input tokens;
- estimated total: **US$0.371752** using $4.00/M uncached input, $0.40/M cached input, and $20.00/M output.

One request was rejected by the API before generation because an intermediate schema used arbitrary dictionaries; it returned no usage telemetry. It is excluded from the token and cost total and explicitly remains unavailable rather than being guessed.

Official price source checked 2026-09-10: https://developers.openai.com/api/docs/models/gpt-5.6-sol

## 8. Honest retest recommendation

The architecture and exact API sequence are live-verified. Before treating v2 as ready for a human acceptance sign-off, repeat the transcript manually in `/app-v2` to inspect readability and scrolling of the 44- and 51-program lists. Keep v2 experimental until that browser-level human check is accepted. Do not infer that this pass fixed the legacy production `/advisor`; it was deliberately left unchanged.
