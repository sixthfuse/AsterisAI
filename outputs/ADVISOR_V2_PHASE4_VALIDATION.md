# Asteris Advisor V2 — Phase 4 eligibility and academic reasoning

## Recommendation

**Phase 4 deterministic implementation is complete. Proceed to hands-on testing of `/app-v2`, but do not begin Phase 5 until that acceptance pass and a small live Sol extraction check are complete.**

The deterministic core, database inventory, focused tests, all-program smoke test, and broad regression suite passed. Production `/advisor` and `/app` were not changed. There was no cutover, migration, source-data normalization, or database write.

## Read-only PostgreSQL inventory

The inventory was generated from the live database with `SET TRANSACTION READ ONLY`. The full machine-readable result is in `outputs/phase4_eligibility_db_inventory.json`.

- 374 active programs; all 374 have an `ADMISSION` rule set.
- 388 admission rule sets, 395 groups, and 476 conditions.
- 392 admission groups use `AND`; 3 use `OR`.
- 3 programs have nested rule groups: Construction Management (`8800BTECH`), Electronics (`8900BTECH`), and Applied Computing (`M600MSC`).
- 349 programs have only one `OFFICIAL_ADMISSION_REQUIREMENTS` condition containing unstructured official text and explicitly marked non-executable/human-confirmation. Only 25 programs have more granular normalized admission conditions.
- Admission rule-set mode metadata covers 211 part-time programs, 131 full-time programs, 15 combined full-time/part-time programs, plus a small number of legacy casing/combined labels. This is metadata, not by itself an executable campus/mode restriction.

Most prevalent granular admission types:

| Type | Conditions | Programs | Treatment |
|---|---:|---:|---|
| Grade | 27 | 17 | Deterministic threshold and accepted alternatives |
| Work experience | 16 | 13 | Deterministic unit threshold; recency can require review |
| Document | 16 | 14 | Student assertion plus institutional verification boundary |
| Credential | 12 | 12 | Deterministic preliminary matching |
| Licensure | 12 | 12 | Missing student fact or institutional verification |
| English grade | 4 | 4 | Deterministic threshold |
| Pre-entry assessment | 3 | 3 | Missing fact, met, or institutional approval depending on stored parameters |
| International credential evaluation | 2 | 2 | Applicability from student country/status; final evaluation requires review |

Singular but important real shapes include prior diploma/degree, GPA, related/unrelated/bridging credential GPA, credential exclusion, Red Seal, high-school graduation, post-secondary credits, subject-sequence averages, intake-date GPA exceptions, combined ELEX course averages, four Electronics entry options, Applied Computing standard/alternate entry, competitive ranking, and linked-program admission.

Representative programs used in design and smoke tests:

- `1165DIPMA`: current and post-2026 English thresholds plus math alternatives/assessment.
- `8630BACC`: diploma, GPA, English, five subject-sequence averages, and pre-entry assessment.
- `8800BTECH`: common requirements plus nested OR pathways involving credential GPA, work experience, Red Seal, math, exclusions, and international credential applicability.
- `8900BTECH`: pre-entry approval, English category, credential/average routes, a three-of-four ELEX combined average, and professional-equivalency review.
- `9940BSC`: UBC/transfer paths and a September 2026 GPA exception, with institutional path review retained.
- `M600MSC`: nested standard/alternate entry plus documents, references, international credential evaluation, and competitive committee review.

Academic-rule diversity beyond initial admission is also material: 15 continuation sets across 15 programs, 13 progression sets across 5 programs, 270 international sets across 266 programs, and 886 completion sets across 359 programs. Progression types include theory/practical pass, second-failure readmission, cohort/mode sequence, maximum duration, and program-course grade. The judgment- or policy-heavy types remain human review in v2.

Course prerequisites contain 278 groups and 387 conditions. They include 335 `AND` course conditions across 240 courses, 20 `OR` course conditions across 12 courses, and 273 minimum-grade conditions across 193 courses. There are also program-admission, department approval, sponsor, work-experience, communication-credit, subject-credit, and program-completion conditions. Deterministic v2 now evaluates course completion, minimum grades, AND/OR alternatives, program admission, and structured work experience; other non-course prerequisite forms remain explicit human review until their parameters are normalized.

Campus and international coverage is not yet uniform enough for a universal deterministic constraint. `program_campuses` has 12 rows, while `program_delivery_facts` has 362 rows. International eligibility values include 246 `ACCEPTED_AVAILABLE`, 108 “Refer to official program page,” and seven more specific records. The engine therefore does not infer campus/mode/international eligibility from prose or missing rows.

## Evaluator and state architecture

The v2 engine remains the sole outcome authority. Sol may extract explicit student assertions and choose presentation metadata, but it cannot resolve programs, supply BCIT facts, or decide eligibility.

The profile now supports normalized v2-only representations for:

- per-subject grades, completed courses, course credits, and subject-sequence averages;
- percentage or 4-point GPA scales and route-specific credential GPAs;
- credentials, Red Seal trade, licences, and admitted programs;
- total or area-specific work experience with month/year conversion;
- documents and completed assessments;
- international/domestic status and credential country;
- application date, intake, requested campus, and requested delivery mode.

Source database records are never rewritten or normalized by this work.

Nested evaluation preserves every condition and group. `AND` and `OR` apply different precedence rules: a known failure is decisive for `AND`, a known pass is decisive for `OR`, and unknown/review/failure states survive when they can still affect the result. Alternative branches remain visible in the returned tree. High-level counts and follow-up questions use only the decisive path, so a passed OR route does not trigger irrelevant questions from unused routes.

## Status semantics

- `met`: all decisive modeled requirements pass, or one decisive OR route passes.
- `unmet`: a decisive, fully known requirement fails.
- `missing_student_information`: the catalog rule is available, but an explicit student fact needed for the decision is missing.
- `evidence_unavailable`: the institutional requirement evidence is absent; this is not a failed requirement.
- `human_review_required`: evidence exists, but institutional judgment, verification, equivalency, ranking, or unsupported semantics prevent a deterministic decision.
- `retrieval_failure`: the database/tool call failed; this is distinct from absent evidence and from ineligibility.

Each leaf includes its status, stored description, reported and minimum values where relevant, applicability, reason, and needed student fields. The API response retains both the nested tree and decisive/all-branch status counts.

## Multi-turn corrections and provenance

Explicit later assertions supersede earlier ones. For example, “English Studies 12 is 68%” followed by “Actually English Studies 12 is 73%” stores 73 as current, records a conflict, and retains both assertions in `profile_provenance` with turn, source, explicit assertion marker, value, and superseded value.

Sol-extracted assertions are tagged `sol_extracted_explicit`; request profile or deterministic message extraction is tagged `request_profile_or_message`. The model prompt still prohibits inferred facts, and model-proposed entities remain subject to deterministic repository confirmation. No model-inferred institutional fact can become a student fact.

## Unsupported and human-review boundaries

The largest limitation is upstream structure: 349 admission records are official prose blobs. They are reported as `human_review_required`, never converted into invented pass/fail checks. Other retained review boundaries include:

- competitive/department ranking, first-qualified capacity, licensure and document verification;
- external credential equivalency and international credential evaluation;
- alternate entry requiring significant computing knowledge;
- linked application routes and time-sensitive transitions that require institutional confirmation;
- professional registration/equivalent education routes;
- progression policy such as theory/practical pass, readmission, cohort sequencing, mode sequencing, and maximum duration;
- non-course prerequisites whose subject-credit, communication-credit, sponsor, approval, or program-completion parameters are not yet normalized;
- campus or delivery restrictions represented only as prose or incomplete relationship data.

Recommended-for-success experience is marked non-applicable to eligibility rather than being treated as a requirement.

## Decimal and telemetry fix

Phase 3B evidence writing no longer uses `default=str`. PostgreSQL `Decimal` values serialize as JSON numbers (integral values as integers, other values as floats), and dates serialize as ISO strings. Unknown non-JSON types now fail loudly instead of silently becoming misleading strings. A focused test verifies that `Decimal("0.127436")` remains numeric.

## Validation

- 40 focused v2 Python tests passed after the final GPA-scale normalization.
- The Phase 4 file contributes 13 deterministic tests covering the live-discovered categories, nested alternatives, partial profiles, work-experience recency, combined averages, credits, course prerequisites, date windows, international applicability, unsupported rules, missing evidence, retrieval failure, corrections/provenance, and Decimal serialization.
- 631 repository-wide Python tests passed in 758.352 seconds at the completed implementation checkpoint. The final small GPA-scale normalization was followed by the 40 focused tests.
- 6 browser-state tests passed after the final changes.
- Read-only live PostgreSQL smoke evaluated all 374 governed programs with zero retrieval failures.
- Empty-profile smoke distribution: 357 `human_review_required`, 16 `missing_student_information`, and 1 `met` (the no-formal-application program). This conservative distribution is expected from the 349 unstructured records.
- Representative live results: `1165DIPMA` met; `8800BTECH` met through one complete nested route without asking about unused routes; `8630BACC`, `8900BTECH`, `9940BSC`, and `M600MSC` remained human review where stored rules require institutional judgment.

## Live Sol use and spend

No live Phase 4 Sol call was made because no OpenAI API credential was available to this workspace process. Exact Phase 4 usage is **0 calls, 0 input tokens, 0 output tokens, and $0.00 measured spend**. Tests that emitted production-advisor model telemetry used mocks and reported zero tokens; they were not paid calls.

When a credential is available, the hands-on gate should include a very small interpretation-only sample for messy explicit facts (grade correction, mixed GPA scale, credential plus work experience, and prior-course list). The deterministic outcomes should be compared against the same profiles supplied directly.

## Files changed or added

- `advisor_v2.py`: profile/state extensions, provenance, deterministic admission and course-prerequisite evaluation, status combination, decisive-path questions, and response explanations.
- `advisor_v2_sol.py`: expanded strict explicit-student-fact extraction schema; model authority remains unchanged.
- `human_advisor_benchmark/phase3b_finalize.py`: numeric/date-safe evidence serialization.
- `phase4_eligibility_inventory.py`: repeatable read-only database inventory.
- `phase4_live_db_smoke.py`: all-program and representative live smoke checks.
- `advisor_v2_phase4_golden.json`: dedicated Phase 4 golden/torture corpus.
- `test_advisor_v2_phase4.py`: focused deterministic tests.
- `outputs/phase4_eligibility_db_inventory.json`: live inventory evidence.
- `outputs/phase4_live_db_smoke.json`: live smoke evidence.
- `outputs/ADVISOR_V2_PHASE4_VALIDATION.md`: this report.

## Remaining risks and hands-on gate

The evaluator is mechanically sound for the normalized rule shapes now supported, but catalog coverage is limited by unstructured upstream data. A `met` result means the modeled decisive requirements pass; it is not an admission offer. Human-review and unavailable states should be tested for clarity in the UI.

Before Phase 5:

1. Run hands-on `/app-v2` conversations for the six representative programs and at least two real prerequisite courses.
2. Verify that nested alternative details are understandable and that only decisive missing facts are requested.
3. Run the four-call Sol extraction sample when credentials are available and record exact token/cost telemetry.
4. Confirm that the long provenance payload remains acceptable for intended session length; if not, introduce a bounded append-only assertion history without weakening correction semantics.
5. Decide whether Phase 5 includes upstream normalization of the 349 prose admission records, the incomplete campus relationships, and progression/non-course prerequisite parameters. Those are data-governance tasks, not safe model-inference tasks.
