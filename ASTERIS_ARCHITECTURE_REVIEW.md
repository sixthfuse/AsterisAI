# Asteris Architecture & Program-Ingestion Review

Date: 2026-09-06  
Scope: canonical project at `C:\Users\rdubo\Asteris`; 19 active programs; 1,233 courses.  
Constraint observed: no program added, no existing file changed or deleted.

## Executive finding

Asteris has a credible generalized **data model** and a partially generalized **extraction/enrichment toolkit**, but it does not yet have one generalized program-onboarding application. The schema has already represented markedly different credentials, delivery patterns, curriculum pools, substitutions, alternative graduate paths, clinical requirements, offerings, and executable versus human-confirmed academic rules without a redesign. That is strong evidence that the foundation can absorb several more deliberately unusual programs.

The scaling risk is now the ingestion/control plane, not the central schema. Electronics and M600MSC share `bcit_program_extractor.py`, but the nominal default path is Electronics-specific and M600MSC is an explicit branch. Specialty Nursing uses `nursing_batch_audit.py` plus `import_nursing_family.py`; the main BSN uses another importer. Several advisor aliases and Civil-pathway behaviors are also embedded in Python. These are manageable for 19 programs, but they will create drift at hundreds.

No production code change is warranted in this review task. The official next engineering phase should consolidate declarative program/family profiles, validation, provenance, and transactional import orchestration before broad scaling.

## 1. Workflow as it exists today

| Stage | Current implementation | Assessment |
|---|---|---|
| Program discovery | `bcit_course_gap_enrichment.discover_program_urls()` crawls official BCIT program links; individual program URLs are also supplied directly. Specialty Nursing maintains a family URL batch in `nursing_batch_audit.py`. | Reusable mechanics; discovery scope/selection remains operator-controlled and the Nursing batch is family-specific. |
| Program-page extraction | Shared HTTP/session, URL normalization, HTML parsing, section extraction, JSON-LD reading, and `ProgramAudit` serialization in `bcit_program_extractor.py`; separate Nursing extraction in `nursing_batch_audit.py`. | Partly generic. Exact heading assumptions and program/family branches remain. |
| Matrix parsing | `parse_matrix()` reads `#programmatrix`, component headings, course rows, embedded summaries, JSON-LD credits, electives, and total credits. Nursing reuses it. | The most reusable part. It is tied to the current BCIT HTML shape and cannot faithfully infer every choice/path rule from prose. |
| Course reconciliation | Normalized course IDs are compared with PostgreSQL via `database_course_ids()`; audits record discovered/existing/missing IDs and per-course reconciliation. | Generic and stable. |
| Missing-course enrichment | `bcit_course_gap_enrichment.py` discovers and validates course pages; `enrich_missing()` can fall back to authoritative program-matrix rows; `apply_database()` is the common controlled insert. | Largely generic. Main BSN and Nursing family wrap it with separate record-building/source categorization. |
| Rule mapping | Generic tables support rule sets/groups/conditions, credit pools, substitutions, progression, clinical requirements, practice hours, delivery facts, and offerings. Python maps source prose to those tables. | Schema is reusable; mapping code is the largest special-case area. |
| Audit | JSON program audits, saved source HTML, course-gap CSV/JSON, and Nursing family comparison outputs exist under `program_extractor_audit` and `course_gap_audit`. `import_ready`, unresolved fields, missing courses, and review flags exist for the shared extractor. | Good audit-first pattern, but formats/checks differ by pipeline and lack a single manifest/version contract. |
| Controlled import | Import requires an explicit `--apply-db`; shared extractor rejects non-import-ready audits; missing courses are validated before insertion. Importers use transactions and mostly replace a program's dependent records before rebuilding them. | Directionally sound, but four program-specific import paths duplicate policy and destructive replacement logic. There is no universal dry-run diff, approval record, or single transaction spanning every phase. |
| Regression tests | Unit/integration tests cover extractor semantics, course enrichment, program families, advisor behavior, rule fidelity, and database-backed imported records. | Strong for known programs, though many assertions encode special cases rather than a reusable ingestion contract. |

## 2. Generic versus special-cased

### Genuinely reusable now

- Course-code normalization, canonical BCIT URLs, HTTP/session behavior, program/course discovery, course-page parsing, validation status, database reconciliation, and controlled course upsert.
- BCIT matrix row parsing for standard component headings, required-course rows, credit-bearing elective pools, embedded prerequisite text, and total credits.
- Core relational model for programs, courses, program courses, curriculum components, component membership, credit pools, substitutions, grouped academic rules, progression, clinical/practice requirements, delivery facts, and dated offerings.
- Read/query services in `academic_rules.py`, `advisor.py`, `advisor_engine.py`, `eligibility.py`, `progression.py`, and `program_requirements.py` where behavior is driven by stored IDs, components, and rules.
- Audit-first and explicit-apply safety principles.

### Remaining special cases

**Extractor/importer**

- `bcit_program_extractor.py` has an Electronics URL as its default and its non-M600MSC `parse_program_page()` constructs Electronics credential, study mode, school, campus, intakes, completion text, review flags, and the `73.0`/29-course import-ready invariant.
- The same file dispatches explicitly on `program_id == "M600MSC"`. `parse_applied_computing_msc()` hard-codes the four curriculum components, 12 course IDs, COMP 9190 substitution, program facts, application-status sentence matching, continuation/completion wording, review flags, and `30.0`/12-course invariant.
- `apply_program()` is effectively an Electronics importer, while `apply_applied_computing_msc()` hard-codes graduate admission conditions, dated 2026/2027 offerings, paths, substitution targets, delivery facts, and human-confirmation rules.
- `nursing_batch_audit.py` contains a fixed Specialty Nursing family inventory and family rule/concept extraction.
- `import_nursing_family.py` selects `810*BSN` audit files, defaults to excluding 810ABSN, hard-codes shared admission thresholds/subjects, clinical requirements, program notes, and Nursing-oriented course metadata.
- `import_main_nursing.py` hard-codes 8875BSN, source URL, three-terms-per-year mapping, 137 credits, admissions thresholds, competitive selection steps, clinical gates, international status, and delivery facts.
- Migration SQL remains program-seeded: Construction Management is substantially encoded in `004_program4_generalized.sql`; Nursing additions are in `009`–`011`. This is valid history/bootstrap data, not a scalable importer.

**Advisor/query layer**

- `ai_advisor.py` contains explicit aliases and direct-ID queries for 8875BSN and M600MSC.
- Civil Engineering is modeled in resolver code as the special related pathway `5410DIPLT` + `8660BENG`, including pathway wording and shared-level behavior.
- Construction Management final-project handling explicitly injects `CMGT8800` and `CMGT8810` when program 8800BTECH is active.
- Family/category recognition uses English regex vocabulary including Nursing, Specialty Nursing, BTech, and master's aliases. Credential categories are partly inferred from fixed strings.
- `nursing_requirements.py` is a family-named service even though its verification mechanics are mostly general clinical/practice-rule evaluation. `get_program_details()` calls it for every program and tolerates missing additive tables with a broad exception.
- Many tests correctly protect current behavior but also freeze these IDs, aliases, family counts, and wording. They should remain until equivalent declarative behavior is covered.

## 3. Manual intervention points

### Unavoidable human review by design

- Competitive committee/department ranking, portfolio/questionnaire/reference quality, interviews, supervisory progress, thesis defence, internship/program approval, and handbook-controlled procedures.
- Credential equivalency where an institution or credential evaluator must decide; alternate-entry background sufficiency and bridging plans.
- Professional licensure in good standing, employer/clinical-site acceptance, clinical recency/equivalence, criminal record checks, immunization/fit-test/CPR evidence, and other third-party documents.
- Approval-based substitutions, transfer credit, PLAR, external elective pools, and exceptions where the authoritative policy assigns discretion to a person or committee.

### Currently manual but safely automatable

- Discovering candidate program URLs, taking immutable source snapshots, calculating content hashes, and identifying changed sections since the last approved import.
- Extracting standard program metadata from JSON-LD/known page fields; reconciling normalized course IDs; fetching missing course pages; checking required fields, links, duplicate IDs, totals, component sums, and referential integrity.
- Producing a dry-run database diff, standardized audit manifest, review queue, and post-import row-count/invariant report.
- Generating explicit review tasks whenever parser confidence is low, source facts conflict, a course page is missing, totals do not balance, or an executable rule type is unsupported.
- Running scoped tests before import and the full suite afterward; recording tool/parser/schema versions and approval identity/time.
- Replacing advisor regex aliases and related-program mappings with maintained database aliases/relationships.

### Currently manual because the source is ambiguous

- Translating prose such as “choose one path,” nested alternatives, “approved electives,” co-op/internship eligibility, laddering, block transfer, and variable completion windows into exact operators and scopes.
- Deciding whether similarly worded requirements are admission, continuation, course prerequisite, offering-specific, or completion requirements.
- Resolving discrepancies between matrix rows, course outlines, marketing copy, handbook text, application-status panels, and external policy pages.
- Determining whether missing/blank credits mean zero-credit requirements, variable credit, non-course milestones, or incomplete source data.
- Inferring international eligibility from conditional permit/credential wording rather than an explicit institution-maintained value.

## 4. Data authority and provenance

### Retain as canonical operational data

- PostgreSQL is the runtime canonical store for active programs/courses and their structured relationships/rules. The reviewed live database contains 19 active programs and 1,233 courses.
- Numbered SQL migrations `004`–`011` are canonical, immutable schema/data history and reproducible bootstrap evidence. Future corrections should use new migrations or an approved importer, not edit applied history.
- Approved program audit JSON plus the corresponding saved official source HTML should be retained as the evidence package for what was imported. Course-gap JSON/CSV is retained when it records validation and provenance for inserted courses.
- Tests are executable acceptance evidence, not a data authority, but are part of the retained release record.

### Retain, but archive outside the active operating surface later

- Superseded audit snapshots, family comparison reports, one-time import reports, and older source HTML should move to a versioned archive after a retention policy exists. Keep hashes, source URL, capture time, parser version, approval, and imported revision.
- Program-seeded migrations remain permanently retained even after generalized import tooling supersedes them.

### Legacy/reference-only; candidate for later removal after verification

- `BCIT_Courses_Phase1_2.xlsx`, `BCIT_Courses_Phase1_2_Cleaned.xlsx`, `BCIT_Courses_Phase1_2_Cleanedbycarlos.xlsx`, and the template workbook are not the runtime authority. The enrichment code still reads workbooks as a reconciliation source, so removal is unsafe until that dependency is eliminated and their unique provenance/value is checked.
- `advisor_engine.py.before_level8_fix`, `.venv-broken-20260831`, zero-byte `inspect_courses.sql`, and zero-byte `py` appear to be backup/temporary artifacts. They are not authoritative, but should only be removed under a separate cleanup task after confirming no operational dependency.
- `.pytest_cache` and `__pycache__` are reproducible cache artifacts.
- `program_extractor_audit/m600msc/_program_audit.json` appears superseded by `m600msc_program_audit.json`; verify timestamps/content lineage before archiving.

Nothing in these categories was modified or deleted during this review.

## 5. Schema fitness for the next weird programs

The schema is plausibly sufficient for the next 3–5 stress tests. It already supports AND/OR rule groups with JSON parameters, credit pools, substitutions, alternative components, offering records, progression, and human-confirmation boundaries. A new schema should not be designed pre-emptively.

Real risks to test:

1. **Nested and cross-component choices.** `exact_choice_count` and grouped conditions exist, but curriculum components mainly express membership plus minimum credits. A program requiring nested “choose N from A, including one from B” or alternatives spanning multiple components may expose a real representation/evaluation gap.
2. **Variable/repeatable credits and non-course milestones.** Current course/program fields assume relatively fixed credits. Thesis, practicum, studio, residency, challenge exam, or repeatable-topic rules may need explicit attempt/credit-range semantics rather than notes.
3. **Offering/version/time scoping.** Offerings exist, but most curriculum/rule records are program-wide. Programs whose curriculum or admissions differ by intake, campus, delivery mode, catalog year, or credential exit may require effective-dated/versioned rule bindings.
4. **Laddered/shared curricula.** Civil is handled partly in advisor code. A certificate-to-diploma-to-degree ladder with shared levels, multiple exit awards, or formal block credit needs a data-driven program relationship model to avoid more resolver special cases.
5. **External/approved pools.** Credit requirements can flag external courses and approval, but a large cross-institution elective pool or dynamic approved list needs explicit authority, version, and equivalency governance.

These are validation targets, not proven reasons for immediate schema redesign.

## 6. Official reusable BCIT onboarding pipeline

1. **Select and register source** — record canonical program URL, intended program ID, capture timestamp, catalog/effective period, operator, and source scope. Save the raw HTML and a cryptographic hash.
2. **Extract** — use shared metadata/section/matrix parsers. A program profile may declare selectors and mappings, but may not execute arbitrary importer code.
3. **Normalize and reconcile** — normalize IDs; compare program and course references with PostgreSQL; detect duplicate/conflicting course facts and stale source links.
4. **Enrich missing courses** — fetch official course pages first; use an embedded official matrix row only when it meets the documented minimum fields. Record source and validation method per field/record.
5. **Map rules declaratively** — map curriculum, choices, substitutions, admissions, progression, completion, clinical requirements, delivery, and offerings into a versioned intermediate model. Unsupported/ambiguous facts must become review flags, never guessed executable logic.
6. **Validate** — schema validation, required fields, unique IDs, referential integrity, credit totals/component sums where meaningful, course-gap closure, rule/operator support, offering consistency, and comparison with the prior approved version.
7. **Human review** — approve ambiguous mappings and all human-confirmation boundaries. Record reviewer, decision, notes, and timestamp.
8. **Dry-run import** — produce a deterministic row-level diff and deletion/replacement scope. Verify the import is idempotent and transactional.
9. **Controlled import** — explicit approval token/flag; one transaction per approved package; fail closed on source/audit hash mismatch or unresolved blocking flags.
10. **Verify and publish** — query imported invariants, run program-specific contract tests, then the full regression suite. Save an import receipt and only then mark the revision active.

### Standard audit package

- `source.html` plus hash, URL, capture time, HTTP status, and relevant linked-source inventory.
- `program_audit.json` conforming to a versioned schema, including normalized metadata, raw section text, components, course references, rule mappings, confidence/source for each field, and parser/schema version.
- `course_reconciliation.json` and a human-readable CSV: existing, missing, changed/conflicting, validation source/status.
- `review_flags.json`: severity, category, raw evidence, proposed disposition, reviewer decision.
- `import_diff.json`: inserts/updates/replacements/deactivations by table; no silent deletes.
- `import_receipt.json`: approved audit hash, database revision, operator/reviewer, timestamp, row counts, scoped/full test results.
- Concise Markdown summary for reviewers.

### Stop/go criteria

**STOP** if program identity/source is uncertain; required metadata or curriculum is absent; referenced courses are unvalidated; credit/invariant checks fail without an approved explanation; unsupported executable rule semantics exist; blocking conflicts remain; review-required items lack disposition; or dry-run scope/hash differs from the approved audit.

**GO** only when all referenced records are validated, every ambiguity is either resolved or explicitly non-executable/human-confirmed, the audit package is complete and approved, the import diff is understood, program contract tests pass, and rollback/re-import is deterministic. Full regression must pass before publication.

## 7. Institution-facing admin/import system

The first institutional product should be a governed data-maintenance workflow, not a page scraper UI. It must support:

- Role-based authors, reviewers, approvers, and publishers; draft/approved/published/retired states; immutable revision history and audit log.
- Structured program identity, credential, school, campuses, delivery modes, duration, intakes, international eligibility, and effective dates.
- A curriculum builder for ordered terms/components, required courses, credit pools, exact/at-least choices, alternative paths, substitutions, external electives, zero-credit milestones, and shared/laddered curriculum links.
- A rule builder for AND/OR groups, thresholds/units, documents, experience, licensure, progression, completion, clinical/practice requirements, and an explicit executable versus human-confirmation setting.
- Offering-level overrides for intake, campus, delivery, application status/deadline, capacity/status, and source/effective period.
- Course catalog ownership with prerequisites, equivalencies, variable credits, status, and controlled reuse across programs.
- Bulk upload/API plus forms; versioned templates; validation previews; row-level errors; dry-run diff; idempotency keys; and transactional publish.
- Per-field provenance: institution source, owner, last verified date, attachment/link, notes, and confidence/approval status.
- Conflict and review queues for changed shared courses, unbalanced credits, broken references, unsupported rules, and expiring facts.
- Preview of student-facing advisor answers and machine-readable test scenarios before publication.
- Export/import receipts, rollback to an approved revision, scheduled re-validation, and downstream change notifications.

## 8. Prioritized backlog

### GREEN — stable enough; no action now

- PostgreSQL core entities and current generalized curriculum/rule tables.
- Shared course normalization, discovery, page parsing, reconciliation, enrichment, and controlled course upsert.
- Audit-first, explicit-apply, transaction, human-confirmation, and regression-test principles.
- Existing program behavior while declarative replacements are developed behind compatible tests.

### YELLOW — improve before scaling to hundreds

1. Define a versioned intermediate program/audit schema and one standard audit-package manifest.
2. Replace Electronics/M600MSC/Nursing/main-BSN importer branches with declarative profiles plus shared validators and table writers.
3. Add a universal dry-run database diff, import receipt, source hashes, parser versions, reviewer decisions, and idempotency checks.
4. Move advisor aliases, program families, credential synonyms, Civil relationships, and named project options into database-managed aliases/relationships.
5. Add effective dates/catalog versions to the ingestion contract and test offering-specific rules before deciding on schema changes.
6. Remove workbook dependency from reconciliation after comparing its unique records/provenance with PostgreSQL; then execute a separate archival cleanup.
7. Make tests contract-oriented (audit schema, importer idempotency, fail-closed validation) while retaining program regressions.

### RED — blocker before institutional pilot/production

1. No authenticated author/reviewer/publisher workflow or immutable approval/audit trail exists.
2. No universal transactional publish protocol with approved-hash verification, deterministic dry-run diff, import receipt, and rollback/revision activation.
3. No effective-dated authoritative data ownership/change workflow; current page-derived application statuses and rules can silently become stale.
4. Institution submissions cannot yet be validated against a supported rule vocabulary with unsupported semantics forced into a review queue.
5. Secrets, deployment/database migration discipline, backup/restore, access controls, monitoring, and production data governance require a dedicated readiness review; the local `.env` must never become an institutional data-management mechanism.

## 9. Recommended stress-test program types

Choose one program in each category after the YELLOW audit contract is in place; choose exact BCIT programs only after inspecting current authoritative pages.

1. **Co-op program with optional and mandatory work terms** — tests non-course terms, eligibility gates, sequencing, fees/status, and alternate completion paths.
2. **Apprenticeship/trades program with technical-training levels and external workplace hours** — tests repeated blocks, employer authority, practical assessments, non-credit requirements, and intake variability.
3. **Laddered credential with multiple exits/advanced entry** — tests shared curriculum, block transfer, formal program relationships, and effective credential boundaries without Civil-specific resolver code.
4. **Program with nested elective baskets and an external approved elective list** — tests cross-component choice logic, exact versus minimum counts/credits, approvals, and changing pools.
5. **Clinical/residency program with variable placements and prerequisites scoped to sites or terms** — tests offering-specific rules, placement capacity, variable hours, human verification, and zero/variable-credit milestones.

## 10. Review conclusion

The architecture checkpoint is passed for the data foundation: no observed evidence requires a schema redesign before the next small set of stress tests. The next step is to standardize the ingestion contract and governance path, not add program-specific branches. Production code was intentionally left untouched in this review; only this document and its companion checklist were added.

Final regression result is recorded below after the single end-of-review run.

After confirming the canonical Asteris API was listening and returned HTTP 200, `python -m unittest discover -v` completed on 2026-09-06: **160 passed, 0 failed, 0 errors in 23.480 seconds (25.240 seconds wall time).** The architecture-review task did not disturb existing behavior.

## 11. Scaling-phase implementation update (2026-09-06)

The first ingestion/governance phase is now implemented. `program_import_contract.py` defines contract version 1.0 and adapters for the shared Electronics/M600MSC audit shape, Specialty Nursing audit shape, and main-BSN audit shape. The normalized structure covers program identity, offerings, curriculum components and course references, minimum-credit/substitution/pathway rules, admissions, progression, completion, non-course requirements, international restrictions, provenance, and unresolved review items.

All four import paths now validate the normalized payload before database mutation. STOP conditions include missing required identity/curriculum, unresolved course references, ambiguous executable mappings, unsupported semantics, and undisposed blocking review items. Human-confirmation-only conditions remain explicit warnings and are allowed to proceed. Canonical JSON hashing supplies a deterministic payload hash and idempotency key.

Migration `012_program_import_governance.sql` adds `program_import_revisions`, an immutable normalized-payload ledger with authoritative source URL/type, extraction/import timestamps, pipeline version, provenance tag through the payload, review/confidence status, optional approval identity/time, importer, status, and a unique idempotency key. The migration was applied to the canonical PostgreSQL database. PostgreSQL remains the operational source of truth; no workbook authority was introduced.

Existing source-specific parsing and table-writing logic intentionally remains where semantics differ: M600MSC graduate paths and substitution details, Specialty Nursing clinical/professional requirements, main-BSN term/year and admissions structure, and Electronics-specific admissions/completion mappings. These now converge at a shared validation/governance boundary; replacing every table writer with one declarative writer remains YELLOW because doing so in one pass would create unnecessary behavior risk.

Remaining YELLOW work: universal row-level dry-run diff and approved-hash enforcement; a shared declarative table writer; effective-dated contract/rule bindings; database-managed advisor aliases and program relationships; workbook reconciliation retirement; rollback/revision activation; and broader per-field provenance. RED institutional-readiness items remain unchanged, although the immutable revision ledger and supported semantic validation reduce parts of items 1, 2, and 4.

No real program was added and no cleanup artifact was deleted. Full regression after implementation: **177 passed, 0 failed, 0 errors in 23.899 seconds.**

## 12. Ingestion/governance hardening update (2026-09-06)

The governed workflow is now: **extract → normalize → validate → dry-run diff → review/approve exact hash → import → activate revision → regression checks**. `dry_run_diff()` projects every normalized contract into stable database-shaped rows and returns deterministic JSON with table, natural key, action (`insert`, `update`, `unchanged`, or `delete-or-deactivate`), concise changed values, and complete before/after values. No dry run mutates PostgreSQL.

Approval is now independent of mutable payload provenance. Human-reviewed imports fail closed unless `program_import_approvals` contains an active approval for the exact program ID and canonical normalized SHA-256. Any payload change produces a different hash and invalidates the prior approval. `auto-clean` payloads retain policy-based eligibility, and the existing hash/idempotency behavior is unchanged.

`write_common_contract()` is the reusable idempotent writer for program metadata, generic offerings/curriculum projections, program-course links, and extension adapter boundaries. Unsafe admission trees, graduate substitutions/pathways, Nursing clinical/professional rules, and main-BSN term semantics remain in their program adapters until byte-for-byte database behavior can be migrated. This moves the common writer capability to GREEN; complete retirement of the four bespoke writers remains YELLOW.

Migration `013_program_import_hardening.sql` was applied to canonical PostgreSQL. It adds exact-hash approvals, revision lifecycle state, append-only transition history, active-revision pointers, advisor aliases, and independent program relationships. Activation supersedes the prior pointer without rewriting its payload. Explicit rollback marks the current revision rolled back and activates the previous known-good revision while retaining every transition. Restoring all materialized domain rows from an arbitrary historical normalized payload remains YELLOW because program-specific semantic adapters are still required.

Applied Computing MSc and main/regular BSN aliases now resolve through `program_advisor_aliases`. Nursing and Specialty Nursing family membership is held in `program_relationships`; all 12 specialties and the main BSN remain independent programs, with no inheritance/override architecture. Remaining credential synonyms, Civil pathway relationships, and Construction Management named-project aliases remain YELLOW.

New GREEN items are deterministic row-level dry run, exact-hash enforcement, activation/supersession/rollback audit history, active revision pointers, the shared common writer boundary, and the first DB-managed aliases/family relationships. Remaining YELLOW items are full bespoke-writer migration, effective dates, remaining advisor relationships/aliases, workbook reconciliation retirement, broader per-field provenance, and full materialized historical restore. The production RED list is reduced to authenticated institutional roles/workflow, an institutional review UI, and production security/backup/monitoring/governance readiness.

Full regression after this phase: **183 passed, 0 failed, 0 errors in 23.631 seconds.** Database-backed tests use transaction rollback. The live catalog remains **19 active programs and 1,233 courses**; no new academic program was imported and no cleanup/test artifact was deleted.

## 13. Official institutional resource-link layer (2026-09-06)

Migration `017_institutional_resources.sql` adds curated, ranked official resources keyed by both institution and resource. Topic triggers and normalized intents are data-managed, so another institution can reuse keys such as `admissions` or `tuition_fees` with different URLs without advisor code changes. Advisor runtime reads PostgreSQL only; it does not search or scrape the web. Matching links are appended after deterministic answers (normally one, never more than two), remain available when Asteris lacks enough academic data, and are omitted for unrelated questions. The initial BCIT seed is intentionally limited to high-value admissions, equivalency, international, language, cost, funding, prior-learning, availability, application, and advising destinations. Campus data is deliberately out of scope.

The canonical catalog remains **24 active programs and 1,303 courses**. Full regression after implementation: **209 passed, 0 failed, 0 errors in 33.536 seconds.**

## 14. Minimal campus information layer (2026-09-06)

Migration `018_campus_information.sql` adds institution-scoped campus records and program-to-campus relationships without replacing the existing descriptive `programs.campus` and `program_offerings.campus` fields. This preserves conditional delivery facts while enabling deterministic address, main-phone, campus-to-program, and program-to-campus answers. Each campus stores one official general campus phone only; department, admissions, school, and service-specific numbers are excluded.

The initial BCIT seed contains Burnaby, Downtown, Aerospace Technology, Annacis Island, and Marine campuses. Runtime uses stored records only. The scope intentionally excludes maps, routing, directions, transit, and parking-navigation logic.

The canonical catalog remains **24 active programs and 1,303 courses**. Full regression after the campus and main-phone implementation: **220 passed, 0 failed, 0 errors in 36.338 seconds.**
# 9940BSC joint-institution stress test (2026-09-07)

Program 9940BSC established reusable institution-qualified course identity through migration 019. External UBC catalogue entries use qualified internal IDs, retain their native display codes, and are never represented as BCIT courses. Reusable `curriculum_requirements` and `curriculum_requirement_courses` structures preserve subject-credit requirements, alternative course sets, minimum-credit pools, alternative completion paths, and no-double-count constraints without inventing courses. Evaluator-sensitive transfer equivalencies, application decisions, criminal-record verification, co-op placement, and elective approval remain explicitly human-confirmed.
