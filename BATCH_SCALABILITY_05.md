# BCIT Catalog Ingestion Batch 05

Run date: 2026-09-08

## Outcome

Processed 100 additional official BCIT candidates from the authoritative eligible pool of 165. Imported 100; held 0.

- GREEN: 69/100 (69.00%)

- YELLOW: 31/100 (31.00%)

- RED: 0/100 (0.00%)

- Flat pipeline: 69

- Reused Batch 01 adapter: 31

- Genuinely new generalized extensions: 0

- Schema migrations: 0

## Selection and discovery

The official sitemap contained 489 program URLs. All 165 authoritative candidates were refreshed, and a round-robin cross-section was selected across all eight school labels. Three same-name, same-credential but distinct-ID/study-mode entries were conservatively deferred from selection; they remain in the legitimate remaining pool rather than being reclassified as aliases.

Known apprenticeship structures, non-program entries, and the two prior RED holdbacks were excluded. No selected candidate became RED after refresh.

The live PostgreSQL baseline exactly matched the user-provided 209 active programs and 3,288 courses. The 373-program strict current universe and 374 no-cleanup total remain reconciled by retaining live-but-unlisted 5325ACERT.

## Course reconciliation

The candidates referenced 400 courses missing at audit time when counted per program. After validation and deduplication, 309 unique official BCIT courses were imported (3.090 per imported program). Cross-program overlap eliminated 91 duplicate missing-course references.

## Per-program audit

| Program | Credential | School/domain | Structural shape | Class | Adapter/custom code | Missing | Import | Revision | Exact hash | Zero diff | Warnings/blockers |
|---|---|---|---|---|---|---:|---|---:|---|---|---|
| 0805CM — Breast Sonography | Microcredential | School of Health Sciences | microcredential with clinical placement | GREEN | none | 1 | active | 449 | 9fa34afc28f067b3a8c981886985975d862e277bdcc8c46efe0192e7a9a21c9c | True | none |
| 0806CM — Musculoskeletal Sonography | Microcredential | School of Health Sciences | microcredential with clinical placement | GREEN | none | 1 | active | 450 | 4911f3c9770d8c485d2f368759eed89795512d9f2f79ed25dc23e6b403fbec09 | True | none |
| 0811CM — Essentials of Data Networks | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 0 | active | 451 | 8f22d2c6b96d29b0fd14d68ef12a61e2888ebde7725e5811f42173fcb9bfa7d8 | True | none |
| 0812CM — Cybersecurity Analysis for Network Administrators | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 0 | active | 452 | dd5ba9368539182809f8982eca07deec432ba81aadd5b30cf9b07dd83ccda4e5 | True | none |
| 0822CM — Food Safety Preventive Controls and HACCP Plans | Microcredential | School of Health Sciences | microcredential with flat published curriculum | GREEN | none | 1 | active | 453 | 4a0dac84c532f537a8abb7d2bd796bcda0192828254e7daa41816b3cac89e232 | True | none |
| 0823CM — Food Safety Management | Microcredential | School of Health Sciences | microcredential with flat published curriculum | GREEN | none | 1 | active | 454 | a7624bd0829db1011a95fd7600f7c03a468def0e8f9923f0fa2ec79ffad9c480 | True | none |
| 0824CM — Animal Cell Culture | Microcredential | School of Health Sciences | microcredential with flat published curriculum | GREEN | none | 2 | active | 455 | c5905eb9376928e9bd8d6e20f0ae056ee1f2965286adf71787bb80313cd5a911 | True | none |
| 0825CM — Canadian Employment Readiness (CER) | Microcredential | BCIT International | microcredential with flat published curriculum | GREEN | none | 2 | active | 456 | 585acb635e1261489dd9d9f7cf3645ce8551e7cdb726b1a04735d604bf1e93aa | True | none |
| 0828CM — Student Mobility Preparedness | Microcredential | BCIT International | microcredential with flat published curriculum | GREEN | none | 3 | active | 457 | aa72b64c5e613ad3d0e15812495696029039b3e7ed0e0c90ae23a188737c59d2 | True | none |
| 0829CM — Building Energy Modelling and Simulation | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 0 | active | 458 | ae6d2e718ed2f0f2b06b292d440e51c652c732d001409d7c7b95c7edc8dcef29 | True | none |
| 0833CM — Forensic Nurse Death Investigator | Microcredential | School of Computing and Academic Studies | microcredential with clinical placement | GREEN | none | 1 | active | 459 | 440d522d7866db62afb0e2d797a18fb5eba64f794ebbd1edb32bac7a22f233fe | True | none |
| 0835CM — International Education Practitioner - Foundation | Microcredential | BCIT International | microcredential with flat published curriculum | GREEN | none | 4 | active | 460 | 2fd7ad17229970247733db68a2b3d9f095734037a8986b8801a7fe929f02f222 | True | none |
| 0837CM — Foundational Digital Forensics Skills | Microcredential | School of Computing and Academic Studies | microcredential with flat published curriculum | GREEN | none | 0 | active | 461 | 82b4dd0ba841a24efab277dfab8f6dbef845401c0299c5dc5f6a49966c6205e0 | True | none |
| 0838CM — Automotive Service Management Essentials | Microcredential | School of Transportation | microcredential with flat published curriculum | GREEN | none | 2 | active | 462 | 90af406c2e06cbd8b2839d5abd66c5bff7af6888b7a9853da2a4a670d0559b15 | True | none |
| 0840CM — Introduction to Full-Stack Web Development | Microcredential | School of Computing and Academic Studies | microcredential with flat published curriculum | GREEN | none | 0 | active | 463 | b4962eaed2816c0b9febde336b97f45491272ee1ac4c7c5bfa3d632d3bcb7ace | True | none |
| 0841CM — Web Development Foundations (WDF) | Microcredential | School of Computing and Academic Studies | microcredential with flat published curriculum | GREEN | none | 0 | active | 464 | 4fc887cc22bf5d40d268587b589af98ab3d1284cca8210b06d70ef829c54070f | True | none |
| 0842CM — Data Visualization with MS Power BI | Microcredential | School of Computing and Academic Studies | microcredential with flat published curriculum | GREEN | none | 0 | active | 465 | 5f9147c6ac9daf75ce5858921b5a1628841f2b30284a71c14b295dcdb9a3439c | True | none |
| 0843CM — Spanish Language and Culture Fundamentals | Microcredential | BCIT International | microcredential with flat published curriculum | GREEN | none | 2 | active | 466 | dbc5cd8d7a53d7215e9eb92b8631ea86c84470d15728619cf764bae52da69597 | True | none |
| 0844CM — Fundamentals of Virtual Containers | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 2 | active | 467 | aed2a806da91478dfd028c5f233245ea21ccae8d19c215eb77414b34586b11dc | True | none |
| 0846CM — Sterile Field and the Aseptic Environment | Microcredential | School of Health Sciences | microcredential with flat published curriculum | GREEN | none | 0 | active | 468 | 8fe615851b041c95955c8c92b8e4665ad453fc3fb3f51c21321516c77d776c91 | True | none |
| 0847CM — Wind Turbine Essentials | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 0 | active | 469 | 3e762c114b47063ae7dac363789c00a7f9ac8a3137bbd43ccbb5e3fd2d7aade8 | True | none |
| 0848CM — Advanced Topics in Networking | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 2 | active | 470 | fda6622eeb0a647b9cad8b38d801586158bab0b1ec535cb3aea75ea7f1e0f9d0 | True | none |
| 0849CM — Asbestos Awareness and Safety | Microcredential | School of Health Sciences | microcredential with flat published curriculum | GREEN | none | 0 | active | 471 | 3e04b588bd357cbb07f10fc6e0b7106a38e946a4606e6015080bf4a67b23f1f1 | True | none |
| 0850CM — Fraud and Financial Crime Investigation | Microcredential | School of Computing and Academic Studies | microcredential with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 4 | active | 472 | afec0c3ad4d49c9865b3e066c85c8fb988b0cbb9ca53c7234f088c89f067b969 | True | none |
| 0851CM — Aircraft Defect Inspection and Reporting Techniques | Microcredential | School of Transportation | microcredential with flat published curriculum | GREEN | none | 2 | active | 473 | 043629eacea5f6aafa1f9d468c553becba3b4429a1a14b6272a8a79215a7c9c4 | True | none |
| 0852CM — Canadian Engineering Professional Practice | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 0 | active | 474 | d2c7d062f87908783c9d6d23ae8b1ffcc41cb0ae13a5a8766df7ba9f208b01d9 | True | none |
| 0855CM — Thermal Power Plant Simulation Proficiency | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 1 | active | 475 | dd63adb21b11be3304c7068d11894121ab63fa12f70ca63dfe2434bbf0e2fa11 | True | none |
| 0857CM — Automotive Collision Estimator | Microcredential | School of Transportation | microcredential with flat published curriculum | GREEN | none | 0 | active | 476 | b65618e97e62275115cf5060a6073e7e9cac3dc39b0464950c1ce7def9602cb8 | True | none |
| 0860CM — Heat Pump Maintenance and Troubleshooting | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 3 | active | 477 | 17ffc8370690b495b58d9323ef15393c2c9fdaa4d5e41b33150f705470ffebb2 | True | none |
| 0865CM — Introduction to Power Systems Protection Design | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 3 | active | 478 | bb5653133266a67de86aa3d778c00dff7345fc600fbb710e784a7255b32f0e9d | True | none |
| 0866CM — Distribution Design for Electrical Utilities | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 1 | active | 479 | 38f2009012fda1f2bc5e760767e942abf1c7b347e8456f14a78388d1f5a34577 | True | none |
| 0872CM — Techniques for Crime & Intelligence Analysts (TCIA) | Microcredential | School of Computing and Academic Studies | microcredential with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 4 | active | 480 | e420d479a0ef887c652f7365f66da96d8dbaccc3b06cefa6d14d32f4a62c5937 | True | none |
| 0873CM — Fundamentals in Polytechnic Teaching | Microcredential | Learning and Teaching Centre | microcredential with flat published curriculum | GREEN | none | 1 | active | 481 | 023a08361df0de040f1664ac3ec5bb0472b7580b3dd8f74e2e7c196731d3a029 | True | none |
| 0875CM — Applied Additive Manufacturing | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 2 | active | 482 | e058f1f703b54b6fc1144fa9c2ce8f17de9fba453a02ad1a05c3f13047562fbe | True | none |
| 1030CERTTS — Aircraft Gas Turbine Technician | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 10 | active | 483 | 0b4ded6a0a097a2ba91b92f1f3631d4f10898b483398ce77b3106f0a896ca64b | True | none |
| 1155ACERT — Construction Drawings | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 0 | active | 484 | a688cc3f6d796da093fa5e6499df04796f846bdadfe098613da3562c3c6d8b66 | True | none |
| 1360CERT — Automotive Technician (Honda/Acura Foundation) | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 1 | active | 485 | 8af4cabb606eab1223b6620d504fcdba5c73c33743b6d63c9bfe44cee50b29d9 | True | none |
| 1375TTCERT — Automotive Technician (Toyota Foundation) | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 1 | active | 486 | c001cf3ba6744b4b2c9c497c9625267d8392d86d6d6ef662933ebd341e47ee98 | True | none |
| 1430DIPMA — Automotive Service Technician and Operations | Diploma | School of Transportation | diploma with flat published curriculum | GREEN | none | 41 | active | 487 | f53c3ffe0f995d79a9d62371c061fb4f808bc1a42ba854b7d12e1fa309d233b5 | True | none |
| 143ADIPMA — Automotive Service Technician and Operations (Ford ASSET Option) | Diploma | School of Transportation | diploma with flat published curriculum | GREEN | none | 41 | active | 488 | ae9bb0ee95c3f21e17d567b1916fc4dc960257c3f120715c1f353d47155541e7 | True | none |
| 143BDIPMA — Automotive Service Technician and Operations - Non-Co-op Option | Diploma | School of Transportation | diploma with flat published curriculum | GREEN | none | 39 | active | 489 | 12aa1418a4ac07049774caeda75d7067d109e090c77b58d2854e569fa67c71af | True | none |
| 1645CERT — Carpentry Framing and Forming Foundation | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 1 | active | 490 | fa6ca35e23b270e6971e6cbea1303629f6a7a31ecd87ae7ba8b1fe8c36e4a96a | True | none |
| 1720CERTTS — Architectural and Structural CADD and Graphics Technician (Architectural Option) | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 13 | active | 491 | d0513e725f4e34fbc07d37ed2400fb63fe8d600efd227c0ec81ba68ca009f8ab | True | none |
| 1855DIPMA — Heavy Duty Truck Technology | Diploma | School of Transportation | diploma with flat published curriculum | GREEN | none | 33 | active | 492 | d1e6ab5eaf17cf68477d1841a8a1dca8b125e05cabcc40b6ee98dfcd19f8d616 | True | none |
| 1885ACERTS — Network Administrator Technician | Associate Certificate | School of Energy | associate certificate with flat published curriculum | GREEN | none | 0 | active | 493 | 5b61edc0a90d0c82e1fe1ebdfea2964e3aa50893e26445a1338c1ba16f852b77 | True | none |
| 2440CERT — Piping Foundation | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 1 | active | 494 | 7c6ee1383ed98c3d93e4325a2e7947992dd6d02582fdad7b1841e2ce966abb10 | True | none |
| 2542CERTTS — Watchkeeping Mate Near Coastal (WKMNC) | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 1 | active | 495 | 170628f0e6e74429d3dd5d4e4ab2a41be1c333b3dbacb382ac874f5725e9f90f | True | none |
| 2645CERT — Sheet Metal Worker Foundation | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 1 | active | 496 | 2c08fc8560b70025e0d8f5e35f3e07028f7198a04aa8b3eada43e1746309e748 | True | none |
| 2825CERT — Metal Fabricator Foundation | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 14 | active | 497 | 81c24e083b124ab5f9a6045aea02e4a56a38d6702208c32228b4e815572fb62f | True | none |
| 2847CERT — Welder Foundation | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 1 | active | 498 | edb9c862f2587f5430d693240847fea20f03ab839123cca13f0e38dd379d2a58 | True | none |
| 2860TTCERT — Welding, Level B | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 1 | active | 499 | 0ff4b635e7d0856cb312744fd2511c18635f5dd440e3e927427435c9a37a719c | True | none |
| 2870TTCERT — Welding, Level A | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 1 | active | 500 | 4cd96094ecda9a10d66e39dd7a23ca5fe82e9a1ae84cebee0ada7c08609643aa | True | none |
| 2915CERT — Security Systems Technician | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 6 | active | 501 | 6f0d318458fe2a8f4f8935e8472a508f8e4f57020faebaff49c82563193adae8 | True | none |
| 5077CERT — Event Marketing and Management Strategy | Certificate | School of Business + Media | certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 502 | f8edc83ef5e0a7d2b189d39543a5f222c91b40aaf52935ce007109d6a2282ef9 | True | none |
| 5085ACERT — Project Management | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 503 | 9605bd3fcca82eff956a0c60d7080c9ac1d886bf59d2f73701eda9ebef40afac | True | none |
| 515HACERT — Building Design and Architectural CAD | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 0 | active | 504 | a89716bccc5389a79460e40e52e2992d08a23b714ceaa3d2bdf60b72dd61a228 | True | none |
| 5160ACERT — Industrial Wood Processing | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 5 | active | 505 | b472018dec318d0a9958372cfe4f5e2013eba829c4761b861e98b14af4fa234b | True | none |
| 5175ACERT — Polytechnic Teaching | Associate Certificate | Learning and Teaching Centre | associate certificate with flat published curriculum | GREEN | none | 3 | active | 506 | 5e6f7ba7dc9b70b93261b435c407e4370ee5da149feb96d32981d3ab310b2c46 | True | none |
| 5275ACERT — Business Intelligence | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 1 | active | 507 | 59b04f58e08c1dd3ab313f04e164f3b63f3ca9556a28da326f33a6eafdef3575 | True | none |
| 530ADIPLT — Cardiology Technology | Diploma | School of Health Sciences | diploma with clinical placement | GREEN | none | 5 | active | 508 | 6c6ccb422b072ed41e9d14d5ff1f5ed1feccd3c24dd0c7b061d2c8e435b72f19 | True | none |
| 5430CERT — Civil Technology | Certificate | School of Construction and the Environment | certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 5 | active | 509 | bac487765abb71d36bace2d7dac160dbc6f4a4ad6daa4109da7202eddf1e281d | True | none |
| 5725ACERT — Computerized Accounting | Associate Certificate | School of Business + Media | associate certificate with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 510 | c6d043045f0f2d6332840726ddbfce2f611ab8290bcc731ddafa52ac81176a37 | True | none |
| 576CDIPMA — Diagnostic Medical Sonography (General and Cardiac Sonography Option) | Diploma | School of Health Sciences | diploma with clinical placement | GREEN | none | 3 | active | 511 | 89a9c3cee41868857d4286ce0c870b91d7f10e43f0c73600912bbab36d77e916 | True | none |
| 585CMCERT — Financial Management (Finance Option) | Certificate | School of Business + Media | certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 512 | 1d98aef6cf77163739cd570ac10dda6af5f9434be5230683dd9e3b3411576538 | True | duplicate course reference normalized during import: BSYS1001; duplicate course reference normalized during import: ECON2100; duplicate course reference normalized during import: ECON2200; duplicate course reference normalized during import: FMGT2711; duplicate course reference normalized during import: FMGT3210; duplicate course reference normalized during import: FMGT3410; duplicate course reference normalized during import: FMGT4210; duplicate course reference normalized during import: FMGT4410 |
| 585FMCERT — Financial Management (Professional Accounting Option) | Certificate | School of Business + Media | certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 3 | active | 513 | af6c8093b64edff614158a9d3a80a286809d4def1679e5720c877913ae60faba | True | duplicate course reference normalized during import: ECON2200; duplicate course reference normalized during import: OPMT1130; duplicate course reference normalized during import: ORGB1105 |
| 5985ACERT — User Interface (UI) and User Experience (UX) Design | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 514 | 70d4e4ad8d2590cf006100c74b7c931df5a990579a438d85d5362842e70d6e64 | True | none |
| 6008CERT — Payroll Administration | Certificate | School of Business + Media | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 515 | 67f39c9664319ddb510fe0aa018c7ddbd24389f488617a103179855c80fd2cf8 | True | none |
| 6030CERT — Architectural and Building Technology | Certificate | School of Construction and the Environment | certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 5 | active | 516 | 42831af703c315a4bce29ab91532c4b5b2d84dd8f8fe5455c874a58abae9275f | True | none |
| 6040ACERT — Fundamentals of Water and Wastewater Operations | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 4 | active | 517 | 0f1153ca06e8da9d03aab445faba116221329a2a4627c0a3c1c9a3a73b2fe628 | True | none |
| 6090CERT — Essential Technical Skills for Architecture, Construction, and Engineering | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 10 | active | 518 | f33e551b3b15b5fae609acababf8f8b95d28eee950ca1d1767a9b32a287fb50f | True | none |
| 6185ADCERT — Renewable Energy Electrical Systems Installation & Maintenance | Advanced Certificate | School of Construction and the Environment | advanced certificate with flat published curriculum | GREEN | none | 2 | active | 519 | a407f8ab6bdb76de316cd72e43f77009eccdf4ba234e0d5a5f21ae0692fc1a16 | True | none |
| 6195CERT — Interior Design Fundamentals | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 1 | active | 520 | 14e2405591eea772ceffbef5814202d59b794a1aab61b821abb812090c6872d3 | True | none |
| 6225ACERT — Global Business Studies | Associate Certificate | School of Business + Media | associate certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 8 | active | 521 | 1cd8204a9576b430e532e05af987e1b98960167a07eddb111f5bd6fb765c850c | True | duplicate course reference normalized during import: RMGT5007 |
| 630HACERT — Marketing Management - Entrepreneurship | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 522 | 78372e689250f2e31d1a293f2d99d20defe009dee7cfa9127288ed9d94f4bf17 | True | none |
| 630MACERT — Marketing Management - Sales Skills | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 523 | 1c06ec21a449fa70c5a545671dae95fa720d80cbccced958854687eb51cc0c60 | True | none |
| 630WACERT — Marketing Management - Customer Relationship Marketing | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 524 | ca217bd6971b34ed419d9c237cc9c4ec66b0d69977010acaa2a4e095be465134 | True | none |
| 630XACERT — Marketing Management - Public Relations | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 525 | ce2eacd5f236c52ac5b93d0118be2cc8d9635a9f3f4cfd500bab8bc5b5fc98f8 | True | none |
| 6365ACERT — Food Safety | Associate Certificate | School of Health Sciences | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 4 | active | 526 | ebe4b73e25174613f1c0bca5b4fb7304da1741b9a44b64dbb0862da4eac0d7f4 | True | none |
| 6375ACERT — Digital Marketing Foundations | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 0 | active | 527 | 6392c5a6c39c2d2c6f0f9ee1fdee7706bdfd1b7f5dcd8e684a67683dafd82c32 | True | none |
| 6390ACERT — Marketing Management - Fundraising Management | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 3 | active | 528 | f90216932837fd9b30504fe64a0c144d050ba0120394e3bb318327eb0c61fa3e | True | none |
| 6505ACERT — Graphic Design Foundations | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 0 | active | 529 | 8d05893ea0e5e020685029369d192ad76995f4013db7f417212eb078211c89ba | True | none |
| 6590ACERT — Tourism and Hospitality | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 530 | 9f69f0af88de3ef607171299125cf3d42dbd0acf14e3babb3870c1baacf28067 | True | none |
| 6630ACERT — Medical Office Assistant | Associate Certificate | School of Business + Media | associate certificate with clinical placement | GREEN | none | 0 | active | 531 | efe7e5fff594ba4fad51e0862a038ea06cbadc07914ca8523e87378cc2da075e | True | none |
| 680FASCERT — Neonatal Nursing Specialty | Advanced Certificate | School of Health Sciences | advanced certificate with published alternatives or pathways, credit pool, clinical placement | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 532 | 630f862bccbbf99514f8a145a98b9285b40931e17731b216921ea195abf00330 | True | none |
| 680PASCERT — Perioperative Nursing Specialty | Advanced Certificate | School of Health Sciences | advanced certificate with published alternatives or pathways, clinical placement | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 533 | 769840b6e0c3a3a94ab737029f101513969ee6fc2bacb991bb2fc1fac3dfed23 | True | none |
| 680VASCERT — Perinatal Nursing Specialty (Perinatal - Perioperative Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 534 | 91b4bafb1421e30c4191d1f2b82d3e8ad169dec468eb383318ce6158ae4af477 | True | none |
| 680YADCERT — Emergency Nursing Specialty (Pediatric Emergency Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 1 | active | 535 | a2a02952a78d4ee6649980a8e395db4d9ee3e66444074dc69f9abbf7c649a6c6 | True | none |
| 680ZADCERT — Pediatric Nursing Specialty (Critical Care Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 536 | ca0e48267447581e917fa80981970ae1b8dc69a818871e7e3b3ad13e95473f42 | True | none |
| 6830ACERT — Leadership | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 537 | b1f97fef689a7918d32421e9f6ebe9ad114c7893fcf596e8a3621746ee22637a | True | none |
| 6835ADCERT — Pediatric Emergency Nursing Specialty | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 1 | active | 538 | 23886218b04d7ae112dd256fe4cff9ba6fa40a6aa9bb6d5654ec1ff79067aacd | True | none |
| 6890CERT — Advanced Safety Management | Certificate | School of Health Sciences | certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 539 | 87da947e7455eea025864ec4a4d017408e6b0f68d498c9e5fe17ab1574f5a434 | True | none |
| 6994ACERT — Applied Database Administration and Design | Associate Certificate | School of Computing and Academic Studies | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 540 | da55d9804ed221eb1e4d05d2b2fb02d55d8e5533203494a8324c9a175e5fdfe4 | True | none |
| 7610ACERT — Human Resource Management | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 541 | a8a91867c944ee093f266c2fa3e8d7a8ef760a6778e3be8da46dbd8e94e0e946 | True | none |
| 7870CERT — Construction Supervision | Certificate | School of Construction and the Environment | certificate with non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 3 | active | 542 | 00fc0b657a4730f67a046827521d0f77f0ecf91943bb4d1be06797cdba75a2f6 | True | none |
| 830ABHSC — Bachelor of Health Science (Magnetic Resonance Imaging Option) | Bachelor of Health Science | School of Health Sciences | bachelor of health science with clinical placement | GREEN | none | 0 | active | 543 | b53eeb58b84743be52dc0d570efa14ff68ab54f742336a524e95167a8c30ecc9 | True | none |
| 867BBSC — Applied Computer Science (Network Security Applications Development Option) | Bachelor of Science | School of Computing and Academic Studies | bachelor of science with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 3 | active | 544 | 4d5bb33d5435980fc61ceaee634958020f918c380b931217c52197787446dbca | True | none |
| 867DBSC — Applied Computer Science (Human Computer Interface Option) | Bachelor of Science | School of Computing and Academic Studies | bachelor of science with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 13 | active | 545 | 8d3a83bc771261db9224f1e253b7f232521710ec7d6d0427c4c4d3d972f69f00 | True | none |
| 867EBSC — Applied Computer Science (Network Security Administration Option) | Bachelor of Science | School of Computing and Academic Studies | bachelor of science with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 16 | active | 546 | 8fc63df5deee2c5907d9195efc53a6856f68d34a5c8361c02cb1d8f338d6f779 | True | none |
| 867FBSC — Applied Computer Science (Wireless and Mobile Applications Development Option) | Bachelor of Science | School of Computing and Academic Studies | bachelor of science with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 13 | active | 547 | fcdb13c0b896917d09542352f9cbfac28f0f65bc12ae8ee58f0c6cede2002d72 | True | none |
| 8910BSC — Honours in Biotechnology | Bachelor of Science | School of Health Sciences | bachelor of science with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 26 | active | 548 | 88476f8884be8dec68419f39fd0220f4b50bd36d39b2c43665c290ee7e98276e | True | none |

## Engineering-rate comparison

Batch 01: 41.67% (5/12). Batch 02: 0.00% (0/24). Batch 03: 0.00% (0/50). Batch 04: 3.00% (3/100). Batch 05: 0.00%; no new generalized extension was required.

Catalog growth exposed generic one-word program-name collisions in conversational routing. A generalized mention-resolution guard was added without changing advisor wording; this correctness hardening is reported separately from ingestion engineering and does not change the Batch 05 ingestion-extension rate.

## Final validation

- Exact-hash active revisions: 100/100

- Post-import zero diff: 100/100

- Unresolved course references: 0

- Ownership violations: 0

- Final catalog: 309 active programs and 3597 courses

- Remaining legitimate candidates after Batch 05: 65

- Active programs missing normalized ADMISSION rules: 0

- Python regression suite: 425 passed of 425; 0 failures, 0 errors

- Browser-state suite: 5 passed of 5

- Approximate runtime: 4.49 minutes
