# Mixed BCIT Batch Scalability Test 02

Run date: 2026-09-08

## Outcome

All 24 official BCIT candidates were imported and activated through exact-hash governance. The catalog moved from 36 to 60 active programs and from 1,620 to 2,103 courses. No schema migration was required and no existing active program was rewritten by the importer.

- GREEN: 14/24 (58.33%)

- YELLOW: 10/24 (41.67%)

- RED: 0/24 (0.00%)

- Imported: 24; held: 0

- Flat existing path with no adapter: 14

- Existing Batch 01 connector/pathway adapter, with no new code: 10

- Genuinely new generalized adapter or extension: 0

- Programs requiring zero new custom engineering: 24

## Course reconciliation metrics

The 24 imported programs had 489 missing-course references in total when counted per program (20.375 per imported program). After cross-program deduplication, 483 unique official courses were validated and added (20.125 unique new courses per imported program). Thus, six missing references overlapped across candidates.

## Per-program audit

| Program | Credential | School/domain | Shape | Status | Custom-code classification | Missing | Import | Revision | Exact hash | Zero diff | Warnings/blockers |
|---|---|---|---|---|---|---:|---|---:|---|---|---|
| A600GRCERT — Business Analytics | Graduate Certificate | School of Business + Media | graduate cohort, capstone, laddering, subjective admissions | GREEN | none | 6 | active | 244 | 281814708d356b3526f80cce7f342f68e511748ca690dcfb8940d447f3b24da8 | True | none |
| 7985ACERT — Business Fundamentals | Associate Certificate | School of Business + Media | short full-time cohort with two laddering/advanced-placement options | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 8 | active | 245 | befd0c2b10d505b6a2287f12e8495cd1b313c7c8bf994300d1a4e2661674782b | True | none |
| 9975BBA — Bachelor of Business Administration | Bachelor of Business Administration | School of Business + Media | degree completion, advanced placement, electives and pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 18 | active | 246 | b499d4964a156d6d47ab82ee094ebeb63cf2fd8a9b0b97d8c72fde8c10daa67b | True | none |
| 6385ACERT — Digital Marketing Strategy | Associate Certificate | School of Business + Media | Flexible Learning marketing certificate with flat current curriculum | GREEN | none | 0 | active | 247 | 39756c6f57c9aede2ebc70bca215e684398507d90f03347670be8a167304f3ab | True | none |
| 6130DIPMA — Television & Video Production | Diploma | School of Business + Media | media cohort, project work and industry practicum | GREEN | none | 25 | active | 248 | fad8e6399ca05af753b79eefb08e36a583dc8d129655e026f6289214912f6aa5 | True | none |
| 5240ADVDIP — Technical Arts | Advanced Diploma | School of Business + Media | advanced diploma with portfolio and production project | GREEN | none | 15 | active | 249 | bed7c9ccc5b04a183f6d24f4701085db7363efd28535d3017530bc145f8f04ff | True | none |
| 5540DIPMA — Computer Information Technology | Diploma | School of Computing and Academic Studies | computing cohort, option electives and co-op | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 30 | active | 250 | 333f19eb9746fe1989ff316523567e3e87c7756b72b742f38755cc9f03031be5 | True | duplicate course reference normalized during import: ACIT2911; duplicate course reference normalized during import: ACIT4770 |
| 6535CERT — Front-End Web Developer | Certificate | School of Computing and Academic Studies | intensive computing certificate with portfolio | GREEN | none | 13 | active | 251 | 6d3846c5fc4498e12a60c8c5a1c007009bcefd4921f5c9858539329ac91553b4 | True | none |
| 8030BENG — Electrical Engineering | Bachelor of Engineering | School of Energy | engineering degree with diploma entry and electives | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 62 | active | 252 | 79ff3c34ef1b377a80991c10e8f0611530afe0b665e8d95f691748153b537b74 | True | none |
| 8020BENG — Mechanical Engineering | Bachelor of Engineering | School of Energy | engineering degree continuation and capstone | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 23 | active | 253 | d8b118f7bcdeb53ccd7dd154fc23211625fbd00a0aa383f6b227e93c07693797 | True | none |
| M500MENG — Smart Grid Systems and Technologies | Master of Engineering | School of Energy | graduate degree with capstone/elective alternatives | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 5 | active | 254 | 705929335b6d8992bb088ad5ee35b2c8db919c01c522f9f5f3aa17057bb3d37a | True | none |
| 0876CM — Applied Mass Timber Engineering | Microcredential | School of Construction and the Environment | engineering microcredential for experienced professionals | GREEN | none | 4 | active | 255 | 580c3d4d07c508918eec661f790ce90d4b8b971660e44af19176fadf6cd424f0 | True | none |
| 5670ADVDIP — Clinical Genetics Technology | Advanced Diploma | School of Health Sciences | post-credential health program with clinical practicum | GREEN | none | 17 | active | 256 | 4b30b0eee2f4a18cc4e4d01255dd9464c748e52ddbeb4502cbd29ae13c2ccf3c | True | none |
| 576ADIPMA — Diagnostic Medical Sonography (General Sonography Option) | Diploma | School of Health Sciences | health option diploma with clinical placements | GREEN | none | 26 | active | 257 | 51e35fa427e766e57889c8d2364d081a9d897dd8c4ec661cbfe4d03203abf851 | True | none |
| 8520BENVH — Environmental Public Health | Bachelor of Environmental Public Health | School of Health Sciences | health bachelor with practicum, advanced entry and Liberal Studies pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 26 | active | 258 | d0af5cd94e483228010f2e920c5d0eab2020cd77b06f0b516f16398aa059dbb2 | True | none |
| 6705DIPMA — Nuclear Medicine | Diploma | School of Health Sciences | regulated health diploma with clinical terms | GREEN | none | 32 | active | 259 | a8847e07e72c6cced0772e3533e2b5bd0334b20e8f763f6c25fdcabbc306eb2a | True | none |
| 100ADIPMA — Airline and Flight Operations Commercial Pilot (Fixed-Wing) | Diploma | School of Transportation | aviation diploma combining academic and external flight training | GREEN | none | 38 | active | 260 | 85291ba7138b91ff911ffab182452e51bd5cb055c2452f2585b738b4163891f1 | True | none |
| 2536DIPMA — Nautical Sciences | Diploma | School of Transportation | marine diploma with identifiable courses and alternating co-op sea terms | GREEN | none | 22 | active | 261 | b46fb59c055ea44d71ef4acccf1566866f607dfa6c188cbb4b118f6dd3db7cfe | True | none |
| 2942DIPMA — Marine Engineering | Diploma | School of Transportation | marine engineering diploma with identifiable courses and co-op sea service | GREEN | none | 36 | active | 262 | 893f08146ce0a1e4c8f81ac074407ba04fb80b45d6c65f46a0dc51fde5018b34 | True | none |
| 2430DIPMA — Power and Process Engineering | Diploma | School of Energy | energy diploma with power-engineering certification | GREEN | none | 40 | active | 263 | 288f022de8fe90d8db1706b534a801f011e51b2586af73a109f5ecb453536e7e | True | none |
| 8050BTECH — Architectural Science | Bachelor of Architectural Science | School of Construction and the Environment | architecture degree with competitive continuation and electives | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 17 | active | 264 | c255408535c221e69175d477df4866ad3c48694df015a7fd2e826471a0ae5431 | True | none |
| 6140DIPMA — Residential Interiors | Diploma | School of Construction and the Environment | Flexible Learning design diploma with laddering and electives | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 14 | active | 265 | 4c86e4d218432047359425dec035fbb65265189a7715b66b196dfd7beddc93bc | True | none |
| 0864CM — Marine Business Essentials | Microcredential | School of Transportation | short marine business Flexible Learning microcredential | GREEN | none | 10 | active | 266 | 123b206b05e384dd10af9a6299aa7c6394eb3926dd72539b85e57a1b85ac73b7 | True | none |
| 5512CERT — Applied Data Analytics | Certificate | School of Computing and Academic Studies | Flexible Learning analytics certificate with elective choices | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 267 | 516d6361e134b7c25200d546820370147c0442f22f827d15160899c99b578aff | True | none |

## Scalability finding

Batch 02 required proportionally less new custom engineering than Batch 01. Batch 01 introduced a new generalized adapter for 5/12 candidates (41.67%); Batch 02 introduced no new adapter for 0/24 candidates (0.00%). Fourteen candidates used the flat governed path and ten reused the Batch 01 adapter unchanged. All subjective admissions, institutional choices, pathways, and non-course clinical requirements remain human-confirmation-only rather than executable claims.

The only generalized application safeguard added after catalog expansion prevents generic single words such as “information” or “clinical” from changing the active program. Exact names, IDs, and governed aliases are unchanged. This prevents academically wrong answers directly caused by the newly imported catalog entries.

## Final validation

- Exact-hash approved active revisions: 24/24

- Post-import zero diff: 24/24

- Unresolved batch course references: 0

- Active programs without normalized ADMISSION rules: 0/60

- Newly validated courses with incorrect institution ownership: 0

- Python regression suite: 414 passed, 0 failures, 0 errors

- Browser-state suite: 5 passed, 0 failures, 0 errors
