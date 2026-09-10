# Human Advisor Experience — Phase 3 Full Certification

Phase 3 used GPT-5.6 Sol with medium reasoning for both the live advisor and the evaluator. Astra was not used.

## Decision

**BLOCKED — NOT CERTIFIED FOR BCIT DEMO PREPARATION.**

The full corpus completed reliably and most measured behavior improved substantially, but 18 source-confirmed critical turns remain. The release gate requires zero source-confirmed critical academic errors.

## Full-run result

| Measure | Phase 1 | Phase 3 |
|---|---:|---:|
| Frozen corpus | 120 scenarios / 636 turns | 120 scenarios / 636 turns |
| Weighted score | 89.52 | 95.52 |
| Factual adequacy | 94.08% | 96.16% |
| Entity resolution | 88.68% | 98.58% |
| Context retention | 90.31% | 97.48% |
| Scope accuracy | 90.57% | 97.17% |
| Unsupported-inference rate | 7.23% | 2.83% |
| Repetition/list-dump rate | 21.70% | 1.26% |
| Structural assertions | 615/678 (90.71%) | 672/678 (99.12%) |
| Transport errors | historical failures recorded | 0 |

> Evaluator caveat: Phase 1 was judged by Astra Low; Phase 3 was judged by Sol Medium. The score and language-quality deltas are descriptive. The frozen corpus, expectations, rubric, evidence protocol, and deterministic assertions were preserved; structural metrics are directly comparable.

## Required answers

1. **Change from 89.52:** the Sol-evaluated score is 95.52 (+6.00). Factual adequacy rose to 96.16%, entity resolution to 98.58%, context retention to 97.48%, and scope accuracy to 97.17%.
2. **Source-confirmed critical errors:** yes—18 of 25 judge-critical flags remain critical after frozen-evidence review. Five were downgraded to noncritical, one has conflicting source fields, and one was not confirmed.
3. **Entity/context/scope:** 98.58% / 97.48% / 97.17% under the frozen rubric; deterministic assertions are 672/678 (99.12%).
4. **Repetition/list dumping:** controlled. The rubric adverse rate is 1.26%; model-free checks found 0/264 long-turn list dumps and 0/264 repetition failures.
5. **Unsupported inference:** materially lower by the rubric estimate, from 7.23% to 2.83%, with evaluator caveat. Model-free long-turn checks found 0/264 heuristic failures, but source review still confirmed several unsupported academic claims.
6. **Long conversations:** 12/12 pass end-to-end memory, structure, and response-discipline checks. Strict rubric scenario success is 0% because isolated academic errors remain in several long conversations.
7. **API cost:** 850 requests, 7,948,592 total tokens, approximately $37.39. Advisor: $14.25; evaluator: $23.14.
8. **Hashes:** production and database hashes did not change; database SHA-256 remained a9acaafb230ca34c5e57adea41f25cf0640c9fdc74864f261a116f67b632f5fc.
9. **Release readiness:** not certified. Resolve the 18 confirmed critical turns and the six deterministic assertion failures, then run a targeted repair validation before considering another full certification.

## Critical adjudication

The complete 25-row table is saved as `critical_finding_adjudication.csv` and `.json` in the run directory. Confirmed blockers include:

- **CAT-02-B/3** (model_language): False absence claim: the frozen program record contains a configured curriculum.
- **CAT-07-B/3** (mixed): The answer omits the published ACCEPTED_AVAILABLE status and sends the international applicant to confirm a restriction that the record resolves.
- **CAT-18-B/3** (mixed): The answer omits the decisive published NOT_ACCEPTED international status in the established international context.
- **CAT-20-B/3** (model_language): A program-level availability restriction was converted into an individual eligibility determination.
- **FLOW-05/3** (deterministic): The response omits a documented criminal-record-check entrance requirement and the UBC application route.
- **FLOW-10/4** (deterministic): A conditional question was stored as completion of both alternatives and the OR-group question was not answered.
- **FLOW-17/4** (model_language): The answer says the forensic elective rule is absent although the frozen curriculum specifies six credits/exactly two courses.
- **FLOW-22/2** (deterministic): The comparison referent was lost and the answer replaced the three programs with a nursing-family list.
- **FLOW-27/3** (mixed): The graduation checklist omits the documented two-year related-work-experience requirement.
- **FLOW-35/3** (mixed): The response retracts the published Program Head approval requirement for all 12 affected nursing programs.
- **FLOW-45/3** (deterministic): The structured correction succeeds, but the student-facing response falsely says the withdrawn course remains completed.
- **FLOW-46/2** (deterministic): The comparison reports international eligibility unknown although both frozen program records say not available.
- **LONG-02/20** (model_language): The response makes ICES uniquely mandatory and omits the published allowance for other Canadian assessment services.
- **LONG-09/11** (model_language): Entry Option 3 courses were mislabeled as the standard entry route.
- **LONG-10/7** (mixed): The response claims entrance requirements are unavailable although the frozen record contains degree, English, and selection rules.
- **LONG-12/10** (model_language): The answer applies the Canadian work-permit condition to all international applicants and omits the outside-Canada path.
- **LONG-12/11** (model_language): The simplified answer again applies approval/work-permit conditions without the outside-Canada exception.
- **LONG-12/20** (model_language): The mandatory alternate-entry pre-entry assessment is incorrectly described as optional.

## Validation and artifacts

The full Python suite ran once. Six API tests initially failed only because localhost was not running; all six passed after starting the unchanged service. The other 541 tests passed in the full run. Browser state passed 5/5.

Grouped failure transcripts: `failure_exports/c3617c20bf3b5797`. The run directory also contains all 120 transcripts, 120 judgments, raw evaluator attempts, evidence packets, score CSVs, the comparison tables, adjudication tables, usage summary, manifests, and validation logs.
