# BCIT Specialty Nursing family extraction audit

Audit only — no program or course data was imported.

## Summary

- Extracted successfully: 12/12
- Unique course references: 91
- Existing / missing-unresolved: 91 / 0

## Program comparison

| Program | Courses | Existing | Missing | Clinical/practicum |
|---|---:|---:|---:|---|
| 810KBSN | 16 | 16 | 0 | NSCC7420, NSER7500 |
| 810ABSN | 16 | 16 | 0 | NSCC7420, NSCC7620 |
| 810NBSN | 17 | 17 | 0 | NSCC7420, NSER7300, NSER7500 |
| 810BBSN | 18 | 18 | 0 | NSER7300, NSER7500 |
| 810MBSN | 19 | 19 | 0 | NSHA7300, NSSC7000 |
| 810CBSN | 20 | 20 | 0 | NSNE7300, NSNE7900, NSSC7000 |
| 810DBSN | 19 | 19 | 0 | NSNN7300, NSNN7500, NSNN7700 |
| 810QBSN | 16 | 16 | 0 | NSPE7310, NSPE7410 |
| 810FBSN | 32 | 32 | 0 | NSPE7300, NSPE7500, NSPE7900, NSSC7000 |
| 810SBSN | 22 | 22 | 0 | NSPN7300, NSPO7330 |
| 810GBSN | 27 | 27 | 0 | NSPN7300, NSPN7500, NSPN7736 |
| 810HBSN | 23 | 23 | 0 | NSPO7350, NSPO7540, NSPO7550, NSPO7740, NSPO7750 |

## Shared and variant structure

Courses shared by all 12: BUSA7250, COMM7100, LIBS7021, NSSC7115, NSSC8000, NSSC8300, NSSC8500, NSSC8600, NSSC8800.

BCIT exposes twelve authoritative program identifiers and pages. Keep twelve independent program records, with reusable shared rule/course-pool objects where duplication is proven. A base/variant inheritance redesign is not justified before the current architecture has override semantics.

## Rule and model gaps

- `advanced_placement_transfer_plar` — storable/representable but not yet executable (12 programs)
- `clinical_placement_eligibility` — requires schema/model extension (5 programs)
- `clinical_practice_hours` — requires schema/model extension (1 programs)
- `cohort_or_sequence` — requires schema/model extension (12 programs)
- `completion_time_limit` — storable/representable but not yet executable (4 programs)
- `course_prerequisite` — already fully supported and executable (12 programs)
- `curriculum_all_listed_courses` — already fully supported and executable (12 programs)
- `curriculum_minimum_credits_from_pool` — storable/representable but not yet executable (5 programs)
- `employer_site_requirement` — should remain authoritative raw text + human confirmation (6 programs)
- `health_safety_clearance` — should remain authoritative raw text + human confirmation (12 programs)
- `professional_registration_licensure` — storable/representable but not yet executable (12 programs)
- `specialty_employment_experience` — storable/representable but not yet executable (12 programs)

## Option-specific course differences

- critical care combined vs standard — combined_only: NSER7410, NSER7500; standard_only: NSCC7520, NSCC7620
- emergency combined vs standard — combined_only: NSCC7320, NSCC7420; standard_only: NSER7250, NSER7800, NSSC8130
- pediatric critical care vs standard — critical_care_only: NSPE7260, NSPE7270, NSPE7280, NSPE7290, NSPE7310, NSPE7410; standard_only: NSCC7150, NSNE7100, NSNE7200, NSPE7200, NSPE7300, NSPE7360, NSPE7380, NSPE7500, NSPE7600, NSPE7800, NSPE7801, NSPE7900, NSPN7100, NSPN7150, NSPN7450, NSPN7720, NSPN7735, NSSC7000, NSSC8110, NSSC8120, NSSC8130, NSSC8160
- perinatal perioperative vs standard — perioperative_only: NSPN7400, NSPO7230, NSPO7330, NSPO7430; standard_only: NSPN7150, NSPN7500, NSPN7710, NSPN7720, NSPN7735, NSPN7736, NSPN7741, NSPN7750, NSPN7755

## Missing/unresolved course references



## Recommended first import

810ABSN (Critical Care — Standard Option): it is a standard rather than combined option, making it the smallest clean test of nursing registration, specialty admission, curriculum, and clinical/practice semantics before nested cross-specialty option logic is introduced.
