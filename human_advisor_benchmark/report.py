"""Aggregate auditable scores. Unknown and missing evaluations never count as passes."""
from __future__ import annotations
import argparse,csv,json,statistics
from collections import Counter,defaultdict
from pathlib import Path
from .runner import ROOT,HOME,save,digest
from .judge import DIMENSIONS

def rate(n,d):
    return round(100*n/d,2) if d else None

def csv_write(path,rows,fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]) if rows else fields or ["no_rows"])
        w.writeheader(); w.writerows(rows)

def compatible(a,b):
    keys=("corpus_sha256","database_sha256","production_hashes","history_window")
    return all(a.get(k)==b.get(k) for k in keys)

def aggregate(run):
    corpus=json.loads((HOME/"corpus.json").read_text(encoding="utf-8"))
    manifest=json.loads((run/"manifest.json").read_text(encoding="utf-8"))
    if manifest["corpus_sha256"]!=digest(corpus): raise ValueError("Corpus changed; use frozen corpus matching manifest")
    transcripts={p.stem:json.loads(p.read_text(encoding="utf-8")) for p in (run/"transcripts").glob("*.json")}
    judgments={}; judge_errors=[]; judge_usage=Counter(); stale=[]; packet_formats=Counter(); rubric_hashes=set(); judge_models=set(); validation_policies=set(); validation_warnings=[]
    for p in sorted((run/"judgments").glob("*.json")):
        if ".input." in p.name: continue
        j=json.loads(p.read_text(encoding="utf-8"))
        if j.get("error"): judge_errors.append({"file":p.name,"error":j["error"]}); continue
        if not j.get("evaluation"): continue
        transcript=transcripts.get(j["scenario_id"])
        if not transcript: continue
        if j.get("transcript_sha256") and j["transcript_sha256"]!=digest(transcript):
            stale.append(p.name); continue
        # Original pre-resume judgments did not carry transcript hashes. Compare raw stored inputs.
        inp=p.with_suffix(".input.json")
        if inp.exists():
            saved_input=json.loads(inp.read_text(encoding="utf-8"))
            if any(o["response"]!=transcript["turns"][o["turn"]-1]["response"] for o in saved_input["observations"]):
                stale.append(p.name); continue
        packet_formats[j.get("packet_format","full_evidence_v1")]+=1
        rubric_hashes.add(j.get("rubric_sha256")); judge_models.add(j.get("judge_model"))
        validation_policies.add(j.get("validation_policy","strict_label_retry_v1"))
        validation_warnings.extend({"scenario_id":j["scenario_id"],**w} for w in j.get("validation_warnings",[]))
        for k in ("input_tokens","output_tokens","total_tokens"): judge_usage[k]+=j.get("usage",{}).get(k,0)
        for t in j["evaluation"]["turns"]:
            key=(j["scenario_id"],t["turn"])
            if key in judgments: raise ValueError("Duplicate current judgment "+str(key))
            judgments[key]=t
    rows=[]; scenario_rows=[]; failures={}; assertion_rows=[]; errors=[]; all_model_usage=Counter(); model_names=Counter()
    seen_judgments=set()
    for s in corpus["scenarios"]:
        d=transcripts.get(s["id"],{"turns":[],"status":"not_run"})
        clean=True; scenario_rows_here=[]
        for i,expected in enumerate(s["turns"],1):
            key=(s["id"],i)
            actual=d["turns"][i-1] if len(d["turns"])>=i else None
            status=actual["http_status"] if actual else None
            if actual and status!=200: clean=False
            j=judgments.get(key) if status==200 and clean else None
            if j: seen_judgments.add(key)
            scores=j["scores"] if j else {k:None for k in DIMENSIONS}
            checks=actual.get("assertions",[]) if actual and status==200 else []
            failed_checks=[c for c in checks if not c["pass"]]
            has_issue=bool(j and j["primary_issue"])
            # Adequate-or-better rubric bar, with academic critical cases separately gated.
            score_fail=any(v is not None and v<3 for v in scores.values())
            evaluated=bool(j)
            result=("error" if actual and status!=200 else "not_run" if not actual else
                    "post_error_diagnostic" if not clean else "fail" if failed_checks or score_fail or has_issue else
                    "pass" if evaluated else "unscored")
            row={"scenario_id":s["id"],"category":s["category"],"turn":i,"http_status":status,
                 "clean_prefix":bool(actual and clean and status==200),"result":result,
                 "assertions":len(checks),"failed_assertions":len(failed_checks),"rubric_evaluated":evaluated,
                 "response_words":len(actual["response"].get("answer","").split()) if actual else None,
                 "elapsed_seconds":actual.get("elapsed_seconds") if actual else None,**scores}
            rows.append(row); scenario_rows_here.append(row)
            if not actual: continue
            for e in actual.get("events",[]):
                if e["kind"]=="model":
                    response=e["response"]; model_names[response.get("model","unknown")]+=1
                    usage=response.get("usage") or {}
                    for k in ("input_tokens","output_tokens","total_tokens"): all_model_usage[k]+=usage.get(k,0)
            if status!=200:
                error={"scenario_id":s["id"],"turn":i,"status":status,"response":actual["response"]}
                errors.append(error); continue
            for c in checks:
                assertion_rows.append({"scenario_id":s["id"],"turn":i,"clean_prefix":clean,**c})
            if not clean: continue
            issue=j["primary_issue"] if j and j["primary_issue"] else None
            if issue:
                failures[key]={"scenario_id":s["id"],"turn":i,**issue,"basis":["rubric"]}
            if failed_checks:
                if key not in failures:
                    c=failed_checks[0]
                    is_state=c["op"]=="state_in"
                    model_events=[e for e in actual["events"] if e["kind"]=="model"]
                    layer="deterministic" if is_state or c["op"]=="tools_empty" or not model_events else "unresolved"
                    pattern=("wrong_or_lost_subject" if is_state else
                             "stop_or_frustration_mishandled" if c["op"]=="tools_empty" else
                             "list_dump_or_repetition" if c["op"]=="max_words" else "source_or_evidence_gap")
                    failures[key]={"scenario_id":s["id"],"turn":i,"root_cause":c.get("root_cause","unresolved"),
                       "pattern":pattern,"layer":layer,"severity":"noncritical","confidence":"high" if is_state else "medium",
                       "evidence":"Frozen structural assertion failed: "+json.dumps(failed_checks,ensure_ascii=False),
                       "basis":["structural_assertion"]}
                else: failures[key]["basis"].append("structural_assertion")
        complete=len(d["turns"])==len(s["turns"]) and all(t["http_status"]==200 for t in d["turns"])
        fully_scored=complete and all(r["rubric_evaluated"] for r in scenario_rows_here)
        observed_failure=any(r["result"]=="fail" for r in scenario_rows_here)
        sr={"scenario_id":s["id"],"category":s["category"],"planned_turns":len(s["turns"]),
            "attempted_turns":len(d["turns"]),"completed_error_free":complete,"fully_scored":fully_scored,
            "result":"fail" if observed_failure else "pass" if fully_scored else "incomplete_or_unscored"}
        scenario_rows.append(sr)
    reviewed_path=run/"reviewed_findings.json"
    reviewed=[]
    if reviewed_path.exists():
        reviewed=json.loads(reviewed_path.read_text(encoding="utf-8"))["findings"]
        for item in reviewed:
            if item.get("historical_attempt"): continue
            key=(item["scenario_id"],item["turn"])
            matching=next((r for r in rows if (r["scenario_id"],r["turn"])==key),None)
            if not matching or not matching["clean_prefix"]: continue
            prior=failures.get(key,{})
            failures[key]={**prior,**item,"basis":list(set(prior.get("basis",[])+["task_agent_evidence_review"]))}
    metrics={}
    scored_rows=[r for r in rows if r["rubric_evaluated"]]
    for dimension,weight in DIMENSIONS.items():
        values=[r[dimension] for r in scored_rows if r[dimension] is not None]
        metrics[dimension]={"denominator":len(values),"fully_correct_or_excellent":sum(v==4 for v in values),
                           "adequate_or_better":sum(v>=3 for v in values),"failures_below_adequate":sum(v<3 for v in values),
                           "strict_rate_percent":rate(sum(v==4 for v in values),len(values)),
                           "adequate_rate_percent":rate(sum(v>=3 for v in values),len(values)),
                           "mean_0_to_4":round(statistics.mean(values),3) if values else None,"weight":weight}
    scored_dimensions=[m for m in metrics.values() if m["denominator"]]
    weighted=round(sum(m["mean_0_to_4"]/4*m["weight"] for m in scored_dimensions)/sum(m["weight"] for m in scored_dimensions)*100,2) if scored_dimensions else None
    categories=[]
    for cat in sorted({s["category"] for s in corpus["scenarios"]}):
        ss=[s for s in scenario_rows if s["category"]==cat]
        rr=[r for r in rows if r["category"]==cat]
        categories.append({"category":cat,"scenarios":len(ss),"planned_turns":len(rr),
            "attempted_turns":sum(r["http_status"] is not None for r in rr),
            "rubric_scored_turns":sum(r["rubric_evaluated"] for r in rr),
            "scenario_pass":sum(s["result"]=="pass" for s in ss),"scenario_fail":sum(s["result"]=="fail" for s in ss),
            "scenario_incomplete_or_unscored":sum(s["result"]=="incomplete_or_unscored" for s in ss)})
    patterns=defaultdict(lambda:{"turns":0,"critical":0,"examples":[]})
    for f in failures.values():
        v=patterns[f["pattern"]]; v["turns"]+=1; v["critical"]+=f["severity"]=="critical"
        if len(v["examples"])<3: v["examples"].append(f'{f["scenario_id"]}/{f["turn"]}')
    patterns=[{"pattern":k,**v} for k,v in patterns.items()]
    patterns.sort(key=lambda v:(-v["critical"],-v["turns"],v["pattern"]))
    long=[s for s in scenario_rows if s["category"]=="long_context"]
    long_eligible=[s for s in long if s["fully_scored"]]
    structural_clean=[c for c in assertion_rows if c["clean_prefix"]]
    state_checks=[c for c in structural_clean if c["op"]=="state_in"]
    export_id=digest({"transcripts":transcripts,"judgments":judgments.__repr__(),"reviewed":reviewed})[:16]
    result={"failure_export_directory":"failure_exports/"+export_id,"status":"complete" if all(s["fully_scored"] for s in scenario_rows) else "PARTIAL_NOT_A_FULL_BASELINE",
        "run_id":run.name,"manifest":manifest,
        "planned_scenarios":len(corpus["scenarios"]),"planned_turns":len(rows),
        "attempted_scenarios":len(transcripts),"error_free_completed_scenarios":sum(s["completed_error_free"] for s in scenario_rows),
        "attempted_turns":sum(r["http_status"] is not None for r in rows),
        "successful_http_turns":sum(r["http_status"]==200 for r in rows),"error_turns":len(errors),
        "clean_prefix_turns":sum(r["clean_prefix"] for r in rows),"rubric_scored_turns":len(scored_rows),
        "fully_scored_scenarios":sum(s["fully_scored"] for s in scenario_rows),
        "metrics":metrics,"overall_weighted_score_percent":weighted,
        "score_scope":"Only current successful, clean-prefix, rubric-scored turns. Never extrapolate incomplete coverage.",
        "structural_checks":{"checked":len(structural_clean),"passed":sum(c["pass"] for c in structural_clean),
           "state_checked":len(state_checks),"state_passed":sum(c["pass"] for c in state_checks),
           "state_accuracy_percent":rate(sum(c["pass"] for c in state_checks),len(state_checks))},
        "long_conversations":{"planned":len(long),"completed_error_free":sum(s["completed_error_free"] for s in long),
           "fully_scored":len(long_eligible),"passed":sum(s["result"]=="pass" for s in long_eligible),
           "success_rate_percent":rate(sum(s["result"]=="pass" for s in long_eligible),len(long_eligible))},
        "failure_turns":len(failures),"matched_coverage_failure_layers":dict(Counter(f["layer"] for key,f in failures.items() if key in seen_judgments)),
        "critical_flags_confirmed_by_task_review":sum(f["severity"]=="critical" and f.get("review_status")=="confirmed_by_task_agent" for f in failures.values()),
        "failure_layers":dict(Counter(f["layer"] for f in failures.values())),
        "critical_failure_turns":sum(f["severity"]=="critical" for f in failures.values()),
        "noncritical_failure_turns":sum(f["severity"]!="critical" for f in failures.values()),
        "root_causes":dict(Counter(f["root_cause"] for f in failures.values())),
        "top_failure_patterns":patterns[:10],"categories":categories,
        "model_calls_by_returned_model":dict(model_names),"observed_advisor_token_usage":dict(all_model_usage),
        "observed_judge_token_usage":dict(judge_usage),"judge_packet_formats":dict(packet_formats),"judge_rubric_hashes":sorted(rubric_hashes),"judge_models":sorted(judge_models),"judge_errors":judge_errors,"stale_judgments_excluded":stale,
        "reviewed_findings":reviewed,"judge_validation_policies":sorted(validation_policies),"judge_validation_warnings":validation_warnings,
        "limitations":["Purpose-built stress suite, not a random sample of users or the catalog.",
          "Rubric scores are Astra-low judgments, not a blinded human panel; investigator-reviewed anchors are labeled separately.",
          "One primary root-cause classification per failed turn; secondary causes may exist. Model-based attribution is provisional.",
          "Correctness is relative to the frozen certified database, not an independent re-certification of every BCIT source.",
          "Evaluator packets contain scoped evidence, not the whole snapshot. FLOW-03/2 demonstrates a source-coverage false positive: a critical flag was rejected against the full snapshot, while original numeric rubric scores remain unchanged. Rates are provisional evaluator estimates, not fully human-adjudicated truth rates.",
          "No confidence interval or model-superiority claim from a single stochastic run.",
          "The fixed rubric was used throughout. Early label inconsistencies triggered resubmission; later judgments preserve numeric scores and flag conflicting labels for review. This selection-policy change is recorded; formal model comparisons require identical evaluator policies.",
          "Model-free deterministic answers cannot improve merely by changing the language model.",
          "Infrastructure errors and turns after them are excluded from clean quality denominators; old attempts remain separate."]}
    failure_rate=lambda dimension: rate(metrics[dimension]["failures_below_adequate"],metrics[dimension]["denominator"])
    result["requested_metrics"]={
        "total_scenarios":len(corpus["scenarios"]),"total_turns_evaluated":len(scored_rows),
        "factual_correctness_rate":metrics["factual_correctness"]["adequate_rate_percent"],
        "strict_factual_correctness_rate":metrics["factual_correctness"]["strict_rate_percent"],
        "entity_resolution_accuracy":metrics["entity_resolution"]["adequate_rate_percent"],
        "context_retention_accuracy":metrics["context_retention"]["adequate_rate_percent"],
        "scope_accuracy":metrics["scope_accuracy"]["adequate_rate_percent"],
        "unsupported_inference_rate":failure_rate("unsupported_inference_avoidance"),
        "unnecessary_clarification_rate":failure_rate("unnecessary_clarification_avoidance"),
        "missed_necessary_clarification_rate":failure_rate("necessary_clarification_detection"),
        "repetition_list_dump_rate":failure_rate("repetition_avoidance"),
        "stop_frustration_handling_rate":metrics["frustration_handling"]["adequate_rate_percent"],
        "human_advisor_naturalness_0_to_4":metrics["naturalness"]["mean_0_to_4"],
        "long_conversation_success_rate":result["long_conversations"]["success_rate_percent"],
        "overall_weighted_score":weighted,
        "rate_definition":"Percent of applicable rubric-scored clean turns at >=3/4; adverse rates are <3/4. Strict rates require 4/4. Denominators are in metrics."}
    reviewed_keys={(x["scenario_id"],x["turn"]) for x in reviewed if not x.get("historical_attempt")}
    result["unresolved_label_warning_count"]=sum((w["scenario_id"],w["turn"]) not in reviewed_keys for w in validation_warnings)
    result["reviewed_label_warning_count"]=len(validation_warnings)-result["unresolved_label_warning_count"]
    from .reliability import summarize
    result["attempt_reliability"]=summarize(run)
    counts=run/"certified_snapshot_counts.json"
    result["certified_snapshot_counts"]=json.loads(counts.read_text(encoding="utf-8")) if counts.exists() else None
    adjudication=run/"adjudication_queue.json"
    result["adjudication_queue"]=json.loads(adjudication.read_text(encoding="utf-8")) if adjudication.exists() else []
    operational=run/"operational_findings.json"
    result["operational_findings"]=json.loads(operational.read_text(encoding="utf-8")) if operational.exists() else []
    save(run/"attempt_reliability.json",result["attempt_reliability"])
    save(run/"summary.json",result); save(ROOT/"HUMAN_ADVISOR_BENCHMARK.json",result)
    csv_write(run/"turn_scores.csv",rows)
    csv_write(run/"scenario_scores.csv",scenario_rows)
    csv_write(run/"category_scores.csv",categories)
    csv_write(run/"dimension_scores.csv",[{"dimension":k,**v} for k,v in metrics.items()])
    save(run/"structural_assertions.json",assertion_rows)
    save(run/"infrastructure_errors.json",errors)
    save(run/"failure_index.json",list(failures.values()))
    # Every classified failure includes full conversation prefix and raw response/tool/model evidence.
    for key,f in failures.items():
        d=transcripts[key[0]]
        save(run/"failure_exports"/export_id/f["root_cause"]/f'{key[0]}__{key[1]:02d}.json',
             {"classification":f,"conversation_prefix":d["turns"][:key[1]]})
    for error in errors:
        d=transcripts[error["scenario_id"]]
        save(run/"failure_exports"/export_id/"infrastructure"/f'{error["scenario_id"]}__{error["turn"]:02d}.json',
             {"classification":error,"conversation_prefix":d["turns"][:error["turn"]]})
    from .write_report import write_report
    write_report(result)
    return result

def main():
    p=argparse.ArgumentParser(); p.add_argument("--run-id",required=True); p.add_argument("--compare-with")
    args=p.parse_args(); run=HOME/"runs"/args.run_id; result=aggregate(run)
    if args.compare_with:
        other=HOME/"runs"/args.compare_with
        previous=json.loads((other/"summary.json").read_text(encoding="utf-8"))
        if result.get("judge_validation_policies")!=previous.get("judge_validation_policies") or set(result["judge_packet_formats"])!=set(previous["judge_packet_formats"]) or result["judge_rubric_hashes"]!=previous["judge_rubric_hashes"] or result["judge_models"]!=previous["judge_models"]:
            raise SystemExit("Comparison refused: evaluator rubric, model, evidence format, or validation policy differs")
        if not compatible(result["manifest"],previous["manifest"]): raise SystemExit("Comparison refused: corpus, data, code or history window differs")
        if result["status"]!="complete" or previous["status"]!="complete": raise SystemExit("Comparison refused: one run is incomplete")
        save(run/"model_comparison.json",{"against":args.compare_with,"paired_scenario_count":result["planned_scenarios"],
             "weighted_score_difference":round(result["overall_weighted_score_percent"]-previous["overall_weighted_score_percent"],2),
             "dimension_mean_differences":{k:None if result["metrics"][k]["mean_0_to_4"] is None or previous["metrics"][k]["mean_0_to_4"] is None else
                round(result["metrics"][k]["mean_0_to_4"]-previous["metrics"][k]["mean_0_to_4"],3) for k in DIMENSIONS},
             "warning":"Descriptive one-run difference; repeat paired runs and human adjudication before claiming superiority."})
    print(json.dumps({k:result[k] for k in ("status","attempted_turns","rubric_scored_turns","overall_weighted_score_percent","failure_layers","critical_failure_turns")},indent=2))
if __name__=="__main__": main()
