"""Meaningful tests for the isolated benchmark, with no model/database dependency."""
import copy, json, sys, unittest
from pathlib import Path
from human_advisor_benchmark.runner import HOME, EVENTS, check_turn, make_payload, profile, validate, digest
from human_advisor_benchmark.judge import DIMENSIONS, validate_judgment, trace_for_judge

class BenchmarkToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=json.loads((HOME/"corpus.json").read_text(encoding="utf-8"))

    def test_corpus_unique_ids_and_expectations(self):
        self.assertTrue(validate(self.corpus))
        self.assertEqual(len(self.corpus["scenarios"]),120)
        self.assertEqual(sum(len(s["turns"]) for s in self.corpus["scenarios"]),636)

    def test_duplicate_ids_rejected(self):
        bad=copy.deepcopy(self.corpus)
        bad["scenarios"].append(bad["scenarios"][0])
        with self.assertRaises(ValueError): validate(bad)

    def test_invalid_check_rejected(self):
        bad=copy.deepcopy(self.corpus)
        bad["scenarios"][0]["turns"][0]["checks"][0]["op"]="always_pass"
        with self.assertRaises(ValueError): validate(bad)

    def test_ambiguous_expectation_is_explicit(self):
        bad=copy.deepcopy(self.corpus)
        bad["scenarios"][0]["turns"][0]["clarification"]="maybe"
        with self.assertRaises(ValueError): validate(bad)

    def test_history_window_excludes_current_user_and_keeps_state(self):
        history=[{"role":"user" if i%2==0 else "assistant","content":str(i)} for i in range(26)]
        state={"scope":"program","program_id":"M600MSC"}
        payload=make_payload("new",history,state)
        self.assertEqual(payload["conversation"],history[-10:])
        self.assertEqual(payload["conversation"][-1]["content"],"25")
        self.assertEqual(payload["conversation_state"],state)
        self.assertEqual(len(history),26)

    def test_fresh_scenario_has_no_inherited_state(self):
        self.assertEqual(make_payload("new",[],None),{"question":"new","conversation":[],"conversation_state":None})

    def test_state_pass_does_not_validate_answer(self):
        turn={"checks":[{"op":"state_in","field":"program_id","value":["M600MSC"]},
                         {"op":"contains_any","value":["Applied Computing"]}]}
        checks=check_turn(turn,{"conversation_state":{"program_id":"M600MSC"},"answer":"Nursing."})
        self.assertTrue(checks[0]["pass"])
        self.assertFalse(checks[1]["pass"])

    def test_missing_response_state_fails_check(self):
        t={"checks":[{"op":"state_in","field":"program_id","value":["M600MSC"]}]}
        self.assertFalse(check_turn(t,{"answer":"hello"})[0]["pass"])

    def test_no_claim_keyword_cannot_fake_fact_pass(self):
        t={"checks":[{"op":"contains_any","value":["374"]}]}
        self.assertFalse(check_turn(t,{"answer":"I do not know"})[0]["pass"])

    def test_stop_assertion_checks_tools_and_length(self):
        t={"checks":[{"op":"tools_empty"},{"op":"max_words","value":10}]}
        self.assertTrue(all(c["pass"] for c in check_turn(t,{"answer":"Okay, we can stop here.","tools_used":[]})))
        self.assertFalse(check_turn(t,{"answer":"Okay.","tools_used":["get_program_details"]})[0]["pass"])

    def test_long_corpus_crosses_real_client_window(self):
        long=[s for s in self.corpus["scenarios"] if s["category"]=="long_context"]
        self.assertEqual(len(long),12)
        self.assertTrue(all(20<=len(s["turns"])<=30 for s in long))

    def test_judge_missing_turn_is_rejected(self):
        with self.assertRaises(ValueError): validate_judgment({"turns":[]},[1])

    def test_judge_missing_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_judgment({"turns":[{"turn":1,"scores":{},"primary_issue":None}]},[1])

    def test_judge_pattern_inconsistent_with_clarification_score_rejected(self):
        item={"turn":1,"scores":{k:4 for k in DIMENSIONS},
              "primary_issue":{"pattern":"unnecessary_clarification"}}
        with self.assertRaises(ValueError): validate_judgment({"turns":[item]},[1])

    def test_unscorable_scores_remain_null(self):
        item={"turn":1,"scores":{k:None for k in DIMENSIONS},"primary_issue":None}
        self.assertTrue(validate_judgment({"turns":[item]},[1]))
        self.assertTrue(all(v is None for v in item["scores"].values()))

    def test_trace_slimming_preserves_raw_output_without_request_duplication(self):
        events=[{"kind":"model","request":{"instructions":"policy","tool_choice":"required"},
                 "response":{"model":"example","output":[{"type":"message","text":"original"}]}}]
        before=copy.deepcopy(events); slim=trace_for_judge(events)
        self.assertEqual(slim[0]["output"],events[0]["response"]["output"])
        self.assertNotIn("instructions",slim[0])
        self.assertEqual(events,before)

    def test_observer_returns_original_values_and_does_not_mutate(self):
        namespace={}
        exec(compile("def resolve_academic_context():\n    return {'program_id':'TEST'}\n","/canonical/ai_advisor.py","exec"),namespace)
        events=[]; token=EVENTS.set(events); previous=sys.getprofile()
        try:
            sys.setprofile(profile); result=namespace["resolve_academic_context"]()
        finally:
            sys.setprofile(previous); EVENTS.reset(token)
        self.assertEqual(result,{"program_id":"TEST"})
        self.assertEqual(events,[{"kind":"resolution","result":{"program_id":"TEST"}}])

    def test_digest_stable_across_dictionary_order(self):
        self.assertEqual(digest({"a":1,"b":2}),digest({"b":2,"a":1}))


    def test_comparison_applies_model_and_reasoning_on_every_round(self):
        from human_advisor_benchmark.comparison import ConfiguredResponses
        class Recorder:
            def __init__(self): self.calls=[]
            def create(self,**kwargs): self.calls.append(kwargs); return kwargs
        original=Recorder(); configured=ConfiguredResponses(original,"gpt-6-astra","low")
        configured.create(model="old",input="first")
        configured.create(model="old",previous_response_id="prior",input=[])
        self.assertEqual(len(original.calls),2)
        self.assertTrue(all(c["model"]=="gpt-6-astra" and c["reasoning"]=={"effort":"low"} for c in original.calls))

    def test_model_profile_names_are_explicit(self):
        from human_advisor_benchmark.comparison import PROFILES
        self.assertEqual(PROFILES["sol_medium"]["model"],"gpt-5.6-sol")
        self.assertEqual(PROFILES["sol_medium"]["reasoning_effort"],"medium")
        self.assertIsNone(PROFILES["baseline"]["model"])

    def test_zero_denominator_is_unavailable_not_perfect(self):
        from human_advisor_benchmark.report import rate
        self.assertIsNone(rate(0,0))
        self.assertEqual(rate(0,5),0)
        self.assertEqual(rate(4,5),80)

    def test_model_comparison_refuses_changed_data_or_corpus(self):
        from human_advisor_benchmark.report import compatible
        a={"corpus_sha256":"a","database_sha256":"b","production_hashes":{"advisor":"x"},"history_window":10}
        self.assertTrue(compatible(a,dict(a,advisor_model_config="another")))
        self.assertFalse(compatible(a,dict(a,database_sha256="changed")))
        self.assertFalse(compatible(a,dict(a,history_window=100)))

    def test_quota_circuit_breaker_prevents_starting_queued_scenario(self):
        import threading
        from human_advisor_benchmark.runner import run_scenario
        event=threading.Event(); event.set()
        target=HOME/"runs"/"must_not_be_created_by_aborted_test"
        result=run_scenario(self.corpus["scenarios"][0],target,event)
        self.assertEqual(result,self.corpus["scenarios"][0]["id"])
        self.assertFalse(target.exists())


    def test_evidence_deduplication_round_trip_preserves_every_value(self):
        from human_advisor_benchmark.packets import encode_evidence,decode_evidence
        value={"rule":"A OR B; not both. "*30,"minimum":50,"unknown":None}
        payload={"source":value,"tool_result":value,"answer":["text "*80,"text "*80]}
        packet=encode_evidence(payload)
        self.assertEqual(decode_evidence(packet),payload)
        self.assertLess(len(json.dumps(packet)),len(json.dumps(payload)))

    def test_evidence_unique_values_and_false_are_not_dropped(self):
        from human_advisor_benchmark.packets import encode_evidence,decode_evidence
        payload={"facts":[False,0,None,[],{},"",{"nested":"unique"}]}
        self.assertEqual(decode_evidence(encode_evidence(payload)),payload)

    def test_atomic_save_retries_a_transient_windows_lock(self):
        from unittest.mock import MagicMock,patch
        from human_advisor_benchmark.runner import save
        target=MagicMock(); temp=MagicMock()
        target.with_suffix.return_value=temp
        temp.replace.side_effect=[PermissionError("sharing violation"),None]
        with patch("human_advisor_benchmark.runner.Path",return_value=target),patch("human_advisor_benchmark.runner.time.sleep"):
            save("test.json",{"complete":True})
        self.assertEqual(temp.replace.call_count,2)
        self.assertEqual(json.loads(temp.write_text.call_args.args[0]),{"complete":True})

    def test_atomic_save_does_not_hide_persistent_write_failure(self):
        from unittest.mock import MagicMock,patch
        from human_advisor_benchmark.runner import save
        target=MagicMock(); temp=MagicMock()
        target.with_suffix.return_value=temp
        temp.replace.side_effect=PermissionError("persistent")
        with patch("human_advisor_benchmark.runner.Path",return_value=target),patch("human_advisor_benchmark.runner.time.sleep"):
            with self.assertRaises(PermissionError): save("test.json",{"complete":True})


    def test_retry_ledger_keeps_application_failure_after_success(self):
        from human_advisor_benchmark.reliability import summarize_records
        bad={"turn":1,"http_status":500,"response":{"error":"AttributeError","detail":"missing value"}}
        good={"turn":1,"http_status":200,"response":{"answer":"ok"}}
        result=summarize_records([("old",{"id":"X","turns":[bad]}),("copy",{"id":"X","turns":[bad]}),("current",{"id":"X","turns":[good]})])
        self.assertEqual(result["unique_recorded_attempted_turns"],2)
        self.assertEqual(result["failure_types"],{"application_exception":1})
        self.assertEqual(result["errors"][0]["transcript"],"old")

    def test_retry_ledger_separates_credit_exhaustion(self):
        from human_advisor_benchmark.reliability import summarize_records
        result=summarize_records([("old",{"id":"X","turns":[{"turn":1,"http_status":500,"response":{"blocker":"api_credits_exhausted"}}]})])
        self.assertEqual(result["failure_types"],{"api_credits":1})


    def test_label_review_preserves_numeric_scores_without_paid_retry(self):
        from human_advisor_benchmark.judge import label_warnings
        item={"turn":1,"scores":{k:4 for k in DIMENSIONS},"primary_issue":{"pattern":"missed_clarification"}}
        item["scores"]["necessary_clarification_detection"]=None
        original=copy.deepcopy(item)
        self.assertTrue(validate_judgment({"turns":[item]},[1],strict_labels=False))
        warnings=label_warnings({"turns":[item]})
        self.assertEqual(len(warnings),1)
        self.assertTrue(warnings[0]["review_required"])
        self.assertEqual(item,original)

if __name__=="__main__": unittest.main()
