# BCIT International Eligibility Enrichment Plan — Read Only

No PostgreSQL writes, migration, advisor changes, or enrichment were performed. All reads use a server-enforced read-only repeatable-read transaction.

## Decision
NO-GO: fewer than 50 verified changes or baseline/schema blockers.

Program actions: {"INSERT":0,"SKIP":0,"UNCHANGED":266,"UPDATE":0}
Program action convention: UPDATE if any row is updated; otherwise INSERT if any row is inserted; UNCHANGED if existing evidence is semantically correct; SKIP for a blocked deterministic program. Unknown-program SKIPs are counted separately from blocked deterministic programs.
Database row actions: {}
Ready for enrichment: 0; blocked deterministic programs: 0; unknown untouched: 108.
Schema migration required: no. Existing text evidence columns suffice; no new permit/PGWP columns or condition types are introduced.
Nursing actions: {"UNCHANGED":13}. Matching rules are reused, even when no delivery-facts row exists.
Validation: {"focused_tests_exit_code":0,"focused_tests_passed":true,"shared_production_code_touched":false}. The focused_tests.txt log records each test, including in-memory apply/replan duplicate prevention.
Existing Accounting/Business Administration INTERNATIONAL rules and conditions are preserved, including their work-component, study-permit and PGWP restrictions.

## Verification
Raw-byte and stable-content SHA-256 are retained. Only the observed WordPress Last generated timestamp comment is normalized; all other byte changes block the source. URL fragments identify sections and are removed for document identity; query strings and host/path changes are rejected. Nursing audit HTML lacked a published audit hash: its retained bytes are hashed now and compared to live bytes; this does not retroactively authenticate the original snapshot.
Offering Domestic Only rows are retained as dated audit context only, with their source verification outcome; no offering updates are proposed.
Snapshot input SHA-256: 5a3205bb05c10c9b5a166dfb80dcb96f6570ade81ef6d9663b63fc7027dc11ee
Proposal SHA-256: 8238dd8bfd058dd31d6e01a0169584dfa8b601140dc89879606aa6350d6481f3
Idempotency: {"definition":"Fixed database, audit and source input snapshots include fixed retrieval timestamps. No run clock participates in proposal generation.","replay_identical":true,"two_independent_builds_identical":true}
Database snapshot unchanged: True

## First batch
Programs without Domestic Only scope first, then exact program ID ascending; unchanged programs excluded.
No verified batch available.

## All deterministic programs
| Program | Title | Status | Action | Blockers |
|---|---|---|---|---|
| 0800CM | Introductory Studies in Mass Timber Construction | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0803CM | Script Supervision and Continuity for Film and TV | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0810CM | Low-Code Mobile Application Development | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0811CM | Essentials of Data Networks | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0812CM | Cybersecurity Analysis for Network Administrators | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0813CM | Advanced Forensic Nurse Examiner | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0815CM | Supervising Net-Zero and Passive House Construction | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0816CM | Applied Circular Economy: Zero Waste Buildings | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0819CM | Essentials of Net-Zero and Passive House Construction | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0820CM | Cybersecurity Essentials for IT Professionals | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0822CM | Food Safety Preventive Controls and HACCP Plans | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0825CM | Canadian Employment Readiness (CER) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0826CM | Technical Communication Essentials | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0828CM | Student Mobility Preparedness | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0829CM | Building Energy Modelling and Simulation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0830CM | Whole-Building Life Cycle Assessment Professional | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0832CM | Cybersecurity Operations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0833CM | Forensic Nurse Death Investigator | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0835CM | International Education Practitioner - Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0837CM | Foundational Digital Forensics Skills | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0838CM | Automotive Service Management Essentials | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0840CM | Introduction to Full-Stack Web Development | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0841CM | Web Development Foundations (WDF) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0842CM | Data Visualization with MS Power BI | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0843CM | Spanish Language and Culture Fundamentals | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0844CM | Fundamentals of Virtual Containers | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0845CM | Network Switching and Routing | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0847CM | Wind Turbine Essentials | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0848CM | Advanced Topics in Networking | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0849CM | Asbestos Awareness and Safety | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0850CM | Fraud and Financial Crime Investigation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0852CM | Canadian Engineering Professional Practice | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0854CM | Essentials of Community Energy and Emissions Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0855CM | Thermal Power Plant Simulation Proficiency | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0859CM | Sexual and Reproductive Health Foundations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0861CM | Climate Changemakers Leadership Training | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0864CM | Marine Business Essentials | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0866CM | Distribution Design for Electrical Utilities | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0870CM | Sexual Health Rehabilitation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0872CM | Techniques for Crime & Intelligence Analysts (TCIA) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0873CM | Fundamentals in Polytechnic Teaching | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 0876CM | Applied Mass Timber Engineering | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 100ADIPMA | Airline and Flight Operations Commercial Pilot (Fixed-Wing) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 100BDIPMA | Airline and Flight Operations Commercial Pilot (Rotary-Wing) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1030CERTTS | Aircraft Gas Turbine Technician | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1070ACERT | Airport Operations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1155ACERT | Construction Drawings | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1165DIPMA | Aircraft Maintenance Engineer Category ‘E’ (Electronics) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1175DIPMA | Aviation Management and Operations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1205DIPMA | Aircraft Maintenance Engineer Category 'S' (Structures) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1230DIPMA | Aircraft Maintenance Engineer Category 'M' (Maintenance) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1320ADCERT | Automated Controls Installation and Maintenance | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1430DIPMA | Automotive Service Technician and Operations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 143BDIPMA | Automotive Service Technician and Operations - Non-Co-op Option | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1645CERT | Carpentry Framing and Forming Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1710CERTTS | Architectural and Structural CADD and Graphics Technician (Structural Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1720CERTTS | Architectural and Structural CADD and Graphics Technician (Architectural Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1790ACERT | Hydronic Technician | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1855DIPMA | Heavy Duty Truck Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1930DIPMA | Computer Information Systems Administration | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 1940CERT | Heavy Mechanical Trades Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2060CERT | Cabinetmaker (Joiner) Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2175TTCERT | Machinist Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2410TTCERT | Power Engineering (General Program) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2425CERT | Refrigeration and Air Conditioning Mechanic Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2430DIPMA | Power and Process Engineering | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2440CERT | Piping Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2645CERT | Sheet Metal Worker Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2825CERT | Metal Fabricator Foundation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2915CERT | Security Systems Technician | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 2945DIPMA | Industrial Instrumentation and Process Control Technician | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5063DIPMA | Biomedical Engineering Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5077CERT | Event Marketing and Management Strategy | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5085ACERT | Project Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5105DIPMA | Digital Communications and Wireless Technologies | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5115ACERT | Music Business | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5140ACERT | Business Administration | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5155DIPMA | Food Processing, Safety, and Quality | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5165ADCERT | Digital Health | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5170ACERT | Healthcare Unit Clerk | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5175ACERT | Polytechnic Teaching | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5180ADVDIP | Sustainable Business Leadership | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5235ADCERT | Building Energy Modelling and Performance Analysis | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5240ADVDIP | Technical Arts | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5265DIPMA | Industrial Network Cybersecurity | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 528AADCERT | Forensic Investigation (Crime and Intelligence Analysis Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 528BADCERT | Forensic Investigation (Forensic Science Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 528CADCERT | Forensic Investigation (Digital Forensics and Cybersecurity Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5290ADVDIP | Professional Accounting | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5312ADVDIP | Business Management - Advanced Diploma | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5325ACERT | Foundations in Occupational Health and Safety | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 534ADIPMA | Electrical and Computer Engineering Technology (Automation and Instrumentation Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 534BDIPMA | Electrical and Computer Engineering Technology (Electrical Power and Industrial Control Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 534CDIPMA | Electrical and Computer Engineering Technology (Telecommunications and Networks Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5375DIPMA | Chemical and Environmental Engineering Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5410DIPLT | Civil Engineering Diploma | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5440ADCERT | Geographic Information Systems | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5500CERT | Computer Systems | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5500DIPMA | Computer Systems Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5500PDIPLT | Computer Systems | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5512CERT | Applied Data Analytics | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5540DIPMA | Computer Information Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5725ACERT | Computerized Accounting | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 585CMCERT | Financial Management (Finance Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 585FMCERT | Financial Management (Professional Accounting Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 585IACERT | Financial Management (Financial Planning) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5880DIPLT | General Insurance and Risk Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 5985ACERT | User Interface (UI) and User Experience (UX) Design | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6005ACERT | Payroll and Human Resources | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6008CERT | Payroll Administration | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6030CERT | Architectural and Building Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6035DIPMA | Accounting | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6035PDIPMA | Accounting | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6045DIPMA | Finance | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6045PDIPMA | Finance | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6055DIPMA | Financial Planning | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6055PDIPMA | Financial Planning | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6110DIPMA | Radio Arts and Entertainment | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6115ACERT | Broadcast and Digital Journalism | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6120ACERT | Video Production and Editing | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6125ACERT | Radio Arts and Entertainment | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6130DIPMA | Television & Video Production | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6135DIPMA | Broadcast and Online Journalism | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6140DIPMA | Residential Interiors | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6185ADCERT | Renewable Energy Electrical Systems Installation & Maintenance | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6195CERT | Interior Design Fundamentals | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6220FDIPMA | Interior Design | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6220PDIPMA | Interior Design | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6225ACERT | Global Business Studies | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6235DIPMA | Business Information Technology Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 623ADIPMA | Business Information Technology Management (Artificial Intelligence Management Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 623BDIPMA | Business Information Technology Management (Enterprise Systems Management Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 623CDIPMA | Business Information Technology Management (Analytics Data Management Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6245DIPLT | Business Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6245MCERT | Business Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6247DIPMA | Graphic Communications | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 625AMCERT | Human Resource Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6265ACERT | Lean Six Sigma Principles | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6290DIPMA | Strategic Human Resources Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6300MCERT | Marketing Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 630DACERT | Marketing Management - Marketing Communications | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 630DMCERT | Marketing Management (Marketing Communications Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 630HACERT | Marketing Management - Entrepreneurship | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 630MACERT | Marketing Management - Sales Skills | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 630PMCERT | Media Techniques and Marketing Communications | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 630VMCERT | Marketing Management (Professional Sales Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 630WACERT | Marketing Management - Customer Relationship Marketing | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 630XACERT | Marketing Management - Public Relations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6310ACERT | Nonprofit Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 635CDIPLT | Mechanical Engineering Technology (Mechanical Systems Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 635DDIPLT | Mechanical Engineering Technology (Mechanical Design Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 635EDIPLT | Mechanical Engineering Technology (Mechanical Manufacturing Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6375ACERT | Digital Marketing Foundations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6385ACERT | Digital Marketing Strategy | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6390ACERT | Marketing Management - Fundraising Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6422DIPMA | Marketing Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6425ACERT | Technical Writing | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 642ADIPMA | Marketing Management (Digital Marketing and Brand Strategy Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 642BDIPMA | Marketing Management (Professional Sales Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 642CDIPMA | Marketing Management (Entrepreneurship Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 642DDIPMA | Marketing Management (Professional Real Estate Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 642EDIPMA | Marketing Management (Tourism Marketing and Sales Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6450MCERT | Media Techniques for Business | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6505ACERT | Graphic Design Foundations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6515DIPMA | Digital Design and Development | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6525DIPMA | New Media Design and Web Development | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6530CERT | Construction Estimating | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6535CERT | Front-End Web Developer | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6575DIPMA | 3D Modeling, Art and Animation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6585CERT | Graphic Design | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6590ACERT | Tourism and Hospitality | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6595DIPMA | Graphic Design and Interactive Media | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6630ACERT | Medical Office Assistant | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6640DIPMA | Mineral Exploration and Mining Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6760ACERT | Mechanical Systems | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680BASCERT | Pediatric Nursing Specialty (Standard Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680CASCERT | Perinatal Nursing Specialty (Standard Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680EASCERT | Emergency Nursing Specialty (Standard Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680FASCERT | Neonatal Nursing Specialty | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680LASCERT | Critical Care Nursing Specialty (Combined Critical Care/Emergency Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680MASCERT | Nephrology Nursing Specialty | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680PASCERT | Perioperative Nursing Specialty | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680SASCERT | Emergency Nursing Specialty (Combined Emergency/Critical Care Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680VASCERT | Perinatal Nursing Specialty (Perinatal - Perioperative Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680WASCERT | High Acuity Nursing Specialty | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680XADCERT | Critical Care Nursing Specialty | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680YADCERT | Emergency Nursing Specialty (Pediatric Emergency Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 680ZADCERT | Pediatric Nursing Specialty (Critical Care Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 681BADCERT | Pediatric Nursing Specialty (Anesthesia Care Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6830ACERT | Leadership | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6835ADCERT | Pediatric Emergency Nursing Specialty | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6850DIPLT | Occupational Health and Safety | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6860ADCERT | Health Leadership | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6890CERT | Advanced Safety Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 690AMCERT | Operations Management (Industrial Engineering Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 690BMCERT | Operations Management (Management Engineering Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 690DMCERT | Operations Management (Materials Management Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 690FMCERT | Operations Management (Facilities Management Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6915DIPMA | Operations & Management Engineering | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6945CERT | Quality and Process Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 6998CERT | Office Administrator with Technology Program (OAT) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 703ADIPMA | Business Administration (General Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 703BDIPMA | Business Administration (Global Studies Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 703CDIPMA | Business Administration (Human Resources Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 703DDIPMA | Business Administration (Management Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 703EDIPMA | Business Administration (Marketing Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7110CERT | Technology Support Professional (TSP) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7140DIPMA | Architectural and Building Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7340DIPLT | Mechatronics and Robotics | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7460MCERT | International Trade and Transportation Logistics | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7475DIPMA | Global Supply Chain Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7535DIPMA | Geomatics Engineering Technology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7610ACERT | Human Resource Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7710DIPMA | Construction Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7870CERT | Construction Supervision | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7880ACERT | Construction Operations | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7935DIPMA | Fish, Wildlife and Recreation | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 7985ACERT | Business Fundamentals | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8040BSC | Ecological Restoration | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8050BTECH | Architectural Science | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 810ABSN | Specialty Nursing (Critical Care - Standard Option), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810BBSN | Specialty Nursing (Emergency - Standard Option), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810CBSN | Specialty Nursing (Neonatal), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810DBSN | Specialty Nursing (Nephrology), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810FBSN | Specialty Nursing (Pediatric - Standard Option), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810GBSN | Specialty Nursing (Perinatal - Standard Option), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810HBSN | Specialty Nursing (Perioperative), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810KBSN | Specialty Nursing (Critical Care - Combined Critical Care/Emergency Option), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810MBSN | Specialty Nursing (High Acuity), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810NBSN | Specialty Nursing (Emergency - Combined Emergency/Critical Care Option), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810QBSN | Specialty Nursing (Pediatric - Critical Care Option), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 810SBSN | Specialty Nursing (Perinatal - Perioperative Option), Bachelor of Science in Nursing, Part-time | CONDITIONAL_RESTRICTED | UNCHANGED |  |
| 8120BTECH | Environmental Engineering | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8310BTECH | Geographic Information Systems | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8350BTECH | Technology Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 847BBTECH | Forensic Investigation (Forensic Science Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 847CBTECH | Forensic Investigation (Digital Forensics and Cybersecurity Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8520BENVH | Environmental Public Health | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8610BENG | Mining and Mineral Resource Engineering | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8630BACC | Accounting | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8645BSC | Geomatics | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8660BENG | Civil Engineering Bachelor of Engineering | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 867ABSC | Applied Computer Science (Games Development Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 867BBSC | Applied Computer Science (Network Security Applications Development Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 867CBSC | Applied Computer Science (Database Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 867DBSC | Applied Computer Science (Human Computer Interface Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 867EBSC | Applied Computer Science (Network Security Administration Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 867FBSC | Applied Computer Science (Wireless and Mobile Applications Development Option) | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8800BTECH | Construction Management | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8830BID | Interior Design | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8875BSN | Nursing, Bachelor of Science in Nursing, Full-time | NOT_ACCEPTED | UNCHANGED |  |
| 8900BTECH | Electronics | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 8910BSC | Honours in Biotechnology | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 9100FADVDIP | Geographic Information Systems | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 9100PADVDIP | Geographic Information Systems | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 9940BSC | Combined Honours in Biochemistry and Forensic Science | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 9975BBA | Bachelor of Business Administration | ACCEPTED_AVAILABLE | UNCHANGED |  |
| 9980BCI | Bachelor of Creative Industries | ACCEPTED_AVAILABLE | UNCHANGED |  |
| A500GRCERT | Global Leadership | ACCEPTED_AVAILABLE | UNCHANGED |  |
| A600GRCERT | Business Analytics | ACCEPTED_AVAILABLE | UNCHANGED |  |
| A700GRCERT | Business Administration | ACCEPTED_AVAILABLE | UNCHANGED |  |
| M120MENG | Building Science | ACCEPTED_AVAILABLE | UNCHANGED |  |
| M220MASC | Building Engineering/Building Science | ACCEPTED_AVAILABLE | UNCHANGED |  |
| M410MSC | Ecological Restoration | ACCEPTED_AVAILABLE | UNCHANGED |  |
| M500MENG | Smart Grid Systems and Technologies | ACCEPTED_AVAILABLE | UNCHANGED |  |
| M600MSC | Applied Computing | ACCEPTED_AVAILABLE | UNCHANGED |  |

## Unknown programs — untouched
| Program | Title |
|---|---|
| 0801CM | Essentials of Natural Resource and Environmental Protection (MENREP) |
| 0804CM | Forensic Nurse Examiner Education for RNs |
| 0805CM | Breast Sonography |
| 0806CM | Musculoskeletal Sonography |
| 0814CM | Essential Field Skills for Environmental Professionals |
| 0817CM | Introduction to Forest Health Quantification with RPAS |
| 0823CM | Food Safety Management |
| 0824CM | Animal Cell Culture |
| 0831CM | Industrial Networking for Cybersecurity Professionals |
| 0836CM | Drone Applications for Environmental Risk Assessment |
| 0839CM | Fiber Optics - Principles, Installation and Repair |
| 0846CM | Sterile Field and the Aseptic Environment |
| 0851CM | Aircraft Defect Inspection and Reporting Techniques |
| 0853CM | Principles of Regenerative Building |
| 0856CM | Retrofit Solutions for Rural Communities |
| 0857CM | Automotive Collision Estimator |
| 0860CM | Heat Pump Maintenance and Troubleshooting |
| 0862CM | Residential Air to Air Heat Pump Specialist |
| 0865CM | Introduction to Power Systems Protection Design |
| 0869CM | Occupational Health and Safety Essentials |
| 0874CM | Fundamentals in Architecture, Construction, and Engineering |
| 0875CM | Applied Additive Manufacturing |
| 1180ACERT | Trades Discovery General |
| 1190ACERT | Trades Discovery for Women |
| 1195IPCERT | Advanced Gas Turbine |
| 1255CERT | Auto Body Repair and Refinishing Technician Foundation |
| 1355TTCERT | Automotive Technician Foundation |
| 1360CERT | Automotive Technician (Honda/Acura Foundation) |
| 1375TTCERT | Automotive Technician (Toyota Foundation) |
| 143ADIPMA | Automotive Service Technician and Operations (Ford ASSET Option) |
| 1450TTCERT | Boilermaker Foundation |
| 1525TTDIPL | CNC Machinist Technician |
| 1685ACERT | Railway Conductor and Operations |
| 1780CERT | Electrical Foundation |
| 1885ACERTS | Network Administrator Technician |
| 1920CERT | Marine Mechanical Technician Foundation |
| 2000TTCERT | Ironworker Foundation |
| 2020CERTTS | Chief Mate |
| 2230CERT | Millwright Foundation |
| 2365CERT | Motorcycle Technician Foundation |
| 2505ACERTS | Master 150GT Domestic |
| 2515ACERTS | Master 500GT Domestic |
| 2522CERTTS | Master 3000GT Domestic |
| 2536DIPMA | Nautical Sciences |
| 2542CERTTS | Watchkeeping Mate Near Coastal (WKMNC) |
| 2847CERT | Welder Foundation |
| 2860TTCERT | Welding, Level B |
| 2870TTCERT | Welding, Level A |
| 2885ADVDIP | Marine Engineering |
| 2933ACERT | Bridge Watch Rating |
| 2942DIPMA | Marine Engineering |
| 2958CERT | Heating, Ventilation, Air Conditioning and Refrigeration Technician |
| 2992DIPMA | Heating, Ventilation, Air Conditioning and Refrigeration Technician |
| 5125ACERT | Business of Sawmilling |
| 5145ADCERT | Sustainable Business |
| 515GACERT | Building Construction Technology |
| 515HACERT | Building Design and Architectural CAD |
| 5160ACERT | Industrial Wood Processing |
| 5180PADVDIP | Sustainable Business Leadership |
| 5205ACERT | Business Analysis |
| 5225ACERT | Construction of Mass Timber Structures |
| 5245ACERT | Artificial Intelligence Management |
| 5275ACERT | Business Intelligence |
| 5295ACERT | Business Data Management |
| 530ADIPLT | Cardiology Technology |
| 5310ADCERT | Cardiac Sciences (Cardiovascular Technology Option) |
| 5320ADCERT | Cardiac Sciences (Electrophysiology Technology Option) |
| 5330ADCERT | Cardiac Sciences (Cardiac Rhythm Device Technology Option) |
| 5365ACERT | Digital Media Foundations |
| 5430ACERT | Civil Technology |
| 5430CERT | Civil Technology |
| 5515ACERT | Applied Network Administration and Design |
| 5530ACERT | Agile Development |
| 5570ACERT | Computer Aided Design (CAD) Technology |
| 5670ADVDIP | Clinical Genetics Technology |
| 5755ACERT | Occupational Health and Safety Practitioners |
| 576ADIPMA | Diagnostic Medical Sonography (General Sonography Option) |
| 576BDIPMA | Diagnostic Medical Sonography (Cardiac Sonography Option) |
| 576CDIPMA | Diagnostic Medical Sonography (General and Cardiac Sonography Option) |
| 5810DIPMA | Electroneurophysiology |
| 6040ACERT | Fundamentals of Water and Wastewater Operations |
| 605DDIPMA | Technology Teacher Education |
| 6090CERT | Essential Technical Skills for Architecture, Construction, and Engineering |
| 6285CERT | Fire Service Industry Leadership |
| 6315ACERT | Event Marketing and Planning Foundations |
| 6365ACERT | Food Safety |
| 6465ACERT | Web and Mobile Application Development |
| 6615DIPMA | Medical Laboratory Science |
| 6635DIPMA | Medical Radiography |
| 6645ADCERT | Bridging Medical Radiography |
| 6705DIPMA | Nuclear Medicine |
| 675FACERT | Fire Protection Inspection and Testing |
| 6820ASCERT | Cardiovascular Perfusion |
| 6957ACERT | Applied Web Development |
| 6958ACERT | Applied Software Development (ASD) |
| 6992ACERT | Applied Computer Information Systems (ACIS) |
| 6994ACERT | Applied Database Administration and Design |
| 7100DIPLT | Prosthetics and Orthotics |
| 7160ADVDIP | Diagnostic Medical Sonography – Cardiac |
| 7485DIPMA | Forest and Natural Areas Management |
| 7950ASCERT | Magnetic Resonance Imaging |
| 7975DIPMA | Magnetic Resonance Imaging |
| 8020BENG | Mechanical Engineering |
| 8030BENG | Electrical Engineering |
| 830ABHSC | Bachelor of Health Science (Magnetic Resonance Imaging Option) |
| 847ABTECH | Forensic Investigation (Crime and Intelligence Analysis Option) |
| 8650BSC | Radiation Therapy |
| A200GRCERT | Building Energy Modelling |

## Review files
The JSON and CSVs contain current complete stored state, exact candidate rows, permitted proposal actions, sources, hashes, retrieval times and restrictions. Blocked rows have no proposed executable actions; candidate rows are review-only.
Run: `.\.venv\Scripts\python.exe -B bcit_international_enrichment_planner.py`; deterministic replay: add `--replay`. No apply option exists.