# ASTERIS PROJECT CONTINUITY

Snapshot date: 2026-09-09
Canonical project: C:\Users\rdubo\Asteris
Canonical backups: C:\Users\rdubo\Asteris\ASTERIS_PROJECT_CONTINUITY.md and C:\Users\rdubo\Asteris\ASTERIS_PROJECT_CONTINUITY.txt

## Purpose and authority

This is a portable working-context backup for resuming Asteris in a new ChatGPT account. It summarizes the project, decisions, certification history, known boundaries, and next work. It is not a software or PostgreSQL backup and does not reproduce the entire conversation.

Canonical project files, governed database evidence, and the latest applicable reports are the factual authority. Newer reports/files override this snapshot. Distinguish a historical result from current verified behavior. This document was prepared by reading project reports and selected source files; database counts and test results below are reported validation, not a new database audit or test run. No live OpenAI/API benchmark calls were made for this documentation task. No secrets or .env values were read or copied.

Business intentions, design preferences, model preferences, and the proposed roadmap below reflect the owner's current instructions. They are not claims that those capabilities have already been implemented.

## Product vision, ownership, and institutional separation

Asteris combines structured institutional academic data with an AI advisor. The value is reliable, evidence-backed advising about programs, courses, admission, progression, graduation, and international availability, explained in useful human language.

The intended business model is hosted SaaS. Asteris retains ownership of its core software and provides institution-specific service rather than transferring the core product to an institution. BCIT is the current institution; SAIT, KPU, and other institutions are future possibilities. Preserve tenant/institution separation in data, configuration, branding, and future access controls. Current institution-name configuration does not establish complete enterprise multitenancy or isolation certification.

Institution voice is invariant: BCIT offers, requires, publishes, and decides; Asteris advises and helps interpret. Never imply that Asteris awards BCIT credentials. Current source exposes ASTERIS_PLATFORM_NAME and ASTERIS_INSTITUTION_NAME, defaulting to Asteris and BCIT. Future institutions must be configurable rather than hardcoded into general behavior.

## Local project and normal startup

Work in the canonical Windows project, not an old copy:

```powershell
Set-Location -LiteralPath 'C:\Users\rdubo\Asteris'
& '.\.venv\Scripts\python.exe' -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000/app in the browser. The normal documented equivalent, when the correct environment is already active, is:

```text
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

PostgreSQL must be running and the existing local environment configuration must be available. Preserve existing secrets locally; never paste them into chat or this file. For a controlled production-mode demo, follow SECURITY_AND_OPERATIONS.md and PRODUCTION_READINESS_CHECKLIST.md, including ASTERIS_ENV=production and the required internal-key setup. Do not switch configuration merely because you are reading this backup.

The explicit current .venv Python launcher successfully loaded Uvicorn during preparation of this snapshot (Uvicorn 0.52.4, CPython 3.12.14). A historical .venv-broken-20260831 directory remains; it is not the startup environment. Prefer python -m uvicorn over a potentially stale standalone launcher. No current failure of the explicit .venv launcher was observed. This check did not start/restart the app or prove database readiness.

When a future engineering task calls for validation, existing commands include:

```text
.venv\Scripts\python.exe -B -m unittest discover -p "test*.py" -q
node --test test_conversation_ui.js
```

Some full-suite HTTP tests require the canonical app running on localhost:8000. Inspect test behavior and select model-free gates first; do not launch expensive benchmark runners by habit.

## Architecture and structured evidence

- main.py serves the FastAPI application, static browser /app, and JSON /advisor route.
- ai_advisor.py resolves exact subjects and scope, gathers deterministic evidence, supplies direct answers where possible, and uses the OpenAI Responses API for remaining synthesis.
- PostgreSQL is the operational academic source of truth. advisor.py supplies academic retrieval; academic_rules.py, eligibility.py, advisor_eligibility.py, advisor_engine.py, program_requirements.py, curriculum_evaluator.py, progression.py, and related services evaluate structured requirements and curriculum.
- conversation_state.py owns versioned TopicState and durable structured subject memory. response_policy.py controls response discipline. static/ contains the browser client.
- The browser sends at most ten text messages, but passes structured state separately. Later Phase 2C memory includes bounded subject snapshots, comparisons, user facts with provenance, and verified conclusions. Corrections must invalidate dependent conclusions. The older CONVERSATION_STATE.md describes the foundational contract; later implementation/reports extend it.
- Browser state is held in page memory and is lost on refresh. Failed requests must not advance saved state. State can survive a server restart while the same page remains open.
- Ingestion uses extracted official evidence, governed payloads/revisions, hashes, review, controlled application, and zero-diff replay. Reports and saved sources explain what was certified.

Permanent priority: factual structured evidence outranks conversational polish. Correct routing and rule evaluation must not depend on the model guessing facts already stored. Model-generated wording must not override a certified evidence packet or turn a retrieval failure into an absence-of-evidence claim.

## Certified catalog, governance, and provenance

Latest reported state: 374 active/governed programs and 3,976 active courses. The ordinary catalog certification reconciled 373/373 current ordinary identities exactly once, plus intentionally retained 5325ACERT under the no-cleanup policy. Do not delete that record to force the count to 373.

The catalog audit recorded 3,934 BCIT-owned courses plus 42 explicitly namespaced UBC courses for the joint 9940BSC curriculum; zero unresolved course references or ownership violations; 374/374 normalized admission coverage; and no program without a curriculum path. Historical CIVL1011 identity is retained for prerequisite integrity without inflating active-course totals.

The catalog audit initially reported 355/374 governed pointers and 19 pre-governance programs. LEGACY_PROGRAM_REAUDIT.md supersedes that gap: all 19 were reviewed and governed, yielding 374/374 active governed revision coverage, zero remaining pre-governance programs, zero factual corrections, one provenance-only correction, and successful exact-hash/zero-diff checks.

All active program source URLs were present in the catalog audit. Seven course source URLs were missing at that audit; do not claim that later governance completion automatically repaired those seven gaps. Two offering-mode discrepancies were also recorded for review. Preserve source URLs, capture context, approval/revision identity, and human-confirmation boundaries. Certification is scoped to recorded evidence and time, not a promise that every institutional page remains unchanged.

## Academic semantics and regression examples

Represent course prerequisites, AND/OR groups, minimum grades, non-course conditions, substitutions, electives, credit pools, progression, and graduation faithfully. Admission, continuation, credential award, and course prerequisites are distinct scopes. A hypothetical question is not proof that a course was completed. Applicant background must remain separate from the requested program's identity and credential.

Keep unknowns explicit. Competitive selection, equivalencies, transfer/PLAR, professional or clinical verification, Program Head approvals, committee decisions, and immigration decisions require the designated human authority where the published rules say so. An opaque condition must not be silently converted into MET or UNMET.

Important regressions:

- Civil Engineering: distinguish 5410DIPLT and 8660BENG. The diploma follows successful completion of the first two academic years; Level 5 requirements govern continuation into BEng years, not the earlier diploma award. Same-name Civil Technology 5430ACERT and 5430CERT need credential disambiguation.
- Nursing: broad family discovery includes 28 active records; Specialty Nursing is a 27-record subset excluding the main 8875BSN. Preserve advanced certificates, program-specific international restrictions, and Program Head approval for the 12 affected specialty programs. Do not apply one pathway's conditions to all nursing applicants.
- Technology Management 8350BTECH: resolve the exact target before interpreting applicant credentials; preserve English, diploma, relevant-work and pre-entry assessment evidence. Detailed acceptance example follows below.
- Applied Computing MSc M600MSC: retrieve actual graduate admission and selection evidence; do not claim requirements are absent. International reconciliation confirmed published availability, a valid BCIT study permit before starting, and eligibility to apply for a PGWP. This is institutional evidence, not a guarantee of an individual immigration outcome.
- Red Seal: search published admission conditions across programs. Report only recorded pathways; do not infer that a Red Seal universally substitutes for prerequisites or grants transfer credit. An unrecorded pathway is not proof that none exists.
- LIBS 7001: preserve three valid OR routes. CMGT 8700: retain completion exceptions, work experience, topic, and sponsor conditions; do not interpret years as a grade or mark both OR alternatives completed from a hypothetical.
- Preserve exact course-code identity, the forensic elective rule of six credits/exactly two courses where applicable, published work-experience graduation requirements, and distinctions between entry options. Do not invent course codes by matching substrings in titles.

## International certification and four-state semantics

Latest reconciliation: 253 ACCEPTED_AVAILABLE + 12 CONDITIONAL_RESTRICTED + 1 NOT_ACCEPTED + 108 UNKNOWN_NOT_PUBLISHED = 374. There are 266 deterministic structured decisions and zero remaining reconciliation blockers.

- ACCEPTED_AVAILABLE: explicit published international availability; not proof that an individual satisfies admission or immigration requirements.
- CONDITIONAL_RESTRICTED: explicit availability subject to published limitations. Surface decisive approval, location, permit, study-permit/PGWP, or other restrictions and applicable exceptions.
- NOT_ACCEPTED: explicit published non-acceptance/unavailability. Do not omit it in an international advising context.
- UNKNOWN_NOT_PUBLISHED: no authoritative published deterministic decision found. It is a valid certified state, not a negative inference or retrieval failure.

Rule-only international evidence is normalized equivalently to delivery-fact-backed evidence. Family answers must use each program's certified state, not generic summaries. In specialty cases, distinguish applicants inside Canada from published outside-Canada pathways; do not universalize work-permit conditions.

The reconciliation resolved six source/evidence blockers, including exact-ID URL/canonicalization issues and M600MSC. It also explained an older 220-versus-217 counting bug: missing delivery-facts rows were mistakenly counted as deterministic. The corrected final count is 266, not the earlier intermediate totals. The 108 unknowns are non-errors; never manufacture certainty to reduce them.

## Human Advisor chronology and validation

Counts below belong to different historical suites and scopes; they are not additive or interchangeable.

1. Phase 1 baseline: 120 scenarios/636 turns; weighted score 89.52/100. Later Phase 3 comparison records baseline structural assertions 615/678. Factual, scope, routing, and language defects justified staged repair.
2. Phase 2A, deterministic/state hardening: 18/18 targeted structural scenarios, 87/87 turns, 11/11 release gates, 520/520 Python, 5/5 browser-state. Fixed prerequisites, course identity, scope binding, family completeness, null handling, comparisons, and state. The attempted live Sol pass hit four exhausted-credit errors and produced zero successful turns; structural success was not language certification.
3. Phase 2B, answer discipline: 18 scenarios/88 live Sol Medium turns, 88/88 structural assertions, 14/14 focused quality, 30/30 harness, 11/11 Phase 2A gates, 534/534 Python, 5/5 browser-state. Closed Civil award/progression and Nursing language gates; reduced list dumping and unsupported inference. Quality comparisons here are heuristics, not a new full rubric score.
4. Phase 2C, long memory: 12/12 long scenarios, 264/264 structural turns, 12/12 return-to-first-program after truncation; comparison 3/3, fact retention 4/4, correction/invalidation 3/3, stop/resume 2/2. Python 547/547; browser-state 5/5. One lexical-overlap candidate remained for review, with zero substantive repetition failures.
5. Phase 3 full certification: 120/120 scenarios and 636/636 turns; weighted score 95.52/100; 672/678 structural assertions. It was BLOCKED because source review confirmed 18 critical turns out of 25 judge flags. A high average cannot offset a critical academic error. The phase-specific report says Phase 1 used Astra Low as judge and Phase 3 Sol Medium, so score deltas are descriptive, not a clean same-judge comparison.
6. Phase 3B: all 18/18 source-confirmed critical turns closed (18 to zero); targeted overlay reached 678/678 assertions. Targeted entity/context/scope were 100% each, with zero transport errors. Gates: Phase 3B 17/17, Phase 2A 11/11, Phase 2B 15/15, Phase 2C 12/12; Python 564/564; browser-state 5/5. Reused frozen evidence, ran 16 affected scenarios and only six residual reruns; no full rerun or model judge. This authorized Production Hardening, not unrestricted production.

Report caution: HUMAN_ADVISOR_BENCHMARK.md currently retains a Phase 1 heading but contains the later phase3_certification run and 95.52 score, with provisional metadata. Do not use it alone to reconstruct baseline history or override the phase-specific source-adjudication and closure reports.

## Production Hardening and readiness boundary

PRODUCTION_HARDENING.md declares READY FOR CONTROLLED BCIT DEMO PREPARATION within the single-process demo boundary. Controls include validated environment configuration, request IDs and privacy-conscious logs, health/live and health/ready, 64 KiB body limits, default 20 requests/minute, four concurrent advisor requests, 30-second OpenAI timeout, one retry, and 1,200 output-token ceiling. Production hides internal endpoints behind a key, disables docs, and enforces trusted hosts/explicit CORS. Dependency failures return safe errors without fabricated academic answers or state advancement.

Validation: 10/10 focused hardening, 17/17 Phase 3B, 12/12 long-memory, 574/574 Python, 5/5 browser-state. Production smoke recorded health 200/200, docs 404, internal endpoint 404 without key and 200 with key. Zero live OpenAI calls in this phase. Frozen evidence estimated 33.5% less replayed history, not an observed universal cost saving.

Before a controlled demo: make and verify a fresh database backup, confirm intended network/proxy exposure, and complete event-specific acceptance. No cloud target was found by the hardening audit. No complete fresh-schema migration baseline/ledger, deployment automation, account system, or institutional admin UI was established.

Limited pilot still needs a chosen TLS/ingress target, shared rate limiting where multi-process, PostgreSQL pooling, full schema baseline/ledger, disposable restore drill, mocked load testing, centralized monitoring and budget alerts, data-refresh ownership, and BCIT privacy/retention/operations approval.

Public production additionally needs managed authentication and least-privilege authorization, durable abuse/session controls, WAF/bot controls, high availability and tested recovery, automated encrypted backups/rollback, threat and vulnerability assessment, penetration testing, accessibility and legal/institutional approval. A shared internal key and process-local limiter are bounded demo controls, not a complete enterprise security system.

## Factual Reliability Recovery: browser reality gets the final vote

Manual /app testing after certification exposed ordinary factual failures. Database evidence was intact; the advisor's routing and response path failed to use it reliably. Browser and benchmark shared /advisor, history width, and structured state, but certification explicitly selected Sol Medium while the browser inherited Luna. The exact manual conversation and rendering boundary were missing from certification coverage.

Root causes included subjects misclassified as credentials; exact target resolution suppressed by applicant background; missing Spanish aliases; Red Seal search limited to metadata rather than admission conditions; certified packets displaced by model prose; and unfiltered raw tool protocol such as functions.search_programs/JSON reaching users. Institutional voice also blurred BCIT and Asteris.

Recovery made exact program resolution take priority, separated applicant facts, routed engineering/nursing/technology/biotechnology/biochemistry as subjects or families, and normalized Spanish ingeniería/ingenieria to engineering. It used certified four-state international packets directly, searched published Red Seal admission evidence, filtered protocol at server and browser boundaries, and configured institution voice. Source defaults now specify gpt-5.6-sol with medium reasoning on model rounds.

Technology Management evidence remained in PostgreSQL: program 8350BTECH, rule set 1186, condition 1330. The recovery did not change the database. Factual answers for the audited path can be deterministic rather than relying on Sol to infer structured requirements.

Latest recorded validation:

- Full Python: 584/584.
- Phase 3B blocker gates: 17/17.
- Factual recovery gates: 10/10.
- Browser-state: 6/6.
- Exact ten-turn manual transcript through actual /advisor: 10/10 with model construction disabled, zero model requests.
- One neighboring live Sol Medium request: HTTP 200, no tool leakage; 13,791 input tokens, 404 output tokens, 2,034 cached tokens. No dollar charge was surfaced and none was estimated. No judge or broad benchmark ran.

Release conclusion: the audited real /app path is factually safe enough to resume Demo/UI preparation. This is not exhaustive certification of arbitrary phrasing. Residuals include 108 published unknowns, opaque human-confirmation conditions, limited Red Seal evidence, limited Spanish normalization rather than multilingual certification, and complex model synthesis.

Critical manual acceptance example: ask for Technology Management, then naturally say, "I have English 12 with 68 percent, I have a diploma from BCIT, but I don't have work experience. Can I apply?"

Expected evidence-based answer: English 12 68% is MET because the published threshold is 67%; BCIT diploma is MET for the regular-entry pathway; no relevant technical work experience is UNMET because at least one year is required; overall the applicant does not currently meet all published requirements. BCIT also requires an approved pre-entry assessment before application. Do not describe that assessment as optional. The preserved user browser transcript showed this result after recovery.

Actual browser behavior gets the final vote. Test ordinary factual questions naturally, including follow-ups and corrections, rather than accepting only scripted benchmark success. Never improve tone at the expense of these facts.

## Model policy and cost-conscious engineering

Standing owner preference: use GPT-5.6 Sol with Medium reasoning for every Asteris Work task unless the owner explicitly changes this instruction in a future request. Do not use Astra Light, Astra, Luna, or another model for Asteris Work tasks. The same Sol Medium preference applies to Asteris advisor/testing. Historical work with other models is context, not permission to reuse them. Source configuration names are ASTERIS_AI_MODEL and ASTERIS_AI_REASONING_EFFORT; defaults were verified in source, without reading secret-bearing runtime configuration.

Run deterministic/model-free checks first; certify factual acceptance before conversational benchmarking. Reuse frozen/cached evidence and checkpoint live runs so completed work survives failures. Do not duplicate reruns or repeat a broad benchmark without a clear unanswered question and justified cost. Stop promptly on quota failures rather than silently switching models. Track all diagnostic requests, including failed/repair attempts, not only the final successful run.

Historical reported live phase totals illustrate the lesson: Phase 2C 752 requests/about US$15.41; Phase 3 850 requests/about US$37.39; targeted Phase 3B 189 requests/about US$3.52. These are historical report estimates under recorded rates, not current prices or a task budget. API spend and Work/Codex subscription credits are separate measures. Unknown credit usage must remain unknown; do not invent dollar charges or infer one system's consumption from the other.

## UI, brand, and remaining roadmap to BCIT

The browser advisor exists and audited factual paths can support controlled-demo preparation. Visual polish remains pending. Desired interface: friendly and modern, mostly light/white with Asteris brand colors; avoid a dark hacker aesthetic or an old-fashioned robot persona. Preserve factual reliability and accessible, readable answers while improving warmth and presentation.

Use Asteris Technologies for the company presentation and preserve the established master logo identity. Locate the owner's approved logo, colors, and website/domain assets before design or publishing; exact domain and master asset were not verified in the canonical reports used for this backup and are deliberately not invented. Position the offering around structured institutional evidence and helpful advising.

Proposed sequence, to confirm against the owner's current goal:

1. If still desired after recovery, complete a large deterministic factual certification and founder manual acceptance of ordinary browser questions, emphasizing the previous failures. Broaden only to resolve real coverage gaps; a costly broad model benchmark is not automatic.
2. Demo/UI: polish the actual /app experience without weakening factual gates or state.
3. Commercial/pilot package: product story, hosted-SaaS ownership model, institution responsibilities, pilot scope, success criteria, support, data refresh, and a clear readiness boundary.
4. Final pre-demo acceptance: natural factual questions, Technology Management acceptance, international families, exact-name routing, long-context corrections, clean rendering, health checks, and verified backup/network setup.
5. BCIT outreach and presentation when the owner authorizes contact. This backup does not authorize sending messages.

Deferred until justified: apprenticeship/training model extension, broad multilingual polish, institutional admin UI, and full public-production enterprise controls. The catalog separately tracked 52 holdbacks: 19 non-program/special-entry items, 31 apprenticeship/training structures without identifiable course IDs, and two prior holdbacks. These are outside ordinary-program certification. Enterprise controls may be deferred for a controlled demo but remain required before their applicable pilot/public scope.

## Important report and artifact map

All paths below are relative to C:\Users\rdubo\Asteris. Most top-level reports have a same-stem .json companion for structured evidence.

- FACTUAL_RELIABILITY_RECOVERY.md / .json: latest audited factual release decision, causes, unchanged data, validation, and narrow live usage.
- factual_reliability_recovery/before_after_manual_transcript.md and .json: exact observed failures and repaired ten-turn output.
- factual_reliability_recovery/end_to_end_trace.md and .json: entity/scope/tool route and where historical evidence was lost.
- factual_reliability_recovery/browser_vs_benchmark_path_comparison.md: shared route but model/profile and coverage divergence.
- factual_reliability_recovery/technology_management_rule_evidence.json: 8350BTECH admission evidence and applicant evaluation.
- factual_reliability_recovery/tool_leak_root_cause.md and root_cause_to_fix_mapping.md: protocol leak and generalized repair mapping.
- factual_reliability_recovery/residual_factual_risks.md, validation_summary.json, api_usage_cost.json, and saved test .txt logs: limits, checks, and usage.
- PRODUCTION_HARDENING.md / .json: bounded controlled-demo controls, final checks, residual risks. production_hardening/ holds supporting artifacts.
- PRODUCTION_READINESS_CHECKLIST.md and SECURITY_AND_OPERATIONS.md: demo/pilot/public gates and backup, restore, secrets rotation, rollback, and operational procedures. Do not copy actual secret values into continuity files.
- HUMAN_ADVISOR_PHASE_3_CERTIFICATION.md / .json: 95.52 full-corpus score and 18 source-confirmed critical blockers. Its adjudication supersedes provisional generic report flags.
- HUMAN_ADVISOR_PHASE_3B.md / .json: 18/18 closure and 678/678 targeted overlay; before_after_transcript_evidence.json and blocker_to_root_cause.csv/.json in the recorded run artifacts explain every closure.
- HUMAN_ADVISOR_PHASE_2A.md, HUMAN_ADVISOR_PHASE_2B.md, HUMAN_ADVISOR_PHASE_2C.md and JSON companions: staged deterministic, language, and long-memory results.
- HUMAN_ADVISOR_BENCHMARK.md / .json and human_advisor_benchmark/runs/: benchmark machinery, frozen transcripts/evidence/judgments and validation ledgers. Inspect run identity; the generic report is not an immutable Phase 1 record.
- BCIT_CATALOG_CERTIFICATION_AUDIT.md / .json: ordinary catalog reconciliation, counts, identity/course/rule integrity, historical provenance gaps and holdbacks. Details: program_extractor_audit/catalog_certification/.
- BCIT_INTERNATIONAL_SOURCE_AUDIT.md, BCIT_INTERNATIONAL_ENRICHMENT_PLAN.md, BCIT_INTERNATIONAL_ENRICHMENT_BATCH_01.md through _05.md: staged discovery/enrichment history. Intermediate counts are superseded.
- BCIT_INTERNATIONAL_RECONCILIATION_AUDIT.md / .json: final four-state totals, six blocker resolutions, 41/41 focused and 470/470 Python checks, zero-diff replay. Details: program_extractor_audit/international_reconciliation/.
- LEGACY_PROGRAM_REAUDIT.md / .json: 19/19 governed, 374/374 total coverage, no factual correction; 7/7 focused and 477/477 Python checks.
- BATCH_SCALABILITY_01.md through _06.md, BCIT_REMAINING_CATALOG_AUDIT.md, program_import_contract.py, and migrations 012/013: scaling/governance/import history. Consult current artifacts before making any import change.
- ASTERIS_ARCHITECTURE_REVIEW.md / checklist JSON: historical architecture and ingestion review. Its 19-program/1,233-course counts are obsolete; retain the design discussion, not those counts as current.
- CONVERSATION_STATE.md, course_prerequisite_audit.md, numbered SQL 004-024, program_extractor_audit/, and course_gap_audit/: foundational state, rule, schema, and source history. Do not rewrite applied migration history during advisor tuning.

## DO NOT REGRESS

- Factual correctness outranks tone, fluency, or aggregate benchmark score.
- Resolve exact program names/IDs first; preserve same-name credential distinctions and family completeness.
- Keep applicant credentials, grades, work experience, and reported completions separate from target-program search filters.
- Preserve four-state international evidence and program-specific restrictions/exceptions; unknown is not rejected.
- Never expose raw tool calls, function protocol, internal JSON, or fabricated verification claims in user answers.
- Never claim evidence is absent until the correct program, scope, and stored fields have been retrieved.
- Say BCIT offers/requires; Asteris advises. Keep institution identity configurable.
- Preserve long-context state, comparisons, corrections, and dependent-conclusion invalidation beyond the text window.
- Preserve prerequisite AND/OR groups, minimum grades, electives, non-course conditions, and admission/continuation/graduation scope.
- Preserve exact course codes, historical versus active identity, and external-course namespaces.
- Keep PostgreSQL academic/international contents immutable during advisor tuning unless a separately authorized data correction is necessary and evidence-backed.
- Keep Technology Management English 68% MET against 67%, BCIT diploma MET, no required experience UNMET, and required pre-entry assessment visible.
- Respect Red Seal and other human-confirmation boundaries; do not invent equivalencies, admission guarantees, or immigration outcomes.
- Maintain model/profile parity between actual browser behavior and relevant acceptance tests; prioritize natural browser acceptance.

## HOW TO RESUME IN A NEW CHATGPT ACCOUNT

1. Upload either ASTERIS_PROJECT_CONTINUITY.md or ASTERIS_PROJECT_CONTINUITY.txt. They contain substantively the same information; either is sufficient.
2. Provide the latest project files/reports if available. Give access to the canonical project or share selected non-secret files. Keep the software and database backups separately; this file cannot restore them.
3. Tell the assistant your current goal, for example: "Read this Asteris continuity backup. Verify the latest project state, then help me prepare the BCIT demo UI. Use Sol Medium; do not use Astra unless I change that preference."
4. Require verification of actual project state before changes: canonical location, current reports, relevant source, and appropriate read-only evidence. Never assume this snapshot is newer than the files.
5. Preserve the documented factual gates, institutional voice, data boundaries, and cost discipline. Ask for the smallest useful next step toward your current goal rather than automatically restarting completed certifications.
6. Do not upload passwords, API keys, database credentials, account identifiers, or secret-bearing .env files. Supply variable names/placeholders if configuration context is needed.

This snapshot records the 2026-09-09 recovery state. Continue from newer verified evidence whenever available.
