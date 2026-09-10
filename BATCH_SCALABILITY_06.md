# BCIT Catalog Ingestion Batch 06

Run date: 2026-09-08

## Outcome

Processed all 65 legitimate candidates remaining from the authoritative 165-program import universe after Batch 05. Imported 65; held 0.

- GREEN: 38/65 (58.46%)

- YELLOW: 27/65 (41.54%)

- RED: 0/65 (0.00%)

- Flat pipeline: 38

- Reused Batch 01 adapter: 27

- Genuinely new generalized extensions: 0

- Schema migrations: 0

## Selection and discovery

The official sitemap contained 489 program URLs. All 65 remaining authoritative candidates were refreshed immediately before contract generation. The three same-name, same-credential entries deferred by Batch 05 were included because their canonical IDs and study modes establish distinct legitimate programs.

Known apprenticeship structures, non-program entries, and the two prior RED holdbacks were excluded. No selected candidate became RED after refresh.

The live PostgreSQL baseline exactly matched the user-provided 309 active programs and 3,597 courses. The 373-program strict current universe and 374 no-cleanup total remain reconciled by retaining live-but-unlisted 5325ACERT.

## Course reconciliation

The candidates referenced 430 courses missing at audit time when counted per program. After validation and deduplication, 379 unique official BCIT courses were imported (5.831 per imported program). Cross-program overlap eliminated 51 duplicate missing-course references.

## Per-program audit

| Program | Credential | School/domain | Structural shape | Class | Adapter/custom code | Missing | Import | Revision | Exact hash | Zero diff | Warnings/blockers |
|---|---|---|---|---|---|---:|---|---:|---|---|---|
| 0800CM — Introductory Studies in Mass Timber Construction | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 0 | active | 565 | 07ffc6b5dba5e1ba3f81999a13e8e65c5c9c6aac5ed4c0bb2000a89476eb917a | True | none |
| 0801CM — Essentials of Natural Resource and Environmental Protection (MENREP) | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 7 | active | 566 | c69d34f6cec82fb683a6075f5190756a59764e192f595bc216f71f4e206f9eb3 | True | none |
| 0803CM — Script Supervision and Continuity for Film and TV | Microcredential | School of Business + Media | microcredential with flat published curriculum | GREEN | none | 5 | active | 567 | ba84bf374231f7b3194fe0619c9293cbdcfe70b26539de95d10b502c7f20624b | True | none |
| 0814CM — Essential Field Skills for Environmental Professionals | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 4 | active | 568 | fc7573526e1fca3a807207c6d401e6f6b8e212b979345879d1fe0b65cac59961 | True | none |
| 0815CM — Supervising Net-Zero and Passive House Construction | Microcredential | School of Construction and the Environment | microcredential with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 569 | b483eb0ee5909f6ad9252171cca52535b588727e4e9eefa95c09278d3fe1c813 | True | none |
| 0817CM — Introduction to Forest Health Quantification with RPAS | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 2 | active | 570 | ca15cb97bffe418f576f7b0f21d837f3c75fbfa4472bda97af5e703e452f624c | True | none |
| 0819CM — Essentials of Net-Zero and Passive House Construction | Microcredential | School of Construction and the Environment | microcredential with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 571 | ad456059859621d3da89a2e241bc922639c07fc7ebcd73ae2cea517e1f34f98a | True | none |
| 0830CM — Whole-Building Life Cycle Assessment Professional | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 2 | active | 572 | e7a4d26af2ac1624cda977ddfeed05d245f3bbf5806a7553eaccb9bb5afb9d02 | True | none |
| 0836CM — Drone Applications for Environmental Risk Assessment | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 0 | active | 573 | 698ab97ba7728e66dd7f6c7f862f4f2e49db51d524210dc57b00b044d39be271 | True | none |
| 0853CM — Principles of Regenerative Building | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 3 | active | 574 | a1a4895df4da3e5fdb8aa41f0a23bb07b27c7a0cb81ab0710261261f93a64047 | True | none |
| 0854CM — Essentials of Community Energy and Emissions Management | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 6 | active | 575 | a4e1eede673be1d3d09cbfe32ef8d1b6dfbe1cd58c331c189874b41b13a32c7b | True | none |
| 0856CM — Retrofit Solutions for Rural Communities | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 2 | active | 576 | 96b9f5b901f32352cf6d5a10a96661ca14fdfe27466ace739a66f87ebd86f3ed | True | none |
| 0859CM — Sexual and Reproductive Health Foundations | Microcredential | School of Health Sciences | microcredential with clinical placement | GREEN | none | 0 | active | 577 | 2f862cf7de3c1e65bb314b3291d603de54bbefbd7e1fc3d4f2bad7e64879fc2a | True | none |
| 0861CM — Climate Changemakers Leadership Training | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 4 | active | 578 | 82aa92e41589c5796a0d3310cd702b13a29585e1fcbf22dd3c8be65453fe36ae | True | none |
| 0862CM — Residential Air to Air Heat Pump Specialist | Microcredential | School of Construction and the Environment | microcredential with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 4 | active | 579 | 97831c8549ca48d13858bca15656fc77eff5ddc325958faa3d9cf2e1e29a2fc6 | True | none |
| 0869CM — Occupational Health and Safety Essentials | Microcredential | School of Health Sciences | microcredential with flat published curriculum | GREEN | none | 0 | active | 580 | 56261e025f4125f868bdd9b336de647eb930b59abb79775a30053613a6838bb2 | True | none |
| 0870CM — Sexual Health Rehabilitation | Microcredential | School of Health Sciences | microcredential with clinical placement | GREEN | none | 0 | active | 581 | 7d28bbe9798f5d79c32e5471864cb7de30e086e366e654a164284c2ca7f5e04a | True | none |
| 0874CM — Fundamentals in Architecture, Construction, and Engineering | Microcredential | School of Construction and the Environment | microcredential with flat published curriculum | GREEN | none | 0 | active | 582 | d757c3e3dcf1e79904e5e44af58ba67a0dd4ebc2709fdd84ff8a58e7b4848fd1 | True | none |
| 5880DIPLT — General Insurance and Risk Management | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 16 | active | 583 | b3d30966146a9030143a124761bfdbc93a3fb7f86f1facc341103c28fba818b2 | True | none |
| 6035PDIPMA — Accounting | Diploma | School of Business + Media | diploma with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 584 | b3d3ca1bf61c2e87fd62d46c24f765e7f1569455b3c2ff613c864a3f6214b093 | True | none |
| 6045DIPMA — Finance | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 0 | active | 585 | 515968355b8086b402a68031404b49884871489931e2cdc67329642b3e6d685e | True | none |
| 6055DIPMA — Financial Planning | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 4 | active | 586 | b03986213c213e7e131bb843bc1ee4f7c0df7c66b82f0cc116aa15df17027023 | True | none |
| 6055PDIPMA — Financial Planning | Diploma | School of Business + Media | diploma with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 3 | active | 587 | 5f5832be5e6a3469078e7ee68df977f4f05ab85ad8ec1ee84dd45db7734a9dd7 | True | none |
| 6110DIPMA — Radio Arts and Entertainment | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 23 | active | 588 | a73463478f6c469d5c07118f6c8ff9e7efc47dffa6c381b05a19a63e5d7fccfc | True | none |
| 6220PDIPMA — Interior Design | Diploma | School of Construction and the Environment | diploma with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 589 | 0f58f76a3bd3d2876e5223efc5b19b1e4cb0fa82166d8e6c254dd47dfa185b4f | True | none |
| 623ADIPMA — Business Information Technology Management (Artificial Intelligence Management Option) | Diploma | School of Business + Media | diploma with non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 9 | active | 590 | d4d87baed9d473ed3983d3064a0dda37c255c13197dccdde03d576392b636527 | True | none |
| 623BDIPMA — Business Information Technology Management (Enterprise Systems Management Option) | Diploma | School of Business + Media | diploma with non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 11 | active | 591 | 3eeffb57871b47e7e13b5b2cbbb10c3d792139214c4cfc38f906d8e25aa66737 | True | none |
| 623CDIPMA — Business Information Technology Management (Analytics Data Management Option) | Diploma | School of Business + Media | diploma with non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 9 | active | 592 | c52dfec2d343b34dbc613ef1451efaca2ec0c7437981c058c20b17fed0de43cd | True | none |
| 6245DIPLT — Business Management | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 15 | active | 593 | 1bd826e84bafa703fd6a9b95b58e041ab3f049098340830203933842c74c7700 | True | none |
| 6245MCERT — Business Management | Certificate | School of Business + Media | certificate with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 594 | 8e23a6fbffe534befadd03b620d98934cddb155d2172c0edcfdf33d2760c3346 | True | none |
| 6247DIPMA — Graphic Communications | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 26 | active | 595 | 00c346d061add90d63f42a53d0edaf35033136b58f95bf06b5057028d92d3d71 | True | none |
| 625AMCERT — Human Resource Management | Certificate | School of Business + Media | certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 596 | a99c8f8a56bbece33d0009e87f96940230ecd1ae421d90b00134eb62f84483ee | True | none |
| 6285CERT — Fire Service Industry Leadership | Certificate | School of Business + Media | certificate with flat published curriculum | GREEN | none | 18 | active | 597 | 91a9ee3feffd2da94f2821ba20f858e23bb524a755f11c8ae82bcef8b0927626 | True | none |
| 6290DIPMA — Strategic Human Resources Management | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 18 | active | 598 | 9a9f01b59caaadd4ddb19cf9778f668a3c8a54bdb759a1b4f59e5445e7a29804 | True | none |
| 6300MCERT — Marketing Management | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 599 | 2854728b08c28b92ef5af386c4744978c90328b5bd5987165fecac60e3fceb58 | True | none |
| 630DMCERT — Marketing Management (Marketing Communications Option) | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 600 | 5ec06737bd3c287e56f0cd02a8dab08661ac4dff37af0289923b683c8215da91 | True | none |
| 630PMCERT — Media Techniques and Marketing Communications | Certificate | School of Business + Media | certificate with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 9 | active | 601 | ef5f0134ff604f52251ed7b847c229769a680c41eb246715a84795700d1fb38c | True | none |
| 630VMCERT — Marketing Management (Professional Sales Option) | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 602 | d1b8ec5e88eb3dc7a4cd23c7e497a6dccb928b7e5477b811c483b203bfc2581e | True | none |
| 6422DIPMA — Marketing Management | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 1 | active | 603 | c106c3ac949d493915383fbdeae1b21f02a6860988750e83606609d932ce31e3 | True | none |
| 642ADIPMA — Marketing Management (Digital Marketing and Brand Strategy Option) | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 12 | active | 604 | 2868d33ead60e8dcb92c2d66d2d53aeae35357b7204c1188134635e777c1dc49 | True | none |
| 642BDIPMA — Marketing Management (Professional Sales Option) | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 12 | active | 605 | c24f5c3fc141f5de3e9ff706bd9be4bae4ef0920690df1170f86b5dad3a1cd88 | True | none |
| 642CDIPMA — Marketing Management (Entrepreneurship Option) | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 15 | active | 606 | 5c627391069568c6e5e46ffddd56d2206fac9212137430aea94c65be4332c78c | True | none |
| 642DDIPMA — Marketing Management (Professional Real Estate Option) | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 14 | active | 607 | 29ae6b766c68cb388ce1853591ec4a8471a6213c84242a62533bf2dd458fd4cc | True | none |
| 642EDIPMA — Marketing Management (Tourism Marketing and Sales Option) | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 15 | active | 608 | 37ffd1277a68f524583e461541a11b5201e3fc8fb02ad957be95b0ce265c744b | True | none |
| 6450MCERT — Media Techniques for Business | Certificate | School of Business + Media | certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 10 | active | 609 | 26ac28fdf94d86e52eea7203bc15a40b95bce81204c21049bda486c6db75df16 | True | none |
| 6525DIPMA — New Media Design and Web Development | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 35 | active | 610 | 28cf613628dac58be6ddb1129500d69244a6dcd28b99b220a1af7b4a14a7d8d7 | True | none |
| 6585CERT — Graphic Design | Certificate | School of Business + Media | certificate with flat published curriculum | GREEN | none | 0 | active | 611 | 643f141b26110da86c2c4566bc955777606f909ea4940d61f5e9ea24db27ae4f | True | none |
| 6640DIPMA — Mineral Exploration and Mining Technology | Diploma | School of Construction and the Environment | diploma with flat published curriculum | GREEN | none | 5 | active | 612 | 07a1534499ab4517911acf5e36b827d3e57477f4ea09b5fd8504090801949dd8 | True | none |
| 690AMCERT — Operations Management (Industrial Engineering Option) | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 4 | active | 613 | 7c00948768eb8bdaae37bc3af311524f534e7b644a4a9bc6780df47232aefaa9 | True | none |
| 690BMCERT — Operations Management (Management Engineering Option) | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 614 | e3b3505be2687edcea08c0db339994b7fd2af0287e212e29fd34bc1fadfbc4bc | True | none |
| 690DMCERT — Operations Management (Materials Management Option) | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 4 | active | 615 | 55aceda1fa927709acf99a9e5bf741e689549f460cc6cf887b115806effea2bf | True | none |
| 690FMCERT — Operations Management (Facilities Management Option) | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 616 | 4c95bb794c95ce523280e7b06aa39161decebe9c7982a27cf6cc1c1fccebb279 | True | none |
| 6915DIPMA — Operations & Management Engineering | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 20 | active | 617 | b60c2fed603d0cd541a7443521bb9fd2f48dc06200bf75474379d117a031084d | True | none |
| 6945CERT — Quality and Process Management | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 618 | 6b71b687df41b67c4f664546a296e787729dbf51b2ee20407fdc83afd8c4c714 | True | none |
| 703BDIPMA — Business Administration (Global Studies Option) | Diploma | School of Business + Media | diploma with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 619 | 5a7c045a88a935c3c9cba744d3cbbd23847b40151d54dae924365834e4941cbd | True | none |
| 703CDIPMA — Business Administration (Human Resources Option) | Diploma | School of Business + Media | diploma with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 620 | 9cdbc6d3100615f012fc72665c222fbb05c24b6ba8c2f1813df80fcf05ebf0f9 | True | none |
| 703DDIPMA — Business Administration (Management Option) | Diploma | School of Business + Media | diploma with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 621 | 139adbb5f04c608020794aa1589d23d5c286b15d822c4cb18bada27598c28927 | True | none |
| 703EDIPMA — Business Administration (Marketing Option) | Diploma | School of Business + Media | diploma with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 622 | d1132e4bc2ac8d6e852945a0302c4e4098ac492c75d5ae0a9923603a186aa947 | True | none |
| 7460MCERT — International Trade and Transportation Logistics | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 4 | active | 623 | c933fa9868cd018629c3152164cd7af3ee8480ec54b4371ed47117af9849194a | True | none |
| 7475DIPMA — Global Supply Chain Management | Diploma | School of Business + Media | diploma with flat published curriculum | GREEN | none | 23 | active | 624 | 08c13d0421de9cc7e5633f45264734e653722f46fe1df745f73f00cd0630a5b1 | True | none |
| 7485DIPMA — Forest and Natural Areas Management | Diploma | School of Construction and the Environment | diploma with flat published curriculum | GREEN | none | 19 | active | 625 | 1a6eace0d7fad225a32813b071dcd5f0bbcb3e5486500954cacc1d85138d36c6 | True | none |
| 7535DIPMA — Geomatics Engineering Technology | Diploma | School of Construction and the Environment | diploma with flat published curriculum | GREEN | none | 19 | active | 626 | e884d9fb2845bbc1a1a544caf535b88071fda7c0228f6403c62c23a6c4e9e6cb | True | none |
| 7710DIPMA — Construction Management | Diploma | School of Construction and the Environment | diploma with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 9 | active | 627 | 6d1a2526e7d9630f0080ac5bdc6e9d5e349dab5e19a771b950f81428f66a0a9f | True | none |
| A200GRCERT — Building Energy Modelling | Graduate Certificate | School of Construction and the Environment | graduate certificate with flat published curriculum | GREEN | none | 2 | active | 628 | 42b22c844b2e90b9ea404648585f9e441c3d24ec73bf070de9b790171b3ef42d | True | none |
| A500GRCERT — Global Leadership | Graduate Certificate | School of Business + Media | graduate certificate with flat published curriculum | GREEN | none | 6 | active | 629 | df62b1207d10ec3375aac7e8609168a9fa39ae157643df2cef1328f87b45653b | True | none |

## Engineering-rate comparison

Batch 01: 41.67% (5/12). Batch 02: 0.00% (0/24). Batch 03: 0.00% (0/50). Batch 04: 3.00% (3/100). Batch 05: 0.00% (0/100). Batch 06: 0.00%; no new generalized extension was required.

Catalog completion introduced exact duplicate program names and additional partial-name collisions. A generalized resolver hardening now treats duplicate exact names as ambiguous unless the credential disambiguates them, and requires stronger evidence before a multi-word program name can replace an active conversation subject. Advisor wording was unchanged; this correctness hardening is separate from ingestion engineering.

## Final validation

- Exact-hash active revisions: 65/65

- Post-import zero diff: 65/65

- Unresolved course references: 0

- Ownership violations: 0

- Final catalog: 374 active programs and 3976 courses

- Remaining legitimate candidates after Batch 06: 0

- Active programs missing normalized ADMISSION rules: 0

- Python regression suite: 428 passed of 428; 0 failures, 0 errors

- Browser-state suite: 5 passed of 5

- Approximate runtime: 3.61 minutes

## Completion checkpoint

The ordinary current BCIT program catalog ingestion is complete: all 373 current catalog-aligned legitimate programs are represented, plus retained live-but-unlisted 5325ACERT, for 374 active Asteris programs under the no-cleanup policy.
