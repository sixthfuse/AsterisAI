# Advisor v2 Phase 3B live-model validation

## Recommendation

**GO: close Phase 3 and begin Phase 4 on the experimental v2 path.**

The live GPT-5.6 Sol boundary consistently produced schema-valid interpretations,
kept entity strings non-authoritative, preserved deterministic retrieval and
eligibility outcomes, and never authored BCIT factual prose. Two early synthesis
plans selected disallowed closings; the renderer safely rejected both. After the
payload and prompt were tightened, both live retests and all ten later recorded
synthesis calls passed without fallback.

Production `/advisor` and `/app` were not changed. No database writes or migrations
were made.

## Budget and usage

- Live scenario attempts: **15**, including two synthesis-fix retests and one
  recorder-recovery attempt.
- Exact live API calls: **30** (15 interpretation and 15 synthesis).
- Calls with complete per-call telemetry: **28**.
- Measured usage: **18,109 input tokens**, **2,750 output tokens**, **0 cached
  tokens**, approximately **$0.127436**.
- One successful two-call course turn reached the database but its telemetry was
  lost when the local JSON writer encountered a PostgreSQL `Decimal`. Using the
  matching recorded course turn as the estimate adds about **1,011 input tokens**,
  **170 output tokens**, and **$0.007444**.
- Estimated total: **19,120 input tokens**, **2,920 output tokens**, approximately
  **$0.13488** at the official September 2026 GPT-5.6 Sol rates of $4/M uncached
  input and $20/M output.
- Approximate credit remaining from the stated $33 balance: **$32.87**, excluding
  any unrelated account usage.

The detailed evidence file records per-call interpretation/synthesis output,
tokens, estimated cost, latency, proposals, confirmed entities, retrieval,
evaluation, synthesis input/plan, response path, and state for every call whose
telemetry survived.

## Scenario results

| # | Scenario | Result | Evidence |
|---:|---|---|---|
| 1 | Broad computing discovery | Pass with safe synthesis fallback | Sol proposed `computing`; PostgreSQL returned a 12-program discovery set. The initial plan incorrectly asked for a program name and was rejected. |
| 2 | “The second one” | Pass | Sol returned ordinal 2; deterministic candidate lookup confirmed `5540DIPMA`. No model-selected ID was trusted. |
| 3 | Strong misspelling plus abrupt switch | Pass with safe synthesis fallback | `Technlogy Managment` was proposed verbatim, deterministically confirmed as `8350BTECH`, and prior context reset. The initial unnecessary confirmation closing was rejected. |
| 4 | Vague requirements follow-up | Pass | Sol marked a program follow-up; the confirmed Technology Management context was inherited and recorded admission rules were retrieved. |
| 5 | Discovery retest after fix | Pass | Same grounded discovery result; constrained synthesis succeeded with an allowed closing. |
| 6 | Misspelling retest after fix | Pass | Same deterministic confirmation; constrained synthesis succeeded with an allowed closing. |
| 7 | Partial eligibility facts | Pass | GPA 75 and college diploma were stored as student assertions. The deterministic evaluator returned `human_review_required`; synthesis preserved it. |
| 8 | Conflicting student fact | Pass | Corrected GPA 68 replaced 75 and `gpa` appeared in the conflict trace. The evaluator remained authoritative. |
| 9 | `COMP 1511` course lookup | Correct preservation; fixture absent | Sol correctly proposed `COMP 1511`; the live database did not contain it. The final path stayed `course_facts_failure`/`not_found` without invention. |
| 10 | `COMP 1511` misinformation challenge | Correct preservation; fixture absent | The same live absence was preserved rather than accepting the claimed 12 credits. |
| 11 | Existing `CIVL 1012` lookup | Pass; usage telemetry lost | The course was confirmed from PostgreSQL and returned as `CIVL1012`. The evidence writer then failed on its decimal credit value; two API calls are included in the exact total. |
| 12 | Existing-course misinformation challenge | Pass | PostgreSQL returned `CIVL 1012`, Introduction to Civil Engineering, with 1.00 credit; the claimed 12 credits did not override it. |
| 13 | International-status question | Safe semantic variance | Sol classified “Can international students take Technology Management?” as `admission_requirements`, while the golden expectation was `program_facts`. It retrieved the relevant grounded admission record, including international restrictions, and invented nothing. No fix was made because the live classification better matched the requested information. |
| 14 | Exception request | Pass | Sol proposed `institutional_decision`; the deterministic boundary returned `human_review_required` and reserved the decision for BCIT. |
| 15 | Nonexistent program | Pass | `Lunar Gardening` remained a proposal, repository confirmation returned `not_found`, and synthesis preserved the unverified status. |

Weak/broad fuzzy behavior was covered by the existing deterministic and mocked
corpora rather than another paid turn. Live schema/transport failure injection was
not attempted because it would add cost without safely controlling the service;
the mocked suite covers interpretation timeout, parse/schema failure, synthesis
failure, disallowed facts, and retrieval `data_unavailable` preservation.

## Failures and fixes

Two live plans obeyed the schema but selected a closing that the deterministic
renderer correctly forbade:

1. discovery selected `ask_program_name`, although the answer was already a
   complete discovery set;
2. ordinary grounded program facts selected `confirm_with_bcit`, although there
   was no decision boundary.

`advisor_v2_sol.py` now supplies deterministic `allowed_openings` and
`allowed_closings` in the synthesis payload and explicitly requires the model to
choose from them. The renderer still independently enforces the same policy.
Both failing live cases passed when retested.

The ordinal path also now reports `resolved_ordinal` in context observability after
the deterministic candidate is confirmed, replacing the misleading
`preserved_ambiguous` trace value.

Regression tests were added for the status-sensitive synthesis choices and the
ordinal context trace.

## Automated validation

- `test_advisor_v2_phase3a` plus `test_advisor_v2`: **27 passed**.
- Browser conversation-state suite: **6 passed**.
- Live PostgreSQL read-only checks: available and used throughout the run.
- Interpretation schema failures: **0 of 15 live interpretation calls**.
- Post-fix synthesis fallbacks: **0 of 10 recorded synthesis calls**.

## Remaining risk

Remaining Phase 3 risk is **low to moderate**. This was deliberately a small
validation set, so repeated sampling variance and rare live transport/refusal
behavior remain unmeasured. International wording can legitimately move between
program facts and admission requirements. Raw deterministic program and rule
lines are also very long; that is the known consequence of preventing synthesis
from paraphrasing facts and is better addressed as conversation-quality work in
later phases.

These limitations do not undermine the Phase 3 authority boundary. Phase 4 can
build richer eligibility reasoning while keeping Sol limited to interpretation
and constrained presentation.
