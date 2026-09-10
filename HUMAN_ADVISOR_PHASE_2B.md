# Human Advisor Experience — Phase 2B

Runs: `phase2b_sol_medium_certified_20260908`, `phase2b_comparison_final_20260908`, `phase2b_flow06_final_20260908`

Advisor responses used GPT-5.6 Sol with medium reasoning. Astra was not used.

The fixed targeted subset contains 18 scenarios and 88 turns. Metrics below are model-free text heuristics, not model-judge rubric scores.

## Release language gates

- PASS — CAT-04-B/3: Diploma award is not conditioned on later Level 5/BEng continuation.
- PASS — FLOW-02/3: Family follow-up returns to the complete Nursing family.
- PASS — FLOW-02/4: International comparison distinguishes conditional specialty programs from the full-time BSN.

## Before and after

| Measure | Baseline failures | Phase 2B failures | Change |
|---|---:|---:|---:|
| List Dump | 26 | 2 | -24 |
| Repetition | 17 | 9 | -8 |
| Unsupported Inference | 1 | 0 | -1 |
| Directness | 18 | 10 | -8 |
| Naturalness | 10 | 0 | -10 |
| Structural | 16 | 0 | -16 |

## Validation

| Check | Passed | Failed | Errors |
|---|---:|---:|---:|
| Focused Response Quality | 14 | 0 | 0 |
| Benchmark Harness | 30 | 0 | 0 |
| Phase2A Release Gates | 11 | 0 | 0 |
| Targeted Live Turns | 88 | 0 | 0 |
| Full Python | 534 | 0 | 0 |
| Browser State | 5 | 0 | 0 |

The recorded live model events contain only `gpt-5.6-sol` with medium reasoning. The representative before/after answers are saved in `representative_transcripts.json` in the certified run directory.

## Implementation

- Added intent-based response depth and progressive disclosure.
- Added concise direct-answer, repetition, uncertainty, and frustration guidance.
- Enforced the evidence boundary between an earlier credential award and later progression requirements.
- Made comparisons load exact program records and synthesize supported differences.
- Preserved comparison, program, and course context through follow-up turns, including null-path handling.

## Interpretation

1. CAT-04-B/3 and both FLOW-02 language gates are closed on the live Sol Medium subset.
2. Unrequested list-dump failures fell from 26 to 2 (24 fewer; +27.28 pass-rate points).
3. Unsupported-inference heuristic failures fell from 1 to 0.
4. Directness gained +9.09 pass-rate points and naturalness gained +11.36, while all 88 targeted structural assertions passed.
5. Comparison answers now synthesize stored differences, and both frustration scenarios answer substantive questions while treating clear stops briefly.
6. No Phase 2A structural gain was lost: entity resolution, context retention, and scope accuracy remain 100%, with all 11 release gates passing.
7. Asteris is ready to begin Phase 2C long-conversation hardening; the remaining heuristic candidates are listed in the JSON artifact.

Academic facts still come from deterministic tools and the governed database. The targeted run does not replace Phase 3 certification.

## Phase 2C remaining work

- Harden full-session recall beyond the browser's ten-message history window.
- Test return-to-prior-subject behavior across several topic switches.
- Add compression or structured memory for prior advisor conclusions, not only entity state.
- Run the expensive full certification only after long-conversation hardening is complete.
