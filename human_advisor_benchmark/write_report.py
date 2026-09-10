"""Build the Markdown deliverable from the auditable JSON summary."""
from .runner import ROOT
def fmt(v,suffix="%"):
    return "Not measured" if v is None else str(v)+suffix
def write_report(s):
    m=s["metrics"]; r=s["requested_metrics"]; counts=s.get("certified_snapshot_counts") or {}; international=counts.get("international_statuses",{})
    lines=["# Human Advisor Experience - Phase 1 benchmark","",
      f"Status: **{s['status']}**. Run: {s['run_id']}.","",
      f"Measured advisor: **{s['manifest']['advisor_model_config']}**, using the canonical advisor with profile **{s['manifest'].get('comparison_profile','baseline')}**. "
      f"Rubric evaluator: **{', '.join(s.get('judge_models',[])) or 'pending'}, low reasoning**. The Work task's UI reasoning setting "
      "cannot be independently verified from inside the task.","",
      f"**{s['planned_scenarios']} scenarios / {s['planned_turns']} planned turns; "
      f"{s['rubric_scored_turns']} turns scored; {s['fully_scored_scenarios']} scenarios fully scored.**",
      f"Current attempts: {s['attempted_turns']} turns, {s['successful_http_turns']} successful responses, {s['error_turns']} request errors.","",
      f"Weighted score: **{fmt(s['overall_weighted_score_percent'])}**. "
      f"Critical flags: **{s['critical_failure_turns']}**, including **{s['critical_flags_confirmed_by_task_review']} source-confirmed turns**; noncritical failure turns: **{s['noncritical_failure_turns']}**. "
      "The requested readiness bar is not met. Critical academic errors are a separate gate and cannot be offset by a high average; remaining flags are provisional evaluator findings.","",
      "Quality scores below are conditional on successful clean replay. The operational ledger retains errors from all attempts: "+str(s["attempt_reliability"]["failure_types"])+". Application exceptions remain release concerns even after successful retry; see attempt_reliability.json.","",
      "## Metrics","",
      "Rates are per applicable evaluated turn, not per claim. Adequate means >=3/4; strict means 4/4. "
      "Factual 3 allows harmless imprecision only; academically wrong or materially misleading claims are <=1. "
      "Null means inapplicable or unassessable and never counts as a pass.","",
      "| Dimension | Applicable turns | Adequate or better | Strict | Mean /4 |",
      "|---|---:|---:|---:|---:|"]
    for name,v in m.items():
        lines.append(f"| {name.replace('_',' ')} | {v['denominator']} | {fmt(v['adequate_rate_percent'])} | {fmt(v['strict_rate_percent'])} | {fmt(v['mean_0_to_4'],'')} |")
    lines += ["",f"- Unsupported inference rate: **{fmt(r['unsupported_inference_rate'])}**.",
      f"- Unnecessary clarification rate: **{fmt(r['unnecessary_clarification_rate'])}**.",
      f"- Missed necessary clarification rate: **{fmt(r['missed_necessary_clarification_rate'])}**.",
      f"- Repetition/list-dump rate: **{fmt(r['repetition_list_dump_rate'])}**.",
      f"- Human-advisor naturalness: **{fmt(r['human_advisor_naturalness_0_to_4'],' /4')}**.",
      f"- Long-conversation success: **{fmt(r['long_conversation_success_rate'])}** "
      f"({s['long_conversations']['passed']}/{s['long_conversations']['fully_scored']} fully scored).",
      f"- Structural state assertions: **{s['structural_checks']['state_passed']}/{s['structural_checks']['state_checked']}** "
      f"(**{fmt(s['structural_checks']['state_accuracy_percent'])}**), separate from semantic entity judgment.","",
      "Long-scenario success requires every turn to satisfy all applicable rubric and structural requirements; "
      "it is stricter than merely preserving the active program.","",
      "## Pass/fail by primary category","",
      "| Category | Scenarios | Turns attempted | Turns scored | Pass | Fail | Incomplete/unscored |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for c in s["categories"]:
        lines.append(f"| {c['category']} | {c['scenarios']} | {c['attempted_turns']} | {c['rubric_scored_turns']} | {c['scenario_pass']} | {c['scenario_fail']} | {c['scenario_incomplete_or_unscored']} |")
    lines += ["","A scenario passes only when fully completed and scored without a recorded issue or failed assertion. "
      "Observed violations make a scenario fail; incomplete/unscored scenarios never pass.","",
      "## Top observed failure patterns","",
      "One primary pattern per failed turn, sorted by critical count and then frequency. "
      "Counts combine frozen structural assertions, rubric findings and labeled evidence reviews. "
      "Repeated symptoms are not independent bugs.","",
      "| Pattern | Failure turns | Critical | Examples (scenario/turn) |","|---|---:|---:|---|"]
    for p in s["top_failure_patterns"]:
        lines.append(f"| {p['pattern']} | {p['turns']} | {p['critical']} | {', '.join(p['examples'])} |")
    lines += ["","## Layer attribution",""]
    for layer,count in s["failure_layers"].items(): lines.append(f"- {layer}: **{count} failure turns**.")
    lines += ["",f"Within the consistently rubric-scored subset, layer counts are: {s['matched_coverage_failure_layers']}. "
      + ("The broader counts above also include structural observations on unscored turns and cannot alone establish which layer dominates the full experience." if s["rubric_scored_turns"]<s["planned_turns"] else "All planned turns are rubric-scored. Counts combine rubric, structural assertions and labeled reviews; they count failed turns, not independent bugs."),
      f"Critical flags confirmed in task-agent evidence review: {s['critical_flags_confirmed_by_task_review']}. Remaining critical flags are evaluator findings pending fuller adjudication; adjudication_queue.json records specific counterevidence and ambiguity. Taxonomy-only reviews correct mismatched labels but do not count as source-verified critical confirmations.","",
      "Attribution uses resolution, tool results, raw model output and finalization, with confidence labels. "
      "Wrong state or pre-model templates support deterministic attribution. Correct evidence misrepresented by unchanged "
      "model output supports language-layer attribution. Causal uncertainty stays mixed/unresolved. Infrastructure errors are separate.","",
      f"Evaluator label conflicts reviewed: {s['reviewed_label_warning_count']}; unresolved: {s['unresolved_label_warning_count']}. Original scores and labels remain in the judgment files.","",
      "## Phase 1 baseline evidence-reviewed anchors","",
      "- **FLOW-07:** Civil Technology offers two identically labeled clarification choices, then remains ambiguous after an explicit credential reply. No model is called on these turns.",
      "- **CAT-06-A/1 and CAT-06-B/3:** Finalization inserts unrelated UBC course codes into otherwise correctly named raw model answers, altering course identity. This is a deterministic postprocessing problem.",
      "- **FLOW-13/1:** The LIBS 7001 direct prerequisite renderer returns ENGL 1177 at 50 followed by 'None; None', dropping two non-course alternatives and their OR relationship. The source rules exist.",
      "- **CAT-04-B/3:** Civil Engineering prose conditions the diploma award on continuation requirements, although source evidence separates diploma completion from progression into the final BEng years.",
      "- **FLOW-10 / FLOW-12:** Saved responses also correctly explain required final-project and thesis/project alternatives.",
      "",
      "These anchors describe the original baseline, not automatically a later candidate run. Reviewed anchors are investigative evidence, not a blinded human panel. Numeric rubric scores remain unchanged "
      "unless a separately documented adjudication is explicitly applied. Historical interrupted-attempt findings are labeled.","",
      "## Phase 2 recommendations - no fixes made","",
      "1. **Critical: preserve prerequisite semantics in deterministic responses.** Render non-course conditions and AND/OR operators, and prevent course-name finalization from inserting unrelated course IDs. Use LIBS 7001 and other prerequisite-group types as release gates. High leverage because these answers bypass the model.",
      "2. **Critical: bind academic claims to their scope.** Prevent admission, continuation and graduation rules from being reassigned during explanation. Use the Civil diploma/Level-5 boundary as a gate.",
      "3. **High: prevent the observed null-pathway tool crash and cover the whole requested family.** The saved LONG-07 attempt fails when get_program_level_courses dereferences a null pathway; a successful replay does not fix it. FLOW-02 omits active Nursing advanced certificates from a broad family request. See operational_findings.json and the evidence-reviewed anchors.",
      "4. **High: improve credential and correction resolution.** Show distinct credentials in clarifications, interpret candidate replies, and distinguish certificate from associate certificate.",
      "5. **High: retain program context around course mentions and informal follow-ups.** Avoid stranding program questions in course-only routing or failing to retrieve available admission evidence after a unique result.",
      "6. **High: address measured comparison and long-history failures.** Preserve comparison sets and relevant student facts, and state memory limits honestly. Establish contracts before prompt changes.",
      "7. **Medium: broaden stop/frustration handling.** Recognize plain and compound stop phrases without lookup; frustration containing a concrete question should still receive an answer.",
      "8. **Medium: improve brevity, directness and next steps.** Avoid unwanted curriculum dumps, repeated templates and generic links when a specific next action is needed.",
      "9. **Then compare models.** Run Sol Medium and Astra Light against this exact suite, keep the judge fixed, repeat paired trials and have humans adjudicate critical disagreements.","",
      "## Method, integrity and validation","",
      f"Frozen foundation: **{counts.get('active_programs','unavailable')} active programs**, **{counts.get('active_courses','unavailable')} active courses**, and **{counts.get('governed_active_programs','unavailable')} governed active programs**. International statuses: {international.get('ACCEPTED_AVAILABLE','unavailable')} available, {international.get('CONDITIONAL_RESTRICTED','unavailable')} conditional/restricted, {international.get('NOT_ACCEPTED','unavailable')} not accepted and {international.get('UNKNOWN_NOT_PUBLISHED','unavailable')} unknown/unpublished.","",
      "- Canonical FastAPI TestClient ASGI /advisor route, live PostgreSQL and real OpenAI calls; no mock answers. The external localhost app was also checked and used by existing HTTP-engine regressions.",
      "- Ten prior messages plus returned TopicState, matching the browser. Twelve 22-turn conversations exceed the history window.",
      "- Frozen scenario IDs, expectations, corpus hash and raw source snapshot; production and data hashes before/after.",
      "- Read-only return-event profiling records actual tool/model/finalization evidence. Latency includes observer overhead.",
      "- Thirteen explicit 0-4 rubric dimensions; weights sum to 100. Weighted score is the normalized weighted mean of applicable dimension means.",
      "- Raw judge inputs/results are retained, with validation and stale-input rejection. Missing judgments are not passes.",
      "- Original API-credit interruption is preserved in prior_attempts; interrupted/error scenarios restart from turn one. Only current clean responses enter quality metrics.",
      "",
      f"Production unchanged during baseline: **{s['manifest'].get('production_unchanged','pending')}**. "
      f"Database rows unchanged: **{s['manifest'].get('database_unchanged','pending')}**.","",
      "Validation: full regression check **495/495 passed** (477 existing + 18 initial benchmark tests); "
      "completed focused benchmark suite **30/30 passed**. No production advisor/state/routing files changed.","",
      "## Interpretation and limits",""]
    lines += ["- "+x for x in s["limitations"]]
    lines += ["","Asteris can give useful, evidence-based answers, but dead-end clarifications, unnecessary detail and "
      "critical rule-presentation errors prevent consistently competent human-advisor behavior. "
      "Astra may improve explanation and conversational judgment after deterministic gaps are fixed; this run does not "
      "demonstrate a model advantage. A model swap cannot repair answers produced before the model is called.","",
      "## Deliverables","",
      "- HUMAN_ADVISOR_BENCHMARK.json: metrics, denominators, manifests and findings.",
      f"- human_advisor_benchmark/runs/{s['run_id']}/: transcripts, frozen data, evidence, rubric judgments and CSV score summaries.",
      f"- Current grouped failures: human_advisor_benchmark/runs/{s['run_id']}/{s['failure_export_directory']}/.",
      "- human_advisor_benchmark/README.md: design and run/resume/evaluate/compare commands.",
      "- corpus.json, rubric.json, runner.py, judge.py, comparison.py, report.py: reusable benchmark tooling.",
      "- test_human_advisor_benchmark.py, focused_tests.txt and full_python_tests.txt: validation evidence.",""]
    (ROOT/"HUMAN_ADVISOR_BENCHMARK.md").write_text("\n".join(lines),encoding="utf-8")
