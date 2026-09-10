# Advisor v3 architecture reset

## Boundary

`/advisor-v3` and `/app-v3` are an isolated experiment. Production `/advisor` and `/app`, PostgreSQL contents, schema, migrations, and curated academic rules are not changed. v3 performs read-only retrieval and keeps conversation state in a bounded process-local session store or an explicitly returned client state.

## Discarded v2 pieces

- The v2 turn orchestrator and its ordered keyword branches are discarded. Its branch order allowed a stale program or a surface phrase such as `sure` to pre-empt the student's current task.
- The v2 interpretation compatibility fields and fallback intent tree are discarded as execution authority. Several overlapping intent/scope fields could disagree, making the actual route depend on local precedence rules.
- Prose-derived state transition is discarded. v3 state is changed only from the validated plan, resolved referent, executed operations, and evidence.
- Candidate lists without durable identity and offer text without an explicit machine-readable action are discarded. Both caused exhaustive follow-ups and assent to lose their source set.
- Special answer handlers that bypass a shared compiler/executor are discarded. Every v3 turn uses the same classify → plan → resolve → compile → execute → synthesize → ground → transition pipeline.

## Retained trustworthy primitives

- PostgreSQL program, area-of-study, delivery, campus, course, and academic-rule records remain authoritative because they are the curated source data and are retrieved read-only.
- The small read-only repository capabilities in `AdvisorV2Repository` are retained behind a v3 adapter: taxonomy area listing, bounded family search, exact/fuzzy program resolution, program facts, campus directory, international delivery facts, and admission-rule retrieval/evaluation. They are data primitives, not the v2 orchestrator.
- `StudentProfileV2` and the deterministic admission evaluator are retained as the academic decision boundary. v3 supplies explicit, provenance-tracked assertions; Sol never determines eligibility.
- GPT-5.6 Sol with Medium reasoning is retained only at two bounded language boundaries: a strict semantic plan and optional prose synthesis from verified evidence. Deterministic planning and prose fallbacks keep the route testable and available without a model call.

## v3 invariant

The current utterance outranks memory. Exact ID, exact name, ordinal/current result-set, and active-entity resolution run before fuzzy global search. Assent can only execute the immediately preceding typed offer. Social turns preserve academic context. Explicit broad domain or credential requests start a new task thread. Exhaustive output is produced only when requested directly or when the student accepts an explicit exhaustive-list offer.
