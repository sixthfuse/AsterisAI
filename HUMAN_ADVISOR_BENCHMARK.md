# Human Advisor Experience - Phase 1 benchmark

Status: **complete**. Run: phase3_certification_sol_medium_20260908.

Measured advisor: **gpt-5.6-sol**, using the canonical advisor with profile **sol_medium**. Rubric evaluator: **gpt-5.6-sol, low reasoning**. The Work task's UI reasoning setting cannot be independently verified from inside the task.

**120 scenarios / 636 planned turns; 636 turns scored; 120 scenarios fully scored.**
Current attempts: 636 turns, 636 successful responses, 0 request errors.

Weighted score: **95.52%**. Critical flags: **25**, including **0 source-confirmed turns**; noncritical failure turns: **93**. The requested readiness bar is not met. Critical academic errors are a separate gate and cannot be offset by a high average; remaining flags are provisional evaluator findings.

Quality scores below are conditional on successful clean replay. The operational ledger retains errors from all attempts: {}. Application exceptions remain release concerns even after successful retry; see attempt_reliability.json.

## Metrics

Rates are per applicable evaluated turn, not per claim. Adequate means >=3/4; strict means 4/4. Factual 3 allows harmless imprecision only; academically wrong or materially misleading claims are <=1. Null means inapplicable or unassessable and never counts as a pass.

| Dimension | Applicable turns | Adequate or better | Strict | Mean /4 |
|---|---:|---:|---:|---:|
| factual correctness | 547 | 96.16% | 94.33% | 3.87 |
| entity resolution | 634 | 98.58% | 97.32% | 3.945 |
| context retention | 516 | 97.48% | 94.96% | 3.901 |
| scope accuracy | 636 | 97.17% | 94.18% | 3.896 |
| unsupported inference avoidance | 636 | 97.17% | 96.23% | 3.914 |
| unnecessary clarification avoidance | 623 | 99.52% | 99.52% | 3.981 |
| necessary clarification detection | 8 | 75.0% | 50.0% | 3.125 |
| response relevance | 636 | 97.64% | 85.69% | 3.816 |
| repetition avoidance | 636 | 98.74% | 97.33% | 3.953 |
| naturalness | 636 | 95.28% | 75.94% | 3.706 |
| frustration handling | 38 | 94.74% | 94.74% | 3.895 |
| next step guidance | 105 | 80.0% | 63.81% | 3.086 |
| evidence discipline | 632 | 96.84% | 95.25% | 3.9 |

- Unsupported inference rate: **2.83%**.
- Unnecessary clarification rate: **0.48%**.
- Missed necessary clarification rate: **25.0%**.
- Repetition/list-dump rate: **1.26%**.
- Human-advisor naturalness: **3.706 /4**.
- Long-conversation success: **0.0%** (0/12 fully scored).
- Structural state assertions: **585/591** (**98.98%**), separate from semantic entity judgment.

Long-scenario success requires every turn to satisfy all applicable rubric and structural requirements; it is stricter than merely preserving the active program.

## Pass/fail by primary category

| Category | Scenarios | Turns attempted | Turns scored | Pass | Fail | Incomplete/unscored |
|---|---:|---:|---:|---:|---:|---:|
| active_subject | 1 | 4 | 4 | 1 | 0 | 0 |
| applicant_background | 2 | 8 | 8 | 0 | 2 | 0 |
| campus_transition | 1 | 4 | 4 | 1 | 0 | 0 |
| comparisons | 3 | 12 | 12 | 0 | 3 | 0 |
| contradiction | 1 | 4 | 4 | 0 | 1 | 0 |
| course_in_program | 1 | 4 | 4 | 0 | 1 | 0 |
| course_reference | 1 | 4 | 4 | 1 | 0 | 0 |
| course_search | 1 | 4 | 4 | 0 | 1 | 0 |
| credential_disambiguation | 2 | 8 | 8 | 0 | 2 | 0 |
| cross_entity | 1 | 4 | 4 | 0 | 1 | 0 |
| elective_pools | 2 | 8 | 8 | 2 | 0 | 0 |
| explicit_target | 1 | 4 | 4 | 0 | 1 | 0 |
| family_scope | 2 | 8 | 8 | 1 | 1 | 0 |
| filtered_results | 3 | 12 | 12 | 0 | 3 | 0 |
| fresh_reset | 1 | 4 | 4 | 1 | 0 | 0 |
| frustration | 2 | 8 | 8 | 0 | 2 | 0 |
| human_confirmation | 1 | 4 | 4 | 1 | 0 | 0 |
| incomplete_information | 1 | 4 | 4 | 0 | 1 | 0 |
| informal_language | 1 | 4 | 4 | 0 | 1 | 0 |
| international | 22 | 68 | 68 | 6 | 16 | 0 |
| long_context | 12 | 264 | 264 | 0 | 12 | 0 |
| minimum_grade | 1 | 4 | 4 | 0 | 1 | 0 |
| necessary_clarification | 2 | 8 | 8 | 0 | 2 | 0 |
| pathways | 1 | 4 | 4 | 1 | 0 | 0 |
| program_identity | 20 | 60 | 60 | 17 | 3 | 0 |
| repetition | 1 | 4 | 4 | 1 | 0 | 0 |
| required_alternatives | 2 | 8 | 8 | 0 | 2 | 0 |
| return_prior | 1 | 4 | 4 | 0 | 1 | 0 |
| scope_boundaries | 2 | 8 | 8 | 0 | 2 | 0 |
| source_discipline | 1 | 4 | 4 | 1 | 0 | 0 |
| stop_resume | 1 | 4 | 4 | 1 | 0 | 0 |
| topic_switch | 1 | 4 | 4 | 1 | 0 | 0 |
| typos | 1 | 4 | 4 | 1 | 0 | 0 |
| unknown_boundaries | 21 | 64 | 64 | 0 | 21 | 0 |
| unknown_facts | 1 | 4 | 4 | 0 | 1 | 0 |
| unnecessary_clarification | 1 | 4 | 4 | 0 | 1 | 0 |
| work_experience | 1 | 4 | 4 | 0 | 1 | 0 |

A scenario passes only when fully completed and scored without a recorded issue or failed assertion. Observed violations make a scenario fail; incomplete/unscored scenarios never pass.

## Top observed failure patterns

One primary pattern per failed turn, sorted by critical count and then frequency. Counts combine frozen structural assertions, rubric findings and labeled evidence reviews. Repeated symptoms are not independent bugs.

| Pattern | Failure turns | Critical | Examples (scenario/turn) |
|---|---:|---:|---|
| unknown_or_human_boundary | 18 | 9 | CAT-01-B/3, CAT-02-B/3, CAT-19-B/3 |
| missing_next_step | 30 | 4 | CAT-01-C/2, CAT-02-C/2, CAT-03-C/2 |
| scope_mismatch | 15 | 4 | CAT-04-B/3, CAT-07-B/3, CAT-08-B/3 |
| wrong_or_lost_subject | 13 | 2 | CAT-14-A/1, CAT-15-A/1, CAT-19-C/1 |
| wrong_academic_rule_or_arithmetic | 4 | 2 | CAT-16-B/3, FLOW-07/3, FLOW-35/3 |
| missed_clarification | 3 | 2 | FLOW-09/2, FLOW-10/4, LONG-09/11 |
| stop_or_frustration_mishandled | 5 | 1 | FLOW-05/4, FLOW-22/2, FLOW-32/3 |
| unverified_claim_or_guarantee | 1 | 1 | CAT-20-B/3 |
| awkward_or_impersonal | 12 | 0 | FLOW-04/3, FLOW-29/3, LONG-03/5 |
| student_fact_lost_or_not_corrected | 8 | 0 | CAT-16-A/2, FLOW-13/3, FLOW-13/4 |

## Layer attribution

- mixed: **16 failure turns**.
- deterministic: **72 failure turns**.
- model_language: **29 failure turns**.
- unresolved: **1 failure turns**.

Within the consistently rubric-scored subset, layer counts are: {'mixed': 16, 'deterministic': 72, 'model_language': 29, 'unresolved': 1}. All planned turns are rubric-scored. Counts combine rubric, structural assertions and labeled reviews; they count failed turns, not independent bugs.
Critical flags confirmed in task-agent evidence review: 0. Remaining critical flags are evaluator findings pending fuller adjudication; adjudication_queue.json records specific counterevidence and ambiguity. Taxonomy-only reviews correct mismatched labels but do not count as source-verified critical confirmations.

Attribution uses resolution, tool results, raw model output and finalization, with confidence labels. Wrong state or pre-model templates support deterministic attribution. Correct evidence misrepresented by unchanged model output supports language-layer attribution. Causal uncertainty stays mixed/unresolved. Infrastructure errors are separate.

Evaluator label conflicts reviewed: 0; unresolved: 8. Original scores and labels remain in the judgment files.

## Phase 1 baseline evidence-reviewed anchors

- **FLOW-07:** Civil Technology offers two identically labeled clarification choices, then remains ambiguous after an explicit credential reply. No model is called on these turns.
- **CAT-06-A/1 and CAT-06-B/3:** Finalization inserts unrelated UBC course codes into otherwise correctly named raw model answers, altering course identity. This is a deterministic postprocessing problem.
- **FLOW-13/1:** The LIBS 7001 direct prerequisite renderer returns ENGL 1177 at 50 followed by 'None; None', dropping two non-course alternatives and their OR relationship. The source rules exist.
- **CAT-04-B/3:** Civil Engineering prose conditions the diploma award on continuation requirements, although source evidence separates diploma completion from progression into the final BEng years.
- **FLOW-10 / FLOW-12:** Saved responses also correctly explain required final-project and thesis/project alternatives.

These anchors describe the original baseline, not automatically a later candidate run. Reviewed anchors are investigative evidence, not a blinded human panel. Numeric rubric scores remain unchanged unless a separately documented adjudication is explicitly applied. Historical interrupted-attempt findings are labeled.

## Phase 2 recommendations - no fixes made

1. **Critical: preserve prerequisite semantics in deterministic responses.** Render non-course conditions and AND/OR operators, and prevent course-name finalization from inserting unrelated course IDs. Use LIBS 7001 and other prerequisite-group types as release gates. High leverage because these answers bypass the model.
2. **Critical: bind academic claims to their scope.** Prevent admission, continuation and graduation rules from being reassigned during explanation. Use the Civil diploma/Level-5 boundary as a gate.
3. **High: prevent the observed null-pathway tool crash and cover the whole requested family.** The saved LONG-07 attempt fails when get_program_level_courses dereferences a null pathway; a successful replay does not fix it. FLOW-02 omits active Nursing advanced certificates from a broad family request. See operational_findings.json and the evidence-reviewed anchors.
4. **High: improve credential and correction resolution.** Show distinct credentials in clarifications, interpret candidate replies, and distinguish certificate from associate certificate.
5. **High: retain program context around course mentions and informal follow-ups.** Avoid stranding program questions in course-only routing or failing to retrieve available admission evidence after a unique result.
6. **High: address measured comparison and long-history failures.** Preserve comparison sets and relevant student facts, and state memory limits honestly. Establish contracts before prompt changes.
7. **Medium: broaden stop/frustration handling.** Recognize plain and compound stop phrases without lookup; frustration containing a concrete question should still receive an answer.
8. **Medium: improve brevity, directness and next steps.** Avoid unwanted curriculum dumps, repeated templates and generic links when a specific next action is needed.
9. **Then compare models.** Run Sol Medium and Astra Light against this exact suite, keep the judge fixed, repeat paired trials and have humans adjudicate critical disagreements.

## Method, integrity and validation

Frozen foundation: **unavailable active programs**, **unavailable active courses**, and **unavailable governed active programs**. International statuses: unavailable available, unavailable conditional/restricted, unavailable not accepted and unavailable unknown/unpublished.

- Canonical FastAPI TestClient ASGI /advisor route, live PostgreSQL and real OpenAI calls; no mock answers. The external localhost app was also checked and used by existing HTTP-engine regressions.
- Ten prior messages plus returned TopicState, matching the browser. Twelve 22-turn conversations exceed the history window.
- Frozen scenario IDs, expectations, corpus hash and raw source snapshot; production and data hashes before/after.
- Read-only return-event profiling records actual tool/model/finalization evidence. Latency includes observer overhead.
- Thirteen explicit 0-4 rubric dimensions; weights sum to 100. Weighted score is the normalized weighted mean of applicable dimension means.
- Raw judge inputs/results are retained, with validation and stale-input rejection. Missing judgments are not passes.
- Original API-credit interruption is preserved in prior_attempts; interrupted/error scenarios restart from turn one. Only current clean responses enter quality metrics.

Production unchanged during baseline: **True**. Database rows unchanged: **True**.

Validation: full regression check **495/495 passed** (477 existing + 18 initial benchmark tests); completed focused benchmark suite **30/30 passed**. No production advisor/state/routing files changed.

## Interpretation and limits

- Purpose-built stress suite, not a random sample of users or the catalog.
- Rubric scores are Astra-low judgments, not a blinded human panel; investigator-reviewed anchors are labeled separately.
- One primary root-cause classification per failed turn; secondary causes may exist. Model-based attribution is provisional.
- Correctness is relative to the frozen certified database, not an independent re-certification of every BCIT source.
- Evaluator packets contain scoped evidence, not the whole snapshot. FLOW-03/2 demonstrates a source-coverage false positive: a critical flag was rejected against the full snapshot, while original numeric rubric scores remain unchanged. Rates are provisional evaluator estimates, not fully human-adjudicated truth rates.
- No confidence interval or model-superiority claim from a single stochastic run.
- The fixed rubric was used throughout. Early label inconsistencies triggered resubmission; later judgments preserve numeric scores and flag conflicting labels for review. This selection-policy change is recorded; formal model comparisons require identical evaluator policies.
- Model-free deterministic answers cannot improve merely by changing the language model.
- Infrastructure errors and turns after them are excluded from clean quality denominators; old attempts remain separate.

Asteris can give useful, evidence-based answers, but dead-end clarifications, unnecessary detail and critical rule-presentation errors prevent consistently competent human-advisor behavior. Astra may improve explanation and conversational judgment after deterministic gaps are fixed; this run does not demonstrate a model advantage. A model swap cannot repair answers produced before the model is called.

## Deliverables

- HUMAN_ADVISOR_BENCHMARK.json: metrics, denominators, manifests and findings.
- human_advisor_benchmark/runs/phase3_certification_sol_medium_20260908/: transcripts, frozen data, evidence, rubric judgments and CSV score summaries.
- Current grouped failures: human_advisor_benchmark/runs/phase3_certification_sol_medium_20260908/failure_exports/c3617c20bf3b5797/.
- human_advisor_benchmark/README.md: design and run/resume/evaluate/compare commands.
- corpus.json, rubric.json, runner.py, judge.py, comparison.py, report.py: reusable benchmark tooling.
- test_human_advisor_benchmark.py, focused_tests.txt and full_python_tests.txt: validation evidence.
