"""Retain request failures across retries; clean quality is not first-attempt reliability."""
import json
from collections import Counter
from .runner import digest

def summarize_records(records):
    seen=set(); errors=[]; attempted=0
    for source,record in records:
        for turn in record.get("turns",[]):
            identity=digest({"scenario":record["id"],"turn":turn})
            if identity in seen: continue
            seen.add(identity); attempted+=1
            if turn["http_status"]==200: continue
            response=turn.get("response",{})
            detail=json.dumps(response)
            kind=("api_credits" if "credit_balance_exhausted" in detail or "insufficient_quota" in detail or response.get("blocker")=="api_credits_exhausted"
                  else "application_exception" if response.get("error") in ("AttributeError","TypeError","KeyError","ValueError")
                  else "other_request_failure")
            errors.append({"scenario_id":record["id"],"turn":turn["turn"],"kind":kind,"response":response,"transcript":source})
    return {"unique_recorded_attempted_turns":attempted,"request_failures":len(errors),
            "failure_types":dict(Counter(e["kind"] for e in errors)),"errors":errors,
            "interpretation":"Includes current and archived attempts, deduplicated identical turn records. Retries were selected after errors, so this is an operational ledger, not an unbiased reliability estimate. Clean quality scores are conditional on successful replay; application exceptions remain release concerns."}

def summarize(run):
    paths=list((run/"transcripts").glob("*.json"))+list((run/"prior_attempts").glob("*/*.json"))
    return summarize_records((str(p.relative_to(run)),json.loads(p.read_text(encoding="utf-8"))) for p in paths)
