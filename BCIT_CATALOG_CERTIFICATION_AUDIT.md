# BCIT Catalog Completion & Integrity Certification Audit

Generated: 2026-09-08T16:33:49.673020+00:00

## Certification decision

**BCIT Ordinary Academic Catalog Data Foundation — CERTIFIED COMPLETE**

The ordinary catalog contains 373/373 reconciled current BCIT program identities exactly once. PostgreSQL also retains 5325ACERT under the explicit no-cleanup policy, producing 374 active programs. No critical RED integrity defect remains after the documented minimal corrections.

Regression passed in the current post-correction run.

## Domain results

| # | Domain | Status | Evidence |
|---:|---|---|---|
| 1 | Catalog completeness | GREEN | 373/373 ordinary identities loaded; retained 5325ACERT; missing=0; unexpected=0 |
| 2 | Duplicate and identity integrity | GREEN | duplicate IDs=0; duplicate canonical URLs=0; controlled same-name groups=23; exact name/credential/mode collisions=0 |
| 3 | Course references and ownership | GREEN | unresolved references=0; ownership violations=0; BCIT courses=3934; namespaced external courses=42 |
| 4 | Admissions and rules | GREEN | 374/374 programs normalized; admission sets=388; degenerate=0; impossible thresholds=0 |
| 5 | Curriculum integrity | GREEN | programs without any curriculum path=0; legacy-only paths=0; invalid credit pools=0; invalid choice groups=0 |
| 6 | Governance and revisions | YELLOW | active revision pointers=355/374; legacy pre-governance programs=19; bad active revisions=0; Batch 06 current hashes=65/65 and historical zero-diff=65/65 |
| 7 | Sources and provenance | YELLOW | active program source URLs missing=0; course source URLs missing=7; retained unlisted record preserved |
| 8 | Offerings, delivery, and campus | GREEN | missing study mode/campus/delivery=0/0/0; invalid campus links=0; offering mode discrepancies for review=2 |
| 9 | International coverage | YELLOW | allowed=5; not allowed=1; conditional=2; unknown/not published=366 (never inferred) |
| 10 | Resource, alias, and routing | GREEN | dangerous alias collisions=0; broken active aliases=0; generic same-name groups=23; exact-name routing covered by regression |
| 11 | Out-of-scope structures | GREEN | holdbacks enumerated=52: {'non-program/special entry': 19, 'apprenticeship/training structure without identifiable course IDs': 31, 'prior RED/holdback': 2} |
| 12 | Regression | GREEN | Python 429/429; browser-state 5/5. |

## Core reconciliation

- Current ordinary catalog identities: **373**; matched active in PostgreSQL: **373**; missing ordinary candidates: **0**.
- Active PostgreSQL programs: **374**; active courses: **3976**.
- Intentional no-cleanup record: **5325ACERT**. Unexpected extra active programs: **0**.
- Duplicate program IDs: **0**; duplicate canonical source URLs: **0**; dangerous active alias collisions: **0**.

## Integrity evidence

- Course/reference checks: **0 unresolved**, **0 ownership violations**. The catalog contains 3934 BCIT-owned courses and 42 explicitly namespaced UBC courses, all tied to the joint 9940BSC curriculum.
- Admissions: **374/374** active programs have normalized ADMISSION rules; 388 rule sets; 0 empty/degenerate programs; 0 impossible thresholds.
- Curriculum: 0 programs lack a curriculum path; 0 remain legacy-only; 0 invalid credit pools and 0 impossible choice groups.
- Governance: **355/374** active revision pointers and **355/355** exact approved hashes. The 19 programs without pointers predate generalized import governance; all governed active payload hashes and lifecycle states are consistent. Batch 06 remains 65/65 exact-current-hash and 65/65 zero-diff by retained evidence.
- International evidence: allowed 5, not allowed 1, conditional/restricted 2, unknown/not published 366. Unknowns were not inferred.

## Corrections made

- **CIVL1011** — Added a Historical BCIT course-identity row so two current 8660BENG prerequisite edges resolve without presenting the retired identity as a current course.
- **810MBSN** — Set allows_external_courses and approval_required true for the 3.0-credit elective pool, matching its preserved official text.
- **get_catalog_counts** — Current catalog course totals now count active course rows, so retained historical identities do not inflate the published current-course count.

No ordinary program was imported, deleted, deactivated, or otherwise rewritten.

## Non-blocking YELLOW gaps

- Governance coverage: 19 pre-governance active programs lack active revision pointers. This is legacy coverage debt, not a broken governed revision.
- Provenance enrichment: missing official URLs by table: `{"academic_rule_sets": 0, "courses": 7, "program_campuses": 0, "program_delivery_facts": 0, "program_offerings": 0, "programs": 0}`. Program identities themselves have complete BCIT source URLs.
- International enrichment: 366 programs have no explicit structured eligibility decision. The audit deliberately leaves them unknown.

## Holdbacks and scope boundary

The 52 current-catalog entries outside the 373-program ordinary universe are separately enumerated: {'non-program/special entry': 19, 'apprenticeship/training structure without identifiable course IDs': 31, 'prior RED/holdback': 2}. Apprenticeship/training pages without identifiable BCIT course IDs and special/non-program entries are future model extensions, not ordinary-program defects.

## Methodology and limits

- PostgreSQL was treated as authoritative. Audit queries were read-only; the only writes were the documented CIVL1011 identity and 810MBSN rule-flag corrections.
- Catalog completeness used the same-day six-area-page/sitemap snapshot already produced by the audited pipeline; official BCIT catalog pages were independently confirmed to identify themselves as current listings.
- No ordinary programs were imported, updated, deactivated, or rewritten.
- Live HTTP status was not re-requested for every one of the 425 canonical entries in this certification pass; source status uses the same-day snapshot.
- The workspace root is not a Git checkout, so commit ancestry and repository diff cleanliness could not be certified.
- International eligibility remains unknown unless explicit structured evidence exists; legacy booleans were not promoted to structured evidence.
- Legacy curriculum and pre-governance records were measured but not bulk-migrated or re-audited.

## Audit tables

Detailed CSV evidence is under `program_extractor_audit/catalog_certification/`, including program-by-program reconciliation, duplicate identities, course references, admissions, curriculum, governance, provenance, campus/delivery, international evidence, aliases, and holdbacks.
