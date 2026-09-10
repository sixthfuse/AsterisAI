# Mixed BCIT Batch Scalability Test 01

Run date: 2026-09-07

Baseline: 25 active programs and 1356 courses. Final: 36 active programs and 1620 courses.

Result: 6 of 12 required no custom engineering, 5 required the small generalized connector/pathway adapter, and 1 was held back. 11 programs were activated. Exactly 264 newly validated BCIT courses were imported.

| Program | Credential | School/domain | Shape | Status | Custom code | Missing courses | Import | Active revision | Hash | Zero diff |
|---|---|---|---|---|---|---:|---|---:|---|---|
| 6575DIPMA — 3D Modeling, Art and Animation | Diploma | School of Business + Media | portfolio/design and competitive departmental assessment | GREEN | none | 28 | active | 221 | d2476578096e418d4f6fc9730c2c504bc894051c65fe49bc1bd3d02e3ec546b8 | True |
| 6615DIPMA — Medical Laboratory Science | Diploma | School of Health Sciences | non-Nursing health and 35-week clinical placement | GREEN | none | 30 | active | 222 | 700937d87a5f481efe77330799751eba4338269d84f61bac1e1a84caba250ce4 | True |
| 3790APPR — Industrial Electrician | Apprenticeship | School of Construction and the Environment | trades/apprenticeship with external sponsorship and hours | RED | held: official matrix has levels and training credits but no course identifiers | 0 | held |  |  | False |
| 6045PDIPMA — Finance | Diploma | School of Business + Media | business/finance with repeated course alternatives | YELLOW | generalized connector-aware alternative grouping | 20 | active | 223 | 1e6f330bf9fc4febbd2bbb8cd5c6e8409d7c89ef9128dd4e6194867969ad91ba | True |
| 0826CM — Technical Communication Essentials | Microcredential | School of Computing and Academic Studies | short microcredential with elective credit pool and laddering | GREEN | none | 4 | active | 224 | 59ac56804d8aefbebf070392463a031c288ff754d8c097fd276c8be31cc03f2f | True |
| 5500PDIPLT — Computer Systems | Diploma | School of Computing and Academic Studies | part-time/Flexible Learning with prior-credential block and elective pools | YELLOW | generalized non-course component and constrained-pool preservation | 12 | active | 225 | 81c1c14537f6a2681c59f5ad366766ecd65c1ecd02da7923515d8c56497ec442 | True |
| 5500DIPMA — Computer Systems Technology | Diploma | School of Computing and Academic Studies | technology diploma with co-op and twelve option pathways | YELLOW | generalized named-pathway grouping and optional co-op handling | 65 | active | 226 | 9429fbbccdd7f8f6b15e0242872fc3e2f2ace89dc76d4718671637c357631f85 | True |
| 6220FDIPMA — Interior Design | Diploma | School of Construction and the Environment | advanced placement/laddering plus portfolio and entrance project | GREEN | none | 5 | active | 227 | e0b6ae7f08c80d2bd4d9ffe284f4c6356a965e3fcfdd408d103e261557d585f0 | True |
| 6635DIPMA — Medical Radiography | Diploma | School of Health Sciences | clinical-practicum-heavy health program | GREEN | none | 30 | active | 228 | ed8309c8c614173ca6669d450f844370b2d0e5f148419cc70bb6bb70a27b7d7b | True |
| 635DDIPLT — Mechanical Engineering Technology (Mechanical Design Option) | Diploma | School of Energy | diploma/degree continuation alternatives | YELLOW | generalized named-pathway grouping | 28 | active | 229 | 453b8cca90cca30075730af2209428cd7e2a9295767f6d79920548034eeb7ec1 | True |
| 6595DIPMA — Graphic Design and Interactive Media | Diploma | School of Business + Media | Flexible Learning with internship, portfolio and advanced entry | GREEN | none | 8 | active | 230 | 194fc104fe2a9b218ae54c258877c02d0e8a4cd57c532965378469add82f25e7 | True |
| 7140DIPMA — Architectural and Building Technology | Diploma | School of Construction and the Environment | elective courses and grouped pathways | YELLOW | generalized connector-aware elective/pathway grouping | 35 | active | 231 | 8022666f85037a434089453f5dbf7c21e58de4c4d34bec574ec593a62aaf1949 | True |

## Generalized findings

The existing database schema and governed contract accepted flat curricula, credit pools, clinical courses, and human-confirmed institutional decisions. This batch added one reusable connector-aware normalization layer for published `or` alternatives, named option pathways, prior-credential blocks, and optional co-op structures. Ambiguous institutional choices remain non-executable.

Industrial Electrician is RED because the official program matrix publishes four apprenticeship levels and 80 training credits without BCIT course identifiers. Importing it would require a governed apprenticeship-level/training-hours model rather than fabricated courses.

No schema migration was required. Existing active programs were not rewritten.

## Final validation

Python regression suite: 411 passed. Browser-state suite: 5 passed. Every active program has a normalized ADMISSION rule set; all 264 new courses have BCIT institution ownership.
