import copy
import json
import unittest
from pathlib import Path

from program_import_contract import ProgramImportContract, Provenance, ReviewItem, adapt_nursing_audit, adapt_shared_program_audit, record_import_revision, require_import_ready, validate_import_readiness
from database import get_connection

ROOT = Path(__file__).parent


class ProgramImportContractTests(unittest.TestCase):
    def minimal(self):
        return ProgramImportContract(
            {"program_id":"TESTCERT","program_name":"Test","credential":"Certificate","study_mode":"Part-time"},
            curriculum_components=[{"name":"Core","courses":[{"course_id":"TEST1000","reconciliation":"existing_database"}]}],
            course_references=[{"course_id":"TEST1000","reconciliation":"existing_database"}],
            provenance=Provenance("https://www.bcit.ca/programs/test-testcert/", review_status="auto-clean", confidence="high"))

    def load(self, relative): return json.loads((ROOT / relative).read_text(encoding="utf-8"))
    def test_valid_contract_is_go(self): self.assertTrue(validate_import_readiness(self.minimal()).go)
    def test_missing_metadata_stops(self):
        c=self.minimal(); c.program["credential"]=""; self.assertIn("credential", " ".join(validate_import_readiness(c).blockers))
    def test_unresolved_course_stops(self):
        c=self.minimal(); c.course_references[0]["reconciliation"]="missing_course"; self.assertFalse(validate_import_readiness(c).go)
    def test_unsupported_semantics_stops(self):
        c=self.minimal(); c.rules={"completion":[{"semantic":"nested_magic"}]}; self.assertIn("unsupported evaluator", " ".join(validate_import_readiness(c).blockers))
    def test_ambiguous_executable_rule_stops(self):
        c=self.minimal(); c.rules={"completion":[{"semantic":"choose_n","ambiguous":True}]}; self.assertFalse(validate_import_readiness(c).go)
    def test_human_confirmation_warns_but_goes(self):
        c=self.minimal(); c.unresolved_items=[ReviewItem("INTERVIEW","Interview",human_confirmation_only=True)]; r=validate_import_readiness(c); self.assertTrue(r.go); self.assertTrue(r.warnings)
    def test_open_review_item_stops(self):
        c=self.minimal(); c.unresolved_items=[ReviewItem("AMBIGUOUS","Unknown")]; self.assertFalse(validate_import_readiness(c).go)
    def test_idempotency_key_is_deterministic(self):
        a=self.minimal(); b=copy.deepcopy(a); self.assertEqual(a.idempotency_key,b.idempotency_key)
    def test_changed_payload_changes_key(self):
        a=self.minimal(); b=copy.deepcopy(a); b.program["program_name"]="Changed"; self.assertNotEqual(a.idempotency_key,b.idempotency_key)
    def test_revision_ledger_is_idempotent(self):
        c=adapt_shared_program_audit(self.load("program_extractor_audit/8900btech_program_audit.json"))
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM program_import_revisions WHERE idempotency_key=%s",(c.idempotency_key,))
            self.assertTrue(record_import_revision(cursor,c,importer="contract_test"))
            self.assertFalse(record_import_revision(cursor,c,importer="contract_test"))
            cursor.execute("SELECT COUNT(*) FROM program_import_revisions WHERE idempotency_key=%s",(c.idempotency_key,))
            self.assertEqual(cursor.fetchone()[0],1)
            connection.rollback()
    def test_governance_fields_round_trip(self):
        p=self.minimal().to_dict()["provenance"]; self.assertEqual(p["source_type"],"official_program_page"); self.assertIn("pipeline_version",p)
    def test_electronics_adapter(self):
        c=adapt_shared_program_audit(self.load("program_extractor_audit/8900btech_program_audit.json")); self.assertEqual(c.program["program_id"],"8900BTECH"); self.assertTrue(c.rules["completion"])
    def test_m600msc_adapter(self):
        c=adapt_shared_program_audit(self.load("program_extractor_audit/m600msc/m600msc_program_audit.json")); self.assertEqual(c.program["program_id"],"M600MSC"); self.assertTrue(c.rules["pathway"]); self.assertTrue(c.rules["substitution"])
    def test_specialty_nursing_adapter(self):
        c=adapt_nursing_audit(self.load("program_extractor_audit/nursing_batch/810bbsn_audit.json")); self.assertEqual(c.program["program_id"],"810BBSN"); self.assertTrue(c.course_references)
    def test_main_bsn_adapter(self):
        c=adapt_nursing_audit(self.load("program_extractor_audit/8875bsn/8875bsn_audit.json"),main_bsn=True); self.assertEqual(c.program["program_id"],"8875BSN"); self.assertTrue(c.non_course_requirements)
    def test_import_ready_audits_pass_stop_go(self):
        cases=[adapt_shared_program_audit(self.load("program_extractor_audit/8900btech_program_audit.json")),adapt_shared_program_audit(self.load("program_extractor_audit/m600msc/m600msc_program_audit.json")),adapt_nursing_audit(self.load("program_extractor_audit/8875bsn/8875bsn_audit.json"),main_bsn=True)]
        for c in cases:
            with self.subTest(c.program["program_id"]): require_import_ready(c)

    def test_specialty_audit_with_unresolved_gap_stops(self):
        c=adapt_nursing_audit(self.load("program_extractor_audit/nursing_batch/810bbsn_audit.json"))
        self.assertFalse(validate_import_readiness(c).go)


if __name__ == "__main__": unittest.main()
