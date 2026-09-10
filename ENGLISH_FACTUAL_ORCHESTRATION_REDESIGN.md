# English Factual Orchestration Redesign

## Release status

**Engineering gates passed. Founder browser acceptance is pending and remains the final release gate.**

This phase does not authorize UI or personality work. Spanish was not expanded or removed.

## Result

The `/advisor` path now records and enforces this pipeline for each answer:

**UNDERSTAND → RESOLVE → RETRIEVE → VERIFY → ANSWER**

The current turn is classified independently of saved conversation state. Saved state may resolve a clear follow-up such as “their phone numbers,” “this program,” or “tell me more.” It may not manufacture relevance for an unrelated turn.

Before a factual candidate answer is released, the verifier checks that:

- the selected handler/tool family is compatible with the current question or freshly resolved subject;
- a carried subject was explicitly referenced when the current turn did not establish a new one;
- retrieved factual results include verification metadata or governed institutional-resource records;
- a model-generated factual answer is not released without retrieved evidence;
- capability, conversational, and off-topic answers do not invoke factual tools.

On verification failure, the factual candidate is withheld, active subject state is cleared, and Asteris asks for a concrete program, course, campus, or BCIT target. Student facts and bounded verified memory are preserved.

## Accuracy lanes

- **FAST:** direct deterministic counts, capability answers, greetings, and off-topic boundaries.
- **NORMAL:** program/course/campus information and ordinary factual follow-ups.
- **DEEP:** eligibility, applicant facts, comparisons, international availability, progression, and graduation.

The lane is visible in the orchestration trace. It does not weaken the standing Sol Medium configuration; factual evidence remains authoritative in every lane.

## Exact regression fixed

Conversation:

1. “How many campuses does BCIT have?”
2. “How many languages can you speak?”

Before this redesign, campus state could append “campuses” to the second question and release campus data. Now the second turn is answered deterministically as an Asteris capability question, uses no factual tool, clears the campus subject, and records a passed verification decision.

The valid follow-up “What are their phone numbers?” still reuses the campus directory and passes verification.

## Deterministic certification

- Full Python suite: **591/591 passed** in 751.397 seconds.
- Browser-state suite: **6/6 passed**.
- New orchestration suite: **9/9 passed**.
- Every active governed program name: **374/374 resolved to its canonical program ID**.
- Model-blocked standalone factual/capability matrix: **16/16 real `/advisor` requests passed**.
- Exact prior recovery conversation: **10/10 real `/advisor` requests passed with model construction blocked**.
- Stale-campus, valid-campus-follow-up, unrelated-unknown, and off-topic-reset endpoint gates passed.
- Live OpenAI API calls: **0**.
- Model judge calls: **0**.
- PostgreSQL mutations: **0**.

The full suite uses local fake model responses where model-shaped behavior must be exercised. Token counts in those test logs are zero; they are not network API calls.

## Files

- `factual_orchestration.py` — current-turn understanding, FAST/NORMAL/DEEP selection, compatibility verification, and pipeline trace.
- `ai_advisor.py` — capability fast path, release-time verification gate, subject reset, and orchestration metadata.
- `test_english_factual_orchestration.py` — database identity, endpoint, lane, and stale-state certification.
- `FOUNDER_ENGLISH_ACCEPTANCE_PACK.md` — 75 manual browser questions across single turns and eight multi-turn conversations.
- `english_factual_orchestration/full_python_tests.txt` — complete Python validation log.
- `english_factual_orchestration/browser_state_tests.txt` — browser-state validation log.
- `AGENTS.md` — standing owner instruction to use GPT-5.6 Sol with Medium reasoning for Asteris Work tasks.

## Remaining gate

The founder should use the real `/app` interface for 30–60 minutes with `FOUNDER_ENGLISH_ACCEPTANCE_PACK.md`, plus spontaneous English questions. Mark each item PASS, FAIL, or UNCERTAIN and copy every failed answer verbatim.

Any confident wrong answer rejects this phase and returns it to engineering. Automated pass counts do not override that result. UI/personality work should begin only after founder acceptance.
