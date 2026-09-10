# Human Advisor Experience — Phase 2C

Phase 2C used GPT-5.6 Sol with medium reasoning. Astra was not used.

## Decision

**Ready to begin Phase 3 full certification.** All Phase 2C structural, continuity, invalidation, response-discipline, regression, and browser-state gates are closed. This is not the Phase 3 full-corpus certification.

## Results

| Measure | Before | After |
|---|---:|---:|
| Long scenarios structurally stable end-to-end | 0/12 | 12/12 |
| Enhanced long-turn structural checks | 252/264 | 264/264 |
| Return to first program after truncation | 0/12 | 12/12 |
| List-dump failures | 70 | 0 |
| Lexical repetition candidates | 68 | 1 |
| Substantive repetition failures | not separately adjudicated | 0 |
| Unsupported-inference failures | 1 | 0 |
| Directness failures | 65 | 0 |
| Crashes / transport errors | — | 0 |

All 12 live long scenarios completed and all 12 passed the targeted quality gates. One 38-word lexical-overlap candidate remains labeled for human review; it did not repeat a list or unsupported inference.

## Continuity and invalidation

- Return-prior accuracy: 12/12 (100%).
- Comparison continuity: 3/3 (100%).
- Student-fact retention: 4/4 (100%).
- Correction and dependent-conclusion invalidation: 3/3 (100%).
- Stop/resume: 2/2 (100%).
- Family → program → unrelated topic → family/program return: passed.

Structured memory is independent of the browser’s ten-message text window. It stores bounded subject snapshots, comparison sets, user-reported facts with provenance, and concise verified conclusions. Corrections overwrite user facts and invalidate conclusions that depend on them.

## Validation

- Full Python regression: 547/547.
- Browser-state suite: 5/5.
- Phase 2A release gates: 11/11; targeted entity, context, and scope remain 100% across 87 turns.
- Phase 2B response-policy tests: 15/15.
- Phase 2C focused memory tests: 12/12.
- Database content changes: 0.

## Live API usage

Phase total: 752 requests; 4012663 input tokens (1433142 cached, 2530021 cache-write, 49500 uncached); 99373 output tokens; 4112036 total tokens.

Approximate API spend: **$15.41 USD** using the official GPT-5.6 Sol text-token rates recorded in the JSON artifact. Work/Codex credit usage is unavailable in this environment and is not estimated.

The final composite itself corresponds to 174 recorded Sol requests. Earlier diagnostic and targeted repair runs remain included in the phase-total cost rather than being hidden.

## Remaining Phase 3 work

1. Run the frozen 120-scenario full certification once.
2. Human-review the retained LONG-03/8 lexical-overlap candidate.
3. Broaden conclusion-memory certification when additional advising workflows are introduced.

Artifacts are under `human_advisor_benchmark/runs/phase2c_*`. The deterministic run contains the before/after rows, final states, validation ledger, Python results, and browser-state results.
