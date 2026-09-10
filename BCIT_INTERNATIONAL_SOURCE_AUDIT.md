# BCIT International Eligibility Source Discovery Audit

Generated: 2026-09-08T17:27:13.137422+00:00

## Decision

BCIT publishes two authoritative, systematic **positive** program-level sources: the [Full-time Cohort Learning Programs](https://www.bcit.ca/international-applicants/regular-credential-programs/) page and the [Flexible Learning Programs](https://www.bcit.ca/international-applicants/flexible-credential-programs/) page. Both embed a stable BCIT program ID, canonical program URL, and explicit international/PGWP flags. Their union positively identifies **265 of 374** active Asteris programs.

These lists do not govern negative eligibility. Absence from either list, or a missing icon on a listed row, remains unknown. Explicit restrictions and negative decisions must come from the exact individual program page. Combining the list positives with explicit individual-page restrictions yields **266 deterministic records** and leaves **108 unknown**.

No program data was updated in this audit.

## Exact result

| Normalized status | Programs |
|---|---:|
| `ACCEPTED_AVAILABLE` | 253 |
| `CONDITIONAL_RESTRICTED` | 12 |
| `NOT_ACCEPTED` | 1 |
| `UNKNOWN_NOT_PUBLISHED` | 108 |
| **Total** | **374** |

The 12 restricted records are the Specialty Nursing BSN options: applicants may complete them outside Canada or hold a valid work permit in Canada for the clinical period; they are study-permit ineligible, PGWP ineligible, and require program-head approval. The explicit negative is the main Nursing BSN (`8875BSN`).

## Source assessment

| Source | Authority and use | Stable identity | Coverage against 374 | Effective-date quality |
|---|---|---|---:|---|
| Full-time international list | Governing positive eligibility and positive PGWP flags | Program ID + canonical URL | 110 listed; 109 positive | Retrieved 2026-09-08; flags have no published effective date |
| Flexible Learning international list | Governing positive eligibility and positive PGWP flags | Program ID + canonical URL | 176 listed; 173 positive | Retrieved 2026-09-08; flags have no published effective date |
| Combined international lists | Best systematic positive source | Program ID + canonical URL | 265 deterministic positives | Snapshot date only |
| Individual program pages | Highest authority for exact negative/conditional restrictions | Canonical URL with program ID | 374 pages represented in retained current audit snapshots; 16 publish explicit evidence | Retrieval timestamp; text generally lacks an effective date |
| Program Availability | Governs application status and explicit Domestic Only rows for an exact mode/intake | Canonical URL + mode + intake | 223 programs; 48 contain a Domestic Only row | Intake-specific; BCIT says availability is approximate |
| Study permit / PGWP policy pages | General immigration context only | No program identity | 0 program-level classifications | Updated pages, but cannot determine a program |

The full-time page contains one listed row without an international flag (`7485DIPMA`); the Flexible page contains three (`5180PADVDIP`, `5430ACERT`, `5430CERT`). Their icon absence is not a negative decision, so they stay unknown unless another explicit source governs them.

## Conflicts and scope

There are **0 direct contradictions** between a positive international-list flag and an individual page saying the same program is not accepted. The 12 Specialty Nursing list positives are **scope refinements**, not contradictions: the program pages add outside-Canada/work-permit-only, study-permit, PGWP, and approval restrictions.

The Program Availability page covers 223 active programs and contains explicit `Domestic Only` rows for 48 matched programs. Those rows are mode/intake-specific. They must be attached to the exact offering and must not turn a program-level positive into a blanket negative. BCIT also states that application availability is approximate and directs international eligibility questions to its International Applicants pages.

The WordPress page metadata reports modification dates of 2025-01-09T18:38:09 for the full-time list and 2025-01-09T18:37:16 for the Flexible list, even though the program records are rendered dynamically. Therefore the audit date and source hash are the reliable snapshot markers; BCIT does not publish per-flag effective dates.

## Recommended vocabulary

Use a program-level decision separate from immigration and offering restrictions:

- Program: `ACCEPTED_AVAILABLE`, `NOT_ACCEPTED`, `CONDITIONAL_RESTRICTED`, `UNKNOWN_NOT_PUBLISHED`.
- Study permit: `REQUIRED`, `ELIGIBLE`, `INELIGIBLE`, `NOT_REQUIRED_DISTANCE_OR_SHORT_STUDY`, `UNKNOWN_NOT_PUBLISHED`.
- PGWP: `ELIGIBLE_TO_APPLY`, `INELIGIBLE`, `CONDITIONAL`, `UNKNOWN_NOT_PUBLISHED`.
- Restrictions: `OUTSIDE_CANADA_ONLY`, `VALID_WORK_PERMIT_REQUIRED`, `PROGRAM_HEAD_APPROVAL_REQUIRED`, `DOMESTIC_ONLY_INTAKE_OR_MODE`, `WORK_COMPONENT_UNAVAILABLE`.

`PGWP` should always mean BCIT says the program is eligible for a student to apply; final issuance remains an IRCC decision.

## Precedence and effective dates

1. Use current explicit text from the exact individual program ID/URL for negative or conditional restrictions.
2. Otherwise accept a current positive international flag from either BCIT international program list.
3. Apply Program Availability `Domestic Only` evidence only to its exact mode and intake.
4. Use generic study-permit and PGWP pages only to explain policy; never derive program status from them.
5. Preserve unknown when evidence is absent. Never infer from delivery, campus, credential, list absence, or a missing icon.
6. Store retrieval time and source hash. If equally scoped evidence conflicts, use a published effective date when present; otherwise prefer the later retrieval and retain both records for review.

## Schema fit

No migration is required for the proposed program-level enrichment. `program_delivery_facts` can store the normalized eligibility text, authoritative raw evidence, source URL, and check date. `academic_rule_sets` already stores multiple `INTERNATIONAL` conditions with evidence. `program_offerings.notes` can retain a dated Domestic Only restriction.

There is one modeling limitation: `program_offerings` has no international-specific field, and `program_delivery_facts` has no separate structured study-permit or PGWP columns. An additive migration is recommended later only if those dimensions must be queried directly rather than represented as `INTERNATIONAL` rules and provenance text.

## Nursing spot check

All **13/13** requested records were fetched from their live BCIT pages on 2026-09-08. The 12 Specialty Nursing pages still publish the same outside-Canada/work-permit-only, study-permit-ineligible, PGWP-ineligible, program-head-approval conditions already stored in Asteris. The main BSN page still says it does not accept international applications. **No discrepancy was found and no correction was made.**

## Recommended enrichment run

Process the **266 deterministic records** in batches of 50: five batches of 50 and a final batch of 16. Before each batch, re-fetch and hash the two list sources and every program page supplying a restriction. Join by exact program ID and verify canonical URL; apply program-page restrictions first, list positives second, and dated offering restrictions third. Generate a pre-apply diff, leave all 108 unknowns untouched, then run focused international integrity checks and the full regression suite after each batch.

Exact next step: implement a read-only planner that consumes `program_coverage.csv`, emits idempotent proposed rows for `program_delivery_facts` and `academic_rule_sets`, and stops on any URL mismatch, changed source hash, or unexplained conflict. Review that diff before authorizing the separate enrichment phase.

## Audit tables

- `program_coverage.csv` — all 374 active programs and the deterministic decision basis.
- `source_summary.csv` — authority, identity, coverage, and date quality by source.
- `availability_offerings.csv` — current BCIT mode/intake application rows and Domestic Only scope.
- `conflicts_and_refinements.csv` — direct conflicts, refinements, and intake/mode scope notes.
- `nursing_spot_check.csv` — live 12 Specialty Nursing plus main BSN comparison.
