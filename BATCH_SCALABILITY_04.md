# BCIT Catalog Ingestion Batch 04

Run date: 2026-09-08

## Outcome

Processed 100 additional official BCIT candidates from a deduplicated eligible pool of 207. Imported 99; held 1.

- GREEN: 65/100 (65.00%)

- YELLOW: 34/100 (34.00%)

- RED: 1/100 (1.00%)

- Flat pipeline: 65

- Reused Batch 01 adapter: 34

- Genuinely new generalized extensions: 2 (published component-credit fallback; deterministic unique rule names for repeated published component orders)

- Schema migrations: 0

## Selection and discovery

The official sitemap contained 489 program URLs. Discovery successfully inspected 221 non-apprenticeship pages, excluded 14 canonical-ID, URL, or credential-context duplicates/aliases, and selected a round-robin cross-section across all six BCIT schools.

Known apprenticeship structures were not used to fill the batch. The naturally encountered RED record was held without architecture work.

## Course reconciliation

The candidates referenced 557 courses missing at audit time when counted per program. After validation and deduplication, 507 unique official BCIT courses were imported (5.121 per imported program). Cross-program overlap eliminated 50 duplicate missing-course references.

## Per-program audit

| Program | Credential | School/domain | Structural shape | Class | Adapter/custom code | Missing | Import | Revision | Exact hash | Zero diff | Warnings/blockers |
|---|---|---|---|---|---|---:|---|---:|---|---|---|
| 0120NOBCIT — International Student Entry | Full-time |  | full-time | RED | held: official curriculum publishes no identifiable BCIT course references | 0 | held |  |  | False | no identifiable BCIT course references in the published curriculum |
| 0804CM — Forensic Nurse Examiner Education for RNs | Microcredential | School of Computing and Academic Studies | microcredential with flat published curriculum | GREEN | none | 0 | active | 342 | b98703bc184a5af5ff576a27c2b10c97146bfd2ef0e95cc64ae418a429895488 | True | none |
| 0810CM — Low-Code Mobile Application Development | Microcredential | School of Computing and Academic Studies | microcredential with flat published curriculum | GREEN | none | 3 | active | 343 | 397080d56aedd27b7b60111d100c8062bbd5643c0284437af26d14ed9d5f199f | True | none |
| 0813CM — Advanced Forensic Nurse Examiner | Microcredential | School of Computing and Academic Studies | microcredential with flat published curriculum | GREEN | none | 6 | active | 344 | 9fcc7202e2c7d95549caa4c9421089d56e7a177a28d41831bd5ac09438fe9fc3 | True | none |
| 0820CM — Cybersecurity Essentials for IT Professionals | Microcredential | School of Computing and Academic Studies | microcredential with flat published curriculum | GREEN | none | 0 | active | 345 | bfe2c52a9956546e821980f16ad396f248e7a39b3252d3bfc9959cba4679346b | True | none |
| 0831CM — Industrial Networking for Cybersecurity Professionals | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 5 | active | 346 | 6c7abd5fcc116803ff488924d1694d3e5b72acb94f24531fee3fea1d31ddcf95 | True | none |
| 0832CM — Cybersecurity Operations | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 0 | active | 347 | 8b14e36cfce018d344ba2e772ecdaaa9c4a0ad7da520037d1e7039506cdce227 | True | none |
| 0839CM — Fiber Optics - Principles, Installation and Repair | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 0 | active | 348 | 634fa0c07ede086dd4f0b0b71f8fceefdb1b1d813289cf95826e0864cede7d66 | True | none |
| 0845CM — Network Switching and Routing | Microcredential | School of Energy | microcredential with flat published curriculum | GREEN | none | 2 | active | 349 | ae8af43c81409fcdc1f17928fcf5bb87eb6610dbd5c3c8deff1dc977630e1ab0 | True | none |
| 1070ACERT — Airport Operations | Associate Certificate | School of Transportation | associate certificate with flat published curriculum | GREEN | none | 6 | active | 350 | 1a6af8b8135a9cf45c2f50f8e28724c6cee11ebf83511d06e248618ffea07cc8 | True | none |
| 1190ACERT — Trades Discovery for Women | Associate Certificate | School of Transportation | associate certificate with flat published curriculum | GREEN | none | 0 | active | 351 | dcf22b0361d23c3b26aea79d5d5af85564e33af4a20c651ec939ec1bf5c04c6c | True | none |
| 1195IPCERT — Advanced Gas Turbine | BCIT/Industry Partnership Certificate | School of Transportation | bcit/industry partnership certificate with flat published curriculum | GREEN | none | 7 | active | 352 | aaa8473b60d7101546c17e385f15d62d09428eacc90abce6afd6790563ad6152 | True | none |
| 1255CERT — Auto Body Repair and Refinishing Technician Foundation | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 15 | active | 353 | 6279c9ba3f94e1ffcee83c1a8a802e5d82399c15ea839d8d05ab4ccfb9975318 | True | none |
| 1320ADCERT — Automated Controls Installation and Maintenance | Advanced Certificate | School of Construction and the Environment | advanced certificate with flat published curriculum | GREEN | none | 3 | active | 354 | 37e5182ff30a29abc1e3f0f068976b45d842307c9c419e063cccdc8d7d1ca387 | True | none |
| 1355TTCERT — Automotive Technician Foundation | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 12 | active | 355 | 76c4f3a2a700b5211fe15a85696eff272f2425c22089892931b34ec139db30cd | True | none |
| 1685ACERT — Railway Conductor and Operations | Associate Certificate | School of Transportation | associate certificate with flat published curriculum | GREEN | none | 0 | active | 356 | 77a07ec5348252e0508405b28ffb57350faf0c1898378d47be8ad9d157f4f477 | True | none |
| 1710CERTTS — Architectural and Structural CADD and Graphics Technician (Structural Option) | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 13 | active | 357 | 84cfd7ca3d42b7fd557534c399f901f8cf0bf00d401b691dd584f326176215c2 | True | none |
| 1790ACERT — Hydronic Technician | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 8 | active | 358 | e76e58803f13542d1f9e5ec755e9c12e163d7028a5248628110e5bac573b6fc5 | True | none |
| 1920CERT — Marine Mechanical Technician Foundation | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 16 | active | 359 | 6ffcc7963d5262d0c0b82bf95824bc3b061098b1931ec026314d856233361b00 | True | none |
| 1940CERT — Heavy Mechanical Trades Foundation | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 14 | active | 360 | 205f5e0284ba52b52e9ba542356cfa6c188a6e37efe80357cc9fc1a75291f94d | True | none |
| 2000TTCERT — Ironworker Foundation | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 13 | active | 361 | c7a80ca36da4ddcf0912600dedc730e1e72c087bfb603d131732bd66e063eea2 | True | none |
| 2020CERTTS — Chief Mate | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 4 | active | 362 | e347ba5e9bf8c2840406aa47bd4e7a4b889c249e7ee205e76630d34e320efba0 | True | none |
| 2060CERT — Cabinetmaker (Joiner) Foundation | Certificate | School of Construction and the Environment | certificate with flat published curriculum | GREEN | none | 1 | active | 363 | 3468071e61ac337baeb0037392518b18e55cb93db428ec3a690350161f9e1415 | True | none |
| 2175TTCERT — Machinist Foundation | Certificate | School of Energy | certificate with flat published curriculum | GREEN | none | 1 | active | 364 | 6aebdab79b8390b7de062e7b31cec31695f3c9eb6a3ac4cbefb6a918828834eb | True | none |
| 2230CERT — Millwright Foundation | Certificate | School of Energy | certificate with flat published curriculum | GREEN | none | 9 | active | 365 | 34d7f19ea22df13ad3c3d007acef043892fbddf601f9f8da4a3fad247cd4210c | True | none |
| 2365CERT — Motorcycle Technician Foundation | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 11 | active | 366 | 4e3c2696dbf04c2cfa27247ff672ea1a6745218672f49bfbd87a42d120bee26f | True | none |
| 2410TTCERT — Power Engineering (General Program) | Certificate | School of Energy | certificate with flat published curriculum | GREEN | none | 7 | active | 367 | 0764dff41eddc404135ca5fc37474e092d41e14066e68e94077079d73a705de1 | True | none |
| 2425CERT — Refrigeration and Air Conditioning Mechanic Foundation | Certificate | School of Energy | certificate with flat published curriculum | GREEN | none | 11 | active | 368 | 66df34ff4274a6a3d4b5f074717ff04d10e45692395a5bd3593c43dec35f104a | True | none |
| 2505ACERTS — Master 150GT Domestic | Associate Certificate | School of Transportation | associate certificate with flat published curriculum | GREEN | none | 2 | active | 369 | e976ca353c8e71a09e3368cc84688512e32ad049f4884c8bbb07b0c94a646bf3 | True | none |
| 2515ACERTS — Master 500GT Domestic | Associate Certificate | School of Transportation | associate certificate with flat published curriculum | GREEN | none | 3 | active | 370 | cd21413d7b1be1fa45d22929a6acc28e057827263e9c1368b334bedbb53f4427 | True | none |
| 2522CERTTS — Master 3000GT Domestic | Certificate | School of Transportation | certificate with flat published curriculum | GREEN | none | 4 | active | 371 | 181f6d3a68ca13f40b3c1244ca525f5cd3a97dc9275e985d1d164b79b4b09b8d | True | none |
| 2885ADVDIP — Marine Engineering | Advanced Diploma | School of Transportation | advanced diploma with flat published curriculum | GREEN | none | 10 | active | 372 | fb0c230cce1ad60d31ad096d448163bbf462a3c986134d4d70ebc38b0cfc5b93 | True | none |
| 2933ACERT — Bridge Watch Rating | Associate Certificate | School of Transportation | associate certificate with flat published curriculum | GREEN | none | 1 | active | 373 | a8eb7240c477806ef963f74d4619d3aa380f4161df98e38e9d60475e0e2d7381 | True | none |
| 2945DIPMA — Industrial Instrumentation and Process Control Technician | Diploma | School of Energy | diploma with flat published curriculum | GREEN | none | 19 | active | 374 | 9bbafff78ee58f2a7297e4ffb47eefbf79867da0b417eab3c25f0cac5b4b5175 | True | none |
| 2958CERT — Heating, Ventilation, Air Conditioning and Refrigeration Technician | Certificate | School of Energy | certificate with flat published curriculum | GREEN | none | 23 | active | 375 | 5853f68cb9ffd2b53ae32fd1b72ff82f8d0e67cfe46c2d542f4207f350090316 | True | none |
| 2992DIPMA — Heating, Ventilation, Air Conditioning and Refrigeration Technician | Diploma | School of Energy | diploma with flat published curriculum | GREEN | none | 26 | active | 376 | 56cc3500b303fbde38c59dc9a1cd547b16ab898550415424e477a7b1bc529564 | True | none |
| 5125ACERT — Business of Sawmilling | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 5 | active | 377 | 6359a3bf0b71a53c413ce3c03a635c46004971565b63ed52953b78546aab36df | True | none |
| 5145ADCERT — Sustainable Business | Advanced Certificate | School of Business + Media | advanced certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 378 | 042dced850cfe7ebad41109d547913a98c299e61a42e9becfe82780a6303bdc5 | True | none |
| 515GACERT — Building Construction Technology | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 0 | active | 379 | d18c0bb424a9d67a69007630661cdce4ccd8f86ddcaa1d4f2e469fc52afaeeaf | True | none |
| 5170ACERT — Healthcare Unit Clerk | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 0 | active | 380 | e4fbfa5682f1c85ab3b4288dab80be41eb51b0e4c751b02ec58198efd4e22431 | True | none |
| 5180ADVDIP — Sustainable Business Leadership | Advanced Diploma | School of Business + Media | advanced diploma with flat published curriculum | GREEN | none | 3 | active | 381 | 5d4eb9b8811e3df392da14d35592c965f5481eddb1750b0c313060ce28f2d216 | True | none |
| 5180PADVDIP — Sustainable Business Leadership | Advanced Diploma | School of Business + Media | advanced diploma with flat published curriculum | GREEN | none | 3 | active | 382 | 1428ee1e0193bc8ec0ae5376832bfbd00f5002602d9cbfb5e6f52fbda9c9bca9 | True | none |
| 5205ACERT — Business Analysis | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 4 | active | 383 | 4ca9d25a2dabc3fd28faf18834bfa0e97f5e89e5d75bb3683f580fd9b1a33e2c | True | none |
| 5225ACERT — Construction of Mass Timber Structures | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 5 | active | 384 | 8647be7e9aa016ee0ad7b4aca7e1b5990ef508e3fd233aacb03ef698e49894d6 | True | none |
| 5235ADCERT — Building Energy Modelling and Performance Analysis | Advanced Certificate | School of Construction and the Environment | advanced certificate with flat published curriculum | GREEN | none | 7 | active | 385 | 01cbbea9edcc7aa99434b94d346da9a7dcfa16d0d93cf404f2149552b4c92e2d | True | none |
| 5245ACERT — Artificial Intelligence Management | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 2 | active | 386 | cac10f88ad5e2adb3e1f71d4787a7c97793bf54bc92bbae23ec51815fdc3ba39 | True | none |
| 5265DIPMA — Industrial Network Cybersecurity | Diploma | School of Energy | diploma with flat published curriculum | GREEN | none | 25 | active | 387 | f5c5de5dbbff6a45600d68aff2611a187c08fc8274b1c269c736e8c44708b77e | True | none |
| 528AADCERT — Forensic Investigation (Crime and Intelligence Analysis Option) | Advanced Certificate | School of Computing and Academic Studies | advanced certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 3 | active | 388 | 35f0ab741b03dcf3b550591044912f98fee3b94c7a7f980e878c1153a6e4117f | True | none |
| 528BADCERT — Forensic Investigation (Forensic Science Option) | Advanced Certificate | School of Computing and Academic Studies | advanced certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 8 | active | 389 | 79c9137e8bd4fe096727c9b48daec3a0d4e5f615c16f04323bd8049a5b9bf222 | True | none |
| 528CADCERT — Forensic Investigation (Digital Forensics and Cybersecurity Option) | Advanced Certificate | School of Computing and Academic Studies | advanced certificate with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 11 | active | 390 | e791f8e7ecad277c631f59fc4ad09bdf2927b6cf7e8dec6ee95e1ae5fec632db | True | none |
| 5295ACERT — Business Data Management | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 2 | active | 391 | 22bae6aba2b1ed273b749d3b92d671b9b40101940c58f580fbeff872933162b1 | True | none |
| 5320ADCERT — Cardiac Sciences (Electrophysiology Technology Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 392 | 459d128336632d74de7a2e75c4e6655fb7a060ec27b1c8e6d101aa81d3f97d86 | True | none |
| 5325ACERT — Foundations in Occupational Health and Safety | Associate Certificate | School of Health Sciences | associate certificate with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 393 | acbbedfaa437839d887dc4e83074741cc43fb14e4ffb2be7f0f79bbd9d3bc5c7 | True | none |
| 5330ADCERT — Cardiac Sciences (Cardiac Rhythm Device Technology Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 394 | 198cbb1103d84a3d9fc52bfc8edd21216cfe9fd26a49fe22bed6e5ec9ecd3fd4 | True | none |
| 534CDIPMA — Electrical and Computer Engineering Technology (Telecommunications and Networks Option) | Diploma | School of Energy | diploma with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 9 | active | 395 | 33bc894f25e3d02259e47691c1f57c90652c866d124acc4a2eca4faa58a4875c | True | none |
| 5365ACERT — Digital Media Foundations | Associate Certificate | School of Business + Media | associate certificate with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 3 | active | 396 | 38813e49bfa8f664a6835559d6f26741c8a1ad772f99dcf53acaabbe8a859b91 | True | none |
| 5430ACERT — Civil Technology | Associate Certificate | School of Construction and the Environment | associate certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 12 | active | 397 | a55f20332800b370e94ce93597b401e792ee25010d852be0793fcf1fb8ba5c22 | True | none |
| 5440ADCERT — Geographic Information Systems | Advanced Certificate | School of Construction and the Environment | advanced certificate with flat published curriculum | GREEN | none | 0 | active | 398 | 89a9c75cbdf9ba8ab902fc9c98a8240f66ec5cc6f0497035769bf227f522a552 | True | none |
| 5500CERT — Computer Systems | Certificate | School of Computing and Academic Studies | certificate with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 399 | e092eb18481c86fc6f54fb8742045ad090848cb10a5e9bfcdf695c0eac8a2539 | True | none |
| 5515ACERT — Applied Network Administration and Design | Associate Certificate | School of Computing and Academic Studies | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 400 | ff47f42d9e98e9d415b145ff8b78a8677c70ca39f7eea21849a841e6ad294c25 | True | none |
| 5530ACERT — Agile Development | Associate Certificate | School of Computing and Academic Studies | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 401 | b74766a635694d659e13c6876c8dfbeeb61da2576dd248c96ad49573b93a7e23 | True | none |
| 5570ACERT — Computer Aided Design (CAD) Technology | Associate Certificate | School of Energy | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 402 | bb36f3c57cb562fbf0449258596a26a37d1fa07fd8558ca02e0fc95e629aac54 | True | none |
| 5755ACERT — Occupational Health and Safety Practitioners | Associate Certificate | School of Health Sciences | associate certificate with flat published curriculum | GREEN | none | 3 | active | 403 | e0a8fa7166e599d144017fe4c9dba6d5961a2a6a57e690d63b98f6ebb0f6ec75 | True | none |
| 585IACERT — Financial Management (Financial Planning) | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 0 | active | 404 | deb99eb79c571d3193e9323ec9c2ecf9b63e6657020eb3f45f64ff51a889022e | True | none |
| 6005ACERT — Payroll and Human Resources | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 405 | 2b1f577e330b26d52820a1f9a1539e42c4bbb4067b634cace0a8dd3bbf1eea59 | True | none |
| 605DDIPMA — Technology Teacher Education | Diploma | School of Energy | diploma with flat published curriculum | GREEN | none | 33 | active | 406 | 0b8e60070d761614a4bef4e443026ac0727681ade3012c0cc1077c7c0ffec14b | True | none |
| 6115ACERT — Broadcast and Digital Journalism | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 407 | c1a41733b7dd3641fc4291bf2c5d8cb200806a2476890312a75617b3c4ee0d7b | True | none |
| 6120ACERT — Video Production and Editing | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 408 | 72ddb4360cbbc388c0f5d58fc325ee833f36f79625e75a5b0a963e68955dbe45 | True | none |
| 6125ACERT — Radio Arts and Entertainment | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 409 | 36144632cd915bab3642fd4ed706fef56378186f1040fd1bf1db859113eaa45e | True | none |
| 6265ACERT — Lean Six Sigma Principles | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 2 | active | 410 | e5cd28c63ad5fa35147921bd97a6789712561a6b636e4c2bb1cff7a1b1e14e47 | True | none |
| 630DACERT — Marketing Management - Marketing Communications | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 411 | 8fd9431eb422ddd793caeb6e37a04d9feb0bb3f30c5c1bdbed9439ea940d6f56 | True | none |
| 6310ACERT — Nonprofit Management | Associate Certificate | School of Business + Media | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 412 | d111f6fafc609ac59a540db6f768950c3bf59d8581a6bedc113f5f9de7d142f8 | True | none |
| 6315ACERT — Event Marketing and Planning Foundations | Associate Certificate | School of Business + Media | associate certificate with flat published curriculum | GREEN | none | 2 | active | 413 | d47de2178f1405f3e893bc778d184600966526ac28bb26c36468152846e34dde | True | none |
| 635CDIPLT — Mechanical Engineering Technology (Mechanical Systems Option) | Diploma | School of Energy | diploma with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 9 | active | 414 | bc1e5e07bffa6cf923a30203266809df4a78103e8a40ba7d3373b7961fcc700a | True | none |
| 6425ACERT — Technical Writing | Associate Certificate | School of Computing and Academic Studies | associate certificate with flat published curriculum | GREEN | none | 5 | active | 415 | 4ea455156b0f1a1590939161ec686e89802c8972f20b15d02fba61377c3b82d3 | True | none |
| 6645ADCERT — Bridging Medical Radiography | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 5 | active | 416 | b6a0433ff888efefa2e13da609156c7fd1c940cdbeea5ccf2dc7e53e5184e5e9 | True | none |
| 675FACERT — Fire Protection Inspection and Testing | Associate Certificate | School of Construction and the Environment | associate certificate with credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 417 | 4551d7772f6fee311564429d864235e20027b623998dd3aa3d3699af1eae975a | True | none |
| 680BASCERT — Pediatric Nursing Specialty (Standard Option) | Advanced Certificate | School of Health Sciences | advanced certificate with published alternatives or pathways, credit pool, clinical placement | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 418 | 1e5df7aab634bd98ef1a5af77907b0ea7af9bd2edd3a615735b79b1c7a6abab2 | True | none |
| 680CASCERT — Perinatal Nursing Specialty (Standard Option) | Advanced Certificate | School of Health Sciences | advanced certificate with credit pool, clinical placement | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 419 | 30c7490891563787e6bdbe9620bbad2abe85627c00d7a5713b33942da328ca58 | True | none |
| 680EASCERT — Emergency Nursing Specialty (Standard Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 420 | 8a76dbc71b9d2daf9f733e97efcf892fba0d90e869fcb78e346668ac691412c1 | True | none |
| 680LASCERT — Critical Care Nursing Specialty (Combined Critical Care/Emergency Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 421 | 2bfd81671772f4e1918a60939643fe8b722f67760093e8a1ebd9b9a47d201c56 | True | none |
| 680MASCERT — Nephrology Nursing Specialty | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 422 | 5b7de2dbf6c19879b72fc141baed0accba559a94c06dfd46331503130f4eb49a | True | none |
| 680SASCERT — Emergency Nursing Specialty (Combined Emergency/Critical Care Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 423 | d9240e9f0730ac7aab508894a9cd15e0b2b65c641d05e7d6775955c5ca5b4022 | True | none |
| 680WASCERT — High Acuity Nursing Specialty | Advanced Certificate | School of Health Sciences | advanced certificate with published alternatives or pathways, clinical placement | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 424 | 5a2966a5c52d6226a63ccbb17639d31f2e4f2817e73a5c52f60f6459c603660b | True | none |
| 680XADCERT — Critical Care Nursing Specialty | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 425 | d027b7101b4454bd0c9c85db17b138d3a5c956f2f2223f3cb5d6541d2172adf7 | True | none |
| 681BADCERT — Pediatric Nursing Specialty (Anesthesia Care Option) | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 2 | active | 426 | 511797f82aeb18d3506319fe1f7a783339e5ee2d103f000d862a6f8127df9dba | True | none |
| 6957ACERT — Applied Web Development | Associate Certificate | School of Computing and Academic Studies | associate certificate with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 0 | active | 427 | 086044fbaa6e10e8f82f155cc07227d98eb3c9a552657eb526869c48d7d5354b | True | none |
| 6998CERT — Office Administrator with Technology Program (OAT) | Certificate | School of Computing and Academic Studies | certificate with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 5 | active | 428 | fb054884f7b9d92dc456157239f60bd5c37f508c774c4c277ebb30a3e8babacb | True | none |
| 7160ADVDIP — Diagnostic Medical Sonography – Cardiac | Advanced Diploma | School of Health Sciences | advanced diploma with clinical placement | GREEN | none | 10 | active | 429 | 166005c9fe2af7d61cae6943d6f72ff0f207b340ca93326cfa29061b4f0969e4 | True | none |
| 7880ACERT — Construction Operations | Associate Certificate | School of Construction and the Environment | associate certificate with flat published curriculum | GREEN | none | 0 | active | 430 | d14ec0cdfc205851092f3b478d66103288c0b290e3ac78c239c486d32cab42d4 | True | none |
| 7950ASCERT — Magnetic Resonance Imaging | Advanced Certificate | School of Health Sciences | advanced certificate with clinical placement | GREEN | none | 0 | active | 431 | dbe0226b4b7c0baf4dcb5daa057631e6cf7ce301814a90d646cac55fc76df552 | True | none |
| 8350BTECH — Technology Management | Bachelor of Technology | School of Transportation | bachelor of technology with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter plus reusable published component-credit fallback | 4 | active | 432 | 7ca1eb7f2933884ce596c920eb6922dd8438b2e5ab2ac211c9d816b3658ef73e | True | none |
| 847ABTECH — Forensic Investigation (Crime and Intelligence Analysis Option) | Bachelor of Technology | School of Computing and Academic Studies | bachelor of technology with published alternatives or pathways, credit pool | YELLOW | existing Batch 01 connector/pathway adapter plus deterministic unique rule-name normalization | 7 | active | 433 | 1175e749b766f522a2f7a10a01d4208bcd5ea42e58b3980fca85287860e2867f | True | none |
| 847BBTECH — Forensic Investigation (Forensic Science Option) | Bachelor of Technology | School of Computing and Academic Studies | bachelor of technology with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter plus deterministic unique rule-name normalization | 16 | active | 434 | fcb825628e6b7e7c89a5d899fa7127fd8522354a27cdc55d9024a0440fb18503 | True | duplicate course reference normalized during import: FSCT8340; duplicate course reference normalized during import: FSCT8110; duplicate course reference normalized during import: FSCT8140; duplicate course reference normalized during import: FSCT8320 |
| 847CBTECH — Forensic Investigation (Digital Forensics and Cybersecurity Option) | Bachelor of Technology | School of Computing and Academic Studies | bachelor of technology with flat published curriculum | GREEN | none | 10 | active | 435 | 41c2d54f8df54293934edf8d970625d0bb4d3ea131b330c026453e6e67e95b76 | True | none |
| 8610BENG — Mining and Mineral Resource Engineering | Bachelor of Engineering | School of Construction and the Environment | bachelor of engineering with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 55 | active | 436 | 51223f49cf67c978f8a933d922af7b0c0d7f29f83cd7b8044afc1a0bb4f5167c | True | none |
| 867ABSC — Applied Computer Science (Games Development Option) | Bachelor of Science | School of Computing and Academic Studies | bachelor of science with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 5 | active | 437 | 94f6de6ff0d75056bc16bd43e2f94c68a751a27c5f48a27a032c63f3daf45c07 | True | none |
| 8830BID — Interior Design | Bachelor of Interior Design | School of Construction and the Environment | bachelor of interior design with published alternatives or pathways, credit pool, non-course component | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 14 | active | 438 | 1684ccc57892ce18c45208640b7606ce102d72f692943e3bbea0ba49029fdf37 | True | none |
| 9100FADVDIP — Geographic Information Systems | Advanced Diploma | School of Construction and the Environment | advanced diploma with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 1 | active | 439 | 4809c862d03c0275ca28cb09ed0993a639add8f5eccc5036530f888bc9a0a514 | True | none |
| 9100PADVDIP — Geographic Information Systems | Advanced Diploma | School of Construction and the Environment | advanced diploma with published alternatives or pathways | YELLOW | existing Batch 01 connector/pathway adapter; no new code | 2 | active | 440 | 9933ed5f0fc0d5a693eb4eba6f109ee45a793d3bb4fef98688c41462906788dd | True | none |

## Engineering-rate comparison

Batch 01: 41.67% (5/12). Batch 02: 0.00% (0/24). Batch 03: 0.00% (0/50). Batch 04: 3.00% (3/100); two reusable normalization extensions were added after the complete audit exposed one absent aggregate total and two repeated component-order records.

## Final validation

- Exact-hash active revisions: 99/99

- Post-import zero diff: 99/99

- Unresolved course references: 0

- Ownership violations: 0

- Final catalog: 209 active programs and 3288 courses

- Active programs missing normalized ADMISSION rules: 0

- Python regression suite: 422 passed of 422; 0 failures, 0 errors

- Browser-state suite: 5 passed of 5

- Approximate runtime: 43.0 minutes
