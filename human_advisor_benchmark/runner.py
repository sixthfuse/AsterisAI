"""Run the unchanged canonical ASGI /advisor with live DB and real model calls.
Observation uses a Python profiler: no patched tools, generated answers, or routes.
Each scenario starts fresh, then reproduces static/app.js's ten-message window.
"""
from __future__ import annotations
import argparse, contextvars, concurrent.futures, hashlib, json, os, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "human_advisor_benchmark"
EVENTS = contextvars.ContextVar("benchmark_events", default=None)

def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)

def digest(value):
    return hashlib.sha256(packed(value).encode()).hexdigest()

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for attempt in range(12):
        try:
            tmp.replace(path)
            break
        except PermissionError:
            if attempt==11: raise
            time.sleep(min(1.0,0.05*2**attempt))

def hashes():
    paths = list(ROOT.glob("*.py")) + list(ROOT.glob("*.sql")) + list((ROOT/"static").glob("*"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file() and p.name != "test_human_advisor_benchmark.py"}

def profile(frame, event, arg):
    events = EVENTS.get()
    if events is None or event != "return":
        return
    name = frame.f_code.co_name
    filename = frame.f_code.co_filename.replace("\\", "/")
    if filename.endswith("/ai_advisor.py"):
        if name == "execute_tool":
            events.append({"kind":"tool", "name":frame.f_locals.get("name"),
                           "arguments":frame.f_locals.get("arguments"),
                           "context":json.loads(packed(frame.f_locals.get("context"))),
                           "result":json.loads(packed(arg))})
        elif name == "resolve_academic_context":
            events.append({"kind":"resolution", "result":json.loads(packed(arg))})
        elif name == "finalize_student_answer":
            events.append({"kind":"finalization", "raw_answer":frame.f_locals.get("answer"),
                           "final_answer":arg})
    elif name == "create" and filename.endswith("/resources/responses/responses.py") and hasattr(arg, "model_dump"):
        fields = ("model", "instructions", "input", "reasoning", "tool_choice", "previous_response_id")
        request = {k: json.loads(packed(frame.f_locals[k])) for k in fields if k in frame.f_locals}
        events.append({"kind":"model", "request":request, "response":arg.model_dump(mode="json")})

def snapshot():
    from database import get_connection
    with get_connection() as c:
        c.execute("SET TRANSACTION READ ONLY")
        names = [r[0] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")]
        from psycopg import sql
        tables = {}
        for name in names:
            rows = c.execute(sql.SQL("SELECT row_to_json(t) FROM {} t").format(sql.Identifier(name))).fetchall()
            tables[name] = sorted((r[0] for r in rows), key=packed)
    return tables

def validate(corpus):
    seen=set()
    for scenario in corpus["scenarios"]:
        sid=scenario["id"]
        if sid in seen:
            raise ValueError("duplicate scenario ID: "+sid)
        seen.add(sid)
        if not 2 <= len(scenario["turns"]) <= 30:
            raise ValueError("scenario must have 2-30 turns")
        for i,t in enumerate(scenario["turns"]):
            if not t.get("question") or not t.get("expected"):
                raise ValueError(f"{sid}/{i}: missing question/expectation")
            if t["clarification"] not in ("required","unnecessary","allowed"):
                raise ValueError("invalid clarification expectation")
            if not t.get("scope"):
                raise ValueError("missing academic scope")
            for check in t.get("checks",[]):
                if check["op"] not in ("state_in","contains_all","contains_any","excludes","max_words","tools_empty"):
                    raise ValueError("unknown check operator")
    return True

def check_turn(turn, response):
    import re
    answer=response.get("answer","")
    outcomes=[]
    for check in turn.get("checks",[]):
        op=check["op"]; want=check.get("value")
        if op=="state_in":
            actual=response.get("conversation_state",{}).get(check["field"])
            ok=actual in want
        elif op=="contains_all":
            actual=answer; ok=all(re.search(s,answer,re.I) for s in want)
        elif op=="contains_any":
            actual=answer; ok=any(re.search(s,answer,re.I) for s in want)
        elif op=="excludes":
            actual=answer; ok=not any(re.search(s,answer,re.I) for s in want)
        elif op=="max_words":
            actual=len(answer.split()); ok=actual<=want
        else:
            actual=response.get("tools_used",[]); ok=not actual
        outcomes.append({**check,"pass":bool(ok),"actual":actual if op in ("state_in","max_words","tools_empty") else None})
    return outcomes

def make_payload(question, history, state):
    return {"question":question,"conversation":history[-10:],"conversation_state":state}

def run_scenario(scenario, out, abort=None, app_override=None):
    from fastapi.testclient import TestClient
    from main import app
    if app_override is not None: app=app_override
    if abort is not None and abort.is_set(): return scenario["id"]
    path=out/"transcripts"/(scenario["id"]+".json")
    if path.exists():
        old=json.loads(path.read_text(encoding="utf-8"))
        stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        save(out/"prior_attempts"/scenario["id"]/(stamp+".json"),old)
    history=[]; state=None; turns=[]
    with TestClient(app, raise_server_exceptions=True) as client:
        for index,turn in enumerate(scenario["turns"],1):
            if abort is not None and abort.is_set(): break
            payload=make_payload(turn["question"],history,state)
            events=[]; token=EVENTS.set(events); start=time.monotonic()
            try:
                response=client.post("/advisor",json=payload)
                status=response.status_code
                try: data=response.json()
                except Exception: data={"error":"non_json_response","body":response.text[:3000]}
            except Exception as e:
                # TestClient exposes the exception that canonical HTTP would turn into a 500.
                status=500; data={"error":type(e).__name__,"detail":str(e)[:1000]}
                if "credit_balance_exhausted" in str(e) or "insufficient_quota" in str(e):
                    data["blocker"]="api_credits_exhausted"
                    if abort is not None: abort.set()
            finally:
                EVENTS.reset(token)
            record={"turn":index,"request":payload,"expectation":turn,"http_status":status,
                    "response":data,"elapsed_seconds":round(time.monotonic()-start,3),
                    "events":events,"assertions":check_turn(turn,data) if status==200 else [],
                    "omitted_history_messages":max(0,len(history)-10)}
            turns.append(record)
            # Browser adds current user before the request; only successful answers update state.
            history.append({"role":"user","content":turn["question"]})
            if status==200 and isinstance(data.get("answer"),str):
                history.append({"role":"assistant","content":data["answer"]})
                state=data.get("conversation_state",state)
            save(path,{"id":scenario["id"],"category":scenario["category"],"tags":scenario["tags"],
                       "status":"running","turns":turns})
    complete=len(turns)==len(scenario["turns"]) and all(t["http_status"]==200 for t in turns)
    save(path,{"id":scenario["id"],"category":scenario["category"],"tags":scenario["tags"],
               "status":"complete" if complete else "interrupted_or_error","turns":turns})
    print(f'{scenario["id"]}: {len(turns)} turns; {sum(t["http_status"]!=200 for t in turns)} transport errors',flush=True)
    return scenario["id"]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", choices=["baseline","sol_medium","astra_light"], default="baseline")
    parser.add_argument("--workers",type=int,default=6)
    parser.add_argument("--ids",nargs="*")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--model", help="Isolated process only; absent preserves production default.")
    args=parser.parse_args()
    from .comparison import PROFILES
    config=PROFILES[args.profile]
    if args.model and args.profile!="baseline": raise SystemExit("Use either --model or a named --profile")
    if config["model"]: args.model=config["model"]
    if args.model:
        os.environ["ASTERIS_AI_MODEL"]=args.model
    os.chdir(ROOT)
    corpus=json.loads((HOME/"corpus.json").read_text(encoding="utf-8")); validate(corpus)
    selected=[s for s in corpus["scenarios"] if not args.ids or s["id"] in args.ids]
    out=HOME/"runs"/args.run_id
    if out.exists() and not args.resume:
        raise SystemExit("Run already exists; choose a new ID or use --resume")
    out.mkdir(parents=True,exist_ok=True)
    import ai_advisor
    from .comparison import make_app
    app_override=make_app(args.profile) if args.profile!="baseline" else None
    fingerprint=hashes()
    if (out/"manifest.json").exists():
        old=json.loads((out/"manifest.json").read_text())
        if old["corpus_sha256"]!=digest(corpus) or old["production_hashes"]!=fingerprint or old["advisor_model_config"]!=ai_advisor.MODEL or old.get("comparison_profile","baseline")!=args.profile:
            raise SystemExit("Resume refused: corpus, production, or model changed")
        before=json.loads((out/"database_before.json").read_text(encoding="utf-8"))
        if digest(snapshot())!=digest(before):
            raise SystemExit("Resume refused: database changed")
        manifest=old
        manifest.pop("finished_at",None)
        manifest["status"]="running"
        save(out/"manifest.json",manifest)
    else:
        before=snapshot(); save(out/"database_before.json",before)
        manifest={"started_at":datetime.now(timezone.utc).isoformat(),"canonical_root":str(ROOT),
                  "transport":"canonical FastAPI TestClient /advisor; live PostgreSQL and real OpenAI; no mocks",
                  "history_window":10,"observer":"read-only Python return-event profiler",
                  "advisor_model_config":ai_advisor.MODEL,"advisor_reasoning":config["reasoning_effort"] or "production API default (unspecified)",
                  "comparison_profile":args.profile,"configuration_adapter":config["adapter"],
                  "requested_work_model":(
                      "GPT-5.6 Sol Medium" if args.profile == "sol_medium"
                      else "GPT-6 Astra Light" if args.profile == "astra_light"
                      else "production default"
                  ),
                  "judge_configuration":None,
                  "corpus_sha256":digest(corpus),"production_hashes":fingerprint,
                  "database_sha256":digest(before),"scenario_ids":[s["id"] for s in selected]}
        save(out/"manifest.json",manifest)
    pending=[]
    for s in selected:
        p=out/"transcripts"/(s["id"]+".json")
        # Re-run an interrupted scenario from turn one; never resume with invented state.
        if args.resume and p.exists():
            prior=json.loads(p.read_text(encoding="utf-8"))
            if prior.get("status")=="complete" and all(t["http_status"]==200 for t in prior["turns"]):
                continue
        pending.append(s)
    abort=threading.Event()
    threading.setprofile(profile); sys.setprofile(profile)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(run_scenario,s,out,abort,app_override) for s in pending]
            for f in concurrent.futures.as_completed(futures): f.result()
    finally:
        threading.setprofile(None); sys.setprofile(None)
        after=snapshot()
        manifest.update({"finished_at":datetime.now(timezone.utc).isoformat(),
                         "status":"blocked_api_credits" if abort.is_set() else "finished",
                         "production_unchanged":fingerprint==hashes(),
                         "database_unchanged":digest(before)==digest(after),
                         "database_after_sha256":digest(after)})
        save(out/"manifest.json",manifest)
    if not manifest["production_unchanged"] or not manifest["database_unchanged"]:
        raise SystemExit("Baseline contaminated by production/database drift")

if __name__=="__main__":
    main()
