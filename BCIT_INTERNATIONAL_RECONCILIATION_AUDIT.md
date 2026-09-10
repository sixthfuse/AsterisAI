# BCIT International Eligibility Reconciliation & Blocker Review Audit

Run date: 2026-09-08

## Certification

**BCIT International Eligibility Data Foundation — CERTIFIED COMPLETE FOR ALL PUBLISHED DETERMINISTIC EVIDENCE**

The 374 active programs reconcile exactly: **253 accepted/available + 12 conditional/restricted + 1 not accepted + 108 unknown/not published + 0 blocked = 374**. The deterministic structured count is **266**. Rule-only evidence is normalized equivalently to delivery-fact-backed evidence.

The 108 unknown/not-published programs are explicitly documented non-errors: no authoritative published deterministic evidence was found, and no negative status was inferred from silence.

## 220 → 217 discrepancy

Batch 04's helper used `facts.get(pid) != UNKNOWN_NOT_PUBLISHED`. For a missing delivery-facts row, `facts.get(pid)` returns `None`, and `None != UNKNOWN_NOT_PUBLISHED` is true. It therefore counted **8660BENG, 8800BTECH, and 8900BTECH** as deterministic even though each had neither a delivery-facts row nor an INTERNATIONAL rule before Batch 05. The normalized count was 217. Batch 05 then legitimately inserted their missing facts and evidence as part of its approved scope. No data was changed merely to reconcile the reports.

## Six-blocker review

All six blockers are resolved. 6130DIPMA's old official URL redirects to the same exact program ID with the renamed `television-and-video-production` canonical path. The four Specialty Nursing legacy URLs remain HTTP 200 aliases and declare exact-ID canonical paths that add `distance-and-online-learning`; their program-specific conditional eligibility, study-permit ineligibility, PGWP ineligibility, and program-head approval text remains authoritative. M600MSC's exact live program page states that the program is available to international applicants, requires a valid BCIT study permit before starting, and is eligible for students to apply for a PGWP.

The correction updated only exact source URLs and the two missing structured evidence records (6130DIPMA and M600MSC). It made **13 database row changes**. Immediate replay proposed/applied **0 changes**. No schema migration or advisor/routing change occurred.

The post-reconciliation planner reports **0 ready, 0 blocked, and 266 unchanged**, with identical deterministic replay. Focused international tests passed **41/41** and the full Python regression suite passed **470/470**. Browser-state tests were not required because no shared advisor or routing code changed.

## Integrity results

- Source drift: 0
- Exact duplicate INTERNATIONAL rows: 0
- Active programs / courses: 374 / 3976
- Resolved / remaining blockers: 6 / 0

Evidence tables are under `program_extractor_audit/international_reconciliation/`.
