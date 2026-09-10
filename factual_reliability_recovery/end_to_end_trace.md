# End-to-end trace table

All after-repair turns used the synchronous `/advisor` JSON endpoint used by `/app`. `OpenAI` was patched to raise if constructed; all ten turns completed, proving zero model calls.

| Turn | Resolved scope/entity | Tool/evidence route | Model | Historical loss layer |
|---:|---|---|---|---|
| 1 | none | deterministic greeting | no | No factual loss; institution voice was generic. |
| 2 | technology | search_programs | no | Institution identity was phrased as platform ownership. |
| 3 | do you offer any biotechnology or biochem programs? | search_programs | no | Institution identity was phrased as platform ownership. |
| 4 | global | get_catalog_counts | no | Institution identity was phrased as platform ownership. |
| 5 | engineering | compare_programs | no | Subject extraction and tool arguments: engineering was misclassified as a credential; the empty packet then became unverifiable prose. |
| 6 | can a red seal | find_programs_by_admission_evidence | no | Admissions evidence discovery searched program metadata rather than condition evidence. |
| 7 | nursing programs | compare_programs | no | Raw model/tool protocol reached the API answer and browser renderer; international rows were not guaranteed to control the prose. |
| 8 | I have my Red Seal. Can I use that to get into any BCIT programs, or does it count toward admission requirements? | find_programs_by_admission_evidence | no | Admissions evidence discovery missed cross-program Red Seal conditions and raw protocol reached rendering. |
| 9 | engineering | search_programs | no | Spanish subject normalization did not map ingenieria to engineering, causing an empty query. |
| 10 | 8350BTECH | evaluate_admission_profile | no | Applicant-background suppression plus credential-family routing prevented exact program resolution; the admission packet was never retrieved. |
