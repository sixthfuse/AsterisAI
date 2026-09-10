# Legacy / Pre-Governance Program Re-Audit

Run date: 2026-09-08

## Result

All **19** authoritative pre-governance programs were re-audited. **19** now have active governed revision pointers; **0** were held.

Factual corrections: **0**. Provenance-only corrections: **1**. New courses: **0**. International mismatches: **0**.

Classification counts are aspect flags and may overlap: NO_CHANGE **19**, STALE_DATA **0**, MISSING_DATA **0**, STRUCTURE_GAP **0**, PROVENANCE_GAP **19**.

## Exact 19-program set

| Program | Stored title | Classifications | Revision | Hash | Zero diff |
|---|---|---|---:|---|---|
| 0816CM | Applied Circular Economy: Zero Waste Buildings | NO_CHANGE, PROVENANCE_GAP | 678 | `4922eeb9e89a609d86a093bb354c20098cb73e4e056abcbde4feacf97869f58a` | yes |
| 5410DIPLT | Civil Engineering Diploma | NO_CHANGE, PROVENANCE_GAP | 680 | `5809f95e1b4506ec12be48bc0c46d0a545ce70b229b51554e30b17be66e45a8a` | yes |
| 810ABSN | Specialty Nursing (Critical Care - Standard Option), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 682 | `82375ca18afc41a4be8dbafd707d40bb77391748921101a741f44ea91e393412` | yes |
| 810BBSN | Specialty Nursing (Emergency - Standard Option), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 684 | `f74199a2bee6a419f3cfd22763cdeab40aad225ad15ba59da0567f40c9ce597c` | yes |
| 810CBSN | Specialty Nursing (Neonatal), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 686 | `e77ac3c6c517f1c4c1a4b72bc90626c6881a4c4c8a93edb2a54caae28da69734` | yes |
| 810DBSN | Specialty Nursing (Nephrology), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 688 | `d194bbb1b96914d37211acb9e5dd9d74ac437fff0f23925cbaf20880b78f0dd2` | yes |
| 810FBSN | Specialty Nursing (Pediatric - Standard Option), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 690 | `51e15c51794fbe5d8ec64510c619a2d6d9af980a8483a33aea32004ba4f6eb18` | yes |
| 810GBSN | Specialty Nursing (Perinatal - Standard Option), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 692 | `5e4f70ccdf4a62c397bdeb3d004a68425018f8daec595e9e3808b105f00cd585` | yes |
| 810HBSN | Specialty Nursing (Perioperative), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 694 | `576520a6f7a6bf55160190e8ee53534cfebcd4fc2b1359a2f3eefb5f11228268` | yes |
| 810KBSN | Specialty Nursing (Critical Care - Combined Critical Care/Emergency Option), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 696 | `6836157edb584dbfd797b488c1a356450e2ee5cb7311448c3cdd154e34771d46` | yes |
| 810MBSN | Specialty Nursing (High Acuity), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 698 | `fb5218fac538f8e92ce1dd26b2dfb3ec7eac0b9ac34146ef4ba3acc78a1eef67` | yes |
| 810NBSN | Specialty Nursing (Emergency - Combined Emergency/Critical Care Option), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 700 | `f098be7721547a0762faf0d3aa56e52f5a4b7ae38393ea45534fe37b53eaff2b` | yes |
| 810QBSN | Specialty Nursing (Pediatric - Critical Care Option), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 702 | `006c9b6d1dd71999feacb6f206ff61a3b474f45d04b199bd67fb59342f8b54ae` | yes |
| 810SBSN | Specialty Nursing (Perinatal - Perioperative Option), Bachelor of Science in Nursing, Part-time | NO_CHANGE, PROVENANCE_GAP | 704 | `1c5c31af67df8f3843a566b3465cafde7674c2041873cbcb94989d3b9f6aad5e` | yes |
| 8660BENG | Civil Engineering Bachelor of Engineering | NO_CHANGE, PROVENANCE_GAP | 706 | `184a011fd068765939c4be8991b1a778eb41cd19706ef3902ceba73180474aaf` | yes |
| 8800BTECH | Construction Management | NO_CHANGE, PROVENANCE_GAP | 708 | `13950881d5c53be36e78358c463dbe9f9351075e98a27dbf7586171b3206157e` | yes |
| 8875BSN | Nursing, Bachelor of Science in Nursing, Full-time | NO_CHANGE, PROVENANCE_GAP | 710 | `53bb6227bcdebbf8d47c3a52cdcc1f7538e8059be3d5807a9abc7519daef0158` | yes |
| 8900BTECH | Electronics | NO_CHANGE, PROVENANCE_GAP | 712 | `5cf60450dd4cc8e6b53d3ec00ae762f6da02682d7685b10518921426f28ade96` | yes |
| M600MSC | Applied Computing | NO_CHANGE, PROVENANCE_GAP | 714 | `0bdfc9a6c0432796bbe7ce52bc78b952905a4009d741fbcef586477bc2d8925c` | yes |

## Governance and integrity

Active programs/courses: **374 / 3976**.
Active governed revision coverage: **374 / 374**.
Remaining active pre-governance programs: **0**.

Every accepted payload was exact-hash approved, inserted once, replayed with no new revision, activated, and compared with the post-activation materialized state. Governance rows do not rewrite curriculum, course, rule, alias, relationship, or routing data.

## Human-confirmation boundaries

Published competitive decisions, clinical or professional verification, transfer/PLAR decisions, program-head approvals, and immigration decisions remain preserved as source-backed human-confirmation boundaries. No apprenticeship or advisor-language architecture was introduced.

## Testing

Focused legacy re-audit: **7/7 passed**, 0 failed, 0 errors.
Full Python regression: **477/477 passed**, 0 failed, 0 errors.
Browser-state suite: **not required** because shared routing/advisor code did not change.
