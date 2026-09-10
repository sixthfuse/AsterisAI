# Human Advisor Experience benchmark - Phase 1

Canonical project: C:\Users\rdubo\Asteris. Production files and data are not modified.

## Design

The frozen English corpus contains 120 scenarios and 636 turns: 60 three-turn
conversations across 20 credential targets, 48 four-turn stress scenarios, and
12 twenty-two-turn journeys. Expectations were fixed before collecting responses.
No expectations were relaxed after observing failures.

Baseline transport is FastAPI TestClient executing canonical main.app /advisor,
with live PostgreSQL and real OpenAI calls. This is in-process ASGI HTTP, not mocked
answers and not the externally running localhost HTTP transport. The localhost app
was also checked and the existing HTTP engine regression suite passed.

Every scenario starts empty. Each request sends the last ten prior messages and
the last successfully returned TopicState, exactly matching static/app.js.
A read-only Python return-event profiler observes resolution, tools, raw model
responses and finalization. It does not replace functions or change their returns.
Actual model names and usage are recorded. Latency includes observation overhead.

## Reproduce (from the canonical project)

Baseline:
    .venv\Scripts\python.exe -B -m human_advisor_benchmark.runner --run-id baseline_20260908 --workers 6 --resume

Evaluate completed transcripts:
    .venv\Scripts\python.exe -B -m human_advisor_benchmark.judge --run-id baseline_20260908 --workers 2 --chunk-size 24 --follow

Retry unscored or failed evaluator requests:
    .venv\Scripts\python.exe -B -m human_advisor_benchmark.judge --run-id baseline_20260908 --workers 1 --chunk-size 24

Generate report, CSV scores and failure transcripts:
    .venv\Scripts\python.exe -B -m human_advisor_benchmark.report --run-id baseline_20260908

Focused tests:
    .venv\Scripts\python.exe -B -m unittest -v test_human_advisor_benchmark

Use a new run ID for an independent replication. Resume refuses changed corpus,
production hashes, model profile or database rows. It retains successful completed
scenarios and restarts interrupted/error scenarios from turn one, preserving the
earlier attempt. Model outputs remain stochastic because production does not set
a seed. API credit exhaustion stops queued work; missing outputs never pass.
Credentials load through the existing project configuration and are not saved.

## Scoring

rubric.json defines all 13 dimensions, weights, applicability and 0-4 anchors.
Null means inapplicable or unassessable, never zero or perfect.
Adequate rates use >=3/4; adverse rates use <3/4; strict rates require 4/4.
Factual 3 allows harmless imprecision only. Academically wrong or materially
misleading claims are <=1 and critical. Critical failures are a separate readiness
gate and cannot be diluted by the weighted score.

Overall score is the weighted mean of dimension means normalized to 0-100.
Every applicable denominator is reported. A scenario passes only when every turn
is completed/scored and has no recorded issue or failed assertion.
Long-scenario success is stricter than active-topic retention alone.

The Astra-low evaluator sees frozen raw database evidence, complete conversation,
expected outcomes, and observed tool/model/finalization traces. It must score each
turn with only the information available at that point, not retroactive corrections.
All judge inputs, outputs, response IDs, usage and hashes are retained.
Missing/invalid/stale judgments are rejected. Separate structural assertions test
specific contracts; correct hidden state alone cannot certify a correct answer.
Task-agent evidence reviews are labeled and do not silently alter numeric scores.

Each failed turn gets a primary root cause and a deterministic/model_language/mixed/
unresolved layer with confidence and evidence. Infrastructure failures are separate.
Repeated symptom turns are not independent bugs or population samples.
Historical interrupted-attempt findings are excluded from current counts.

## Later model comparison (prepared, not run in Phase 1)

    .venv\Scripts\python.exe -B -m human_advisor_benchmark.runner --run-id sol_medium_01 --profile sol_medium
    .venv\Scripts\python.exe -B -m human_advisor_benchmark.runner --run-id astra_light_01 --profile astra_light

The isolated comparison adapter uses the existing answer_student_question client
injection and the same request/state/history contract. It sets model and reasoning
on every API round: gpt-5.6-sol / medium versus gpt-6-astra / low. It never changes
the external production process or .env. Baseline does not use this adapter.

Evaluate both with the same rubric, then:
    .venv\Scripts\python.exe -B -m human_advisor_benchmark.report --run-id astra_light_01 --compare-with sol_medium_01

Comparison refuses incomplete runs and different corpus, data, code or history
windows. Differences are descriptive; repeat paired runs and use blinded human
review before claiming model superiority.

## Files and limitations

Project root contains HUMAN_ADVISOR_BENCHMARK.md and .json.
runs/<run-id>/ contains manifests, all public-table rows frozen before execution,
transcripts, judge inputs/results, evidence slices, CSV summaries, failure_index.json,
and versioned grouped failure exports referenced by the summary.
Older attempts and exports remain auditable and are not current results.

This is a purposeful stress suite, not a representative sample of students or
all programs. Rubric scores are model judgments, not a blinded human panel.
Correctness is fidelity to the certified snapshot, not a fresh audit of every BCIT
webpage. No model advantage is established by this single-model baseline.

Evaluator protocol is locked per run (judge model, reasoning, rubric hash and chunk size).
The remaining evaluator uses scoped catalog evidence and lossless reference encoding of
repeated data, verified by exact reconstruction. Earlier valid scores retain their original
full evidence packets. Comparison rejects different evaluator models, rubrics or evidence
formats; re-evaluate both candidate runs consistently for a formal comparison.

The attempt_reliability.json ledger retains and deduplicates recorded failures across
current and archived attempts. Clean quality scores are conditional on successful
replay, not first-attempt reliability. Application exceptions remain release concerns
and evidence-reviewed operational causes are in operational_findings.json.

Evaluator validation policy v2 retains otherwise valid numeric judgments when a
clarification label conflicts with its score, flags the conflict, and saves raw API
attempts. Missing turns, missing dimensions and invalid numeric scores still fail
validation. Earlier v1 judgments used label-based resubmission; each policy is
recorded and comparison refuses differing policy sets. The scoring rubric itself
was not changed. Review flagged labels before using pattern counts.
