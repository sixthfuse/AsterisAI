# Human Advisor Experience — Phase 2A: Deterministic & State Hardening

Status: **implementation and deterministic validation complete; live Sol language validation blocked by exhausted API credits**. Date: 2026-09-08.

The work used **GPT-5.6 Sol Medium**. Astra was not used. The attempted live run was configured with `gpt-5.6-sol` and medium reasoning; no language judge ran.

## Result

Phase 2A fixed the targeted deterministic root causes in prerequisite rendering, course identity finalization, academic-scope evidence binding, null-path handling, program-family completeness, credential disambiguation, topic continuity, comparison state, long-history state, and stop routing.

The model-free targeted replay contains 18 scenarios and 87 turns. It uses the frozen Phase 1 transcripts for the baseline and replays the same structural expectations against the Phase 2A resolver and deterministic output gates.

| Targeted structural measure | Frozen Phase 1 | Phase 2A | Change |
|---|---:|---:|---:|
| Scenarios passing every structural check | 11/18 (61.11%) | 18/18 (100.00%) | +38.89 points |
| Turns passing every applicable structural check | 68/87 (78.16%) | 87/87 (100.00%) | +21.84 points |
| Entity resolution | 59/71 (83.10%) | 71/71 (100.00%) | +16.90 points |
| Context retention | 57/68 (83.82%) | 68/68 (100.00%) | +16.18 points |
| Scope accuracy | 73/87 (83.91%) | 87/87 (100.00%) | +16.09 points |
| Deterministic release gates | — | 11/11 | all passed |

These are structural checks, not model-language rubric scores. They establish that the correct subject, scope, state, and deterministic evidence reach the answer layer. They do not prove that every generated answer is concise, natural, or perfectly worded.

## Root causes fixed

1. **Prerequisite semantics.** Prerequisite retrieval now includes group identity, operators, condition parameters, and descriptions. The renderer preserves AND/OR relationships and non-course conditions. LIBS 7001 now shows its three valid OR routes, and CMGT 8700 retains program-completion exceptions, work experience, topic, and sponsor conditions instead of producing `None` values or treating years as a grade.

2. **Course-code identity.** Finalization first normalizes exact internal IDs. It adds a code to a bare title only when the collected evidence identifies one course unambiguously. It also refuses substring matches inside a different, longer course title and does not add a second code to an already coded title. Frozen source replays pass for CAT-06-A/1, CAT-06-B/3, and FLOW-31/2 with zero unrelated codes inserted.

3. **Academic scope binding.** Structured state now carries admission, international, progression, or graduation scope. Program details expose early credential-award evidence separately from later-level progression requirements. Civil Engineering evidence states that the diploma follows successful completion of the first two academic years, while the Level 5 requirements govern continuation into the BEng years.

4. **Null pathway and family completeness.** `get_program_level_courses` safely asks for a program when no program/pathway is active instead of dereferencing null. Family discovery generically unions active catalog-name matches with governed family relationships. A broad Nursing query now returns all 28 active Nursing-family records, including the relevant advanced certificates; the specialty subset contains 27 and excludes the main BSN.

5. **Credential disambiguation.** Same-name choices include credential labels. Replies such as `associate certificate`, `certificate`, `diploma`, `bachelor`, and `master` filter the current candidate or comparison set. FLOW-07 now resolves the Civil Technology associate certificate to `5430ACERT` and a later explicit certificate correction to `5430CERT`.

6. **Topic continuity.** A course named inside an active program discussion no longer discards the program subject. A verified unique program search is promoted into active state for informal follow-ups. Explicit new subjects still replace stale state.

7. **Comparison and long-history state.** Structured state stores comparison program IDs, prior program IDs, and reported completed course IDs. FLOW-06 retains `7710DIPMA` and `8800BTECH` across the ambiguous “other one” follow-up and resolves “the diploma” correctly. Three-way comparisons remain intact. Prior programs and student-reported courses survive beyond the browser's ten-message text window without reconstructing facts from stale prose.

8. **Stop and frustration routing.** Plain and compound stop phrases now stop without retrieval. A compound phrase that also contains a concrete academic request continues to the request, so “Never mind, tell me about 9940BSC” is not swallowed.

## Failure accounting

The targeted failure map contains **15 baseline deterministic failure-turn labels** and **5 mixed labels**. All 15 targeted deterministic labels now pass their applicable structural checks and release gates. The deterministic contributor was corrected for all 5 mixed labels, including Nursing family completeness, comparison continuity, and the LONG-07 state/crash path; their final language quality could not be re-scored.

Across the full Phase 1 benchmark, 112 turns were labeled deterministic. The 97 labels outside this targeted set were not individually re-adjudicated, even though some share the generalized fixes. They must not be counted as still failing or as fixed without a future targeted or full replay.

Of the 10 source-confirmed critical Phase 1 findings:

- **7 deterministic findings are fixed:** FLOW-13/1, CAT-06-A/1, CAT-06-B/3, FLOW-03/1, FLOW-09/2, FLOW-29/4, and FLOW-31/2.
- **2 mixed findings have their deterministic retrieval defect fixed but need generated-answer verification:** FLOW-02/1 and FLOW-02/3.
- **1 model-language finding remains a release risk:** CAT-04-B/3. The evidence boundary is now explicit, but a live Sol answer must demonstrate that it does not attach Level 5 continuation rules to the earlier diploma award.

There were **0 deterministic replay crashes or errors**. The saved live Sol attempt started 4 of 18 scenarios and received 4 `credit_balance_exhausted` errors before the circuit breaker stopped the remaining 14. It produced 0 successful turns, so no post-change factual, naturalness, or other language rubric rate is available. No Astra fallback was used.

## Validation

| Validation | Pass | Fail | Error |
|---|---:|---:|---:|
| Focused deterministic/state/routing regressions | 20 | 0 | 0 |
| Phase 2A structural turns | 87 | 0 | 0 |
| Phase 2A structural scenarios | 18 | 0 | 0 |
| Release gates | 11 | 0 | 0 |
| Full Python regression suite | 520 | 0 | 0 |
| Benchmark-tool tests (included above, rerun separately) | 30 | 0 | 0 |
| Browser-state suite | 5 | 0 | 0 |
| Live Sol target attempt | 0 | 0 | 4 quota errors |

No regressions were found. The Phase 1 and Phase 2A database snapshots have the same SHA-256 hash, `c8833accc12d28cb5911fe8d7e49652abdff3a503f1ca34caae061c089572cd5`. Certified contents remain 374 active/governed programs and 3,976 active courses. No academic or international data was changed.

## Remaining Phase 2B work, ranked

1. Verify scope-safe explanation language, beginning with CAT-04-B/3 and the two FLOW-02 mixed findings.
2. Reduce list dumping and repetition; the frozen baseline failure rate is 21.70%.
3. Improve directness and naturalness; the frozen baseline mean is 3.168/4.
4. Improve comparison synthesis after the deterministic set is preserved.
5. Give useful next steps without appending generic boilerplate.
6. Reduce unsupported inference; the frozen baseline failure rate is 7.23%.
7. Improve wording when frustration and a substantive academic question occur together.
8. Recheck complete long conversations for answer quality now that structured state survives the text window.

## Phase 2B readiness

The system is ready to begin Phase 2B implementation with **GPT-5.6 Sol Medium**. Deterministic and state prerequisites for that work are in place, and the full regression suites are clean. Release certification is not complete: when Sol API credits are available, rerun the saved 18-scenario target and score its generated answers before declaring the critical language gates closed. A full 636-turn rerun is not warranted until the Phase 2B language changes are complete.

## Artifacts and changed files

- `HUMAN_ADVISOR_PHASE_2A.md`
- `HUMAN_ADVISOR_PHASE_2A.json`
- `human_advisor_benchmark/runs/phase2a_deterministic_20260908/`
- `human_advisor_benchmark/runs/phase2a_sol_medium_20260908/`
- Production: `advisor.py`, `ai_advisor.py`, `conversation_state.py`
- Regression coverage: `test_ai_advisor.py`, `test_conversation_state.py`, `test_conversation_results.py`, `test_main_nursing.py`
- Target validator: `human_advisor_benchmark/phase2a_validate.py`
