import copy
import unittest

from database import get_connection
from program_import_contract import (
    ProgramImportContract, Provenance, activate_revision, approve_payload,
    dry_run_diff, record_import_revision, require_approved_hash,
    rollback_revision, write_common_contract,
)


class ProgramImportHardeningTests(unittest.TestCase):
    def contract(self, program_id="8900BTECH", review="needs-human-review"):
        return ProgramImportContract(
            {"program_id":program_id,"program_name":"Electronics","credential":"Bachelor of Technology",
             "study_mode":"Part-time","school":"Energy","campus":"Burnaby","delivery_method":"Blended"},
            curriculum_components=[{"name":"Governance test","order":99,"courses":[]}],
            rules={"completion":[{"code":"AUDIT_ONLY","semantic":"raw_policy","raw":"test"}]},
            provenance=Provenance("https://www.bcit.ca/programs/electronics-bachelor-of-technology-part-time-8900btech/",
                                  review_status=review,confidence="high"))

    def test_dry_run_is_row_level_and_deterministic(self):
        contract=self.contract()
        with get_connection() as connection, connection.cursor() as cursor:
            first=dry_run_diff(cursor,contract); second=dry_run_diff(cursor,copy.deepcopy(contract))
            self.assertEqual(first,second)
            self.assertEqual(first["payload_sha256"],contract.payload_sha256)
            self.assertTrue({c["action"] for c in first["changes"]} <= {"insert","update","unchanged","delete-or-deactivate"})
            self.assertTrue(all(c["table"] and c["key"] for c in first["changes"]))

    def test_exact_hash_approval_and_changed_payload_invalidation(self):
        contract=self.contract()
        with get_connection() as connection, connection.cursor() as cursor:
            with self.assertRaisesRegex(ValueError,"exact normalized payload hash"): require_approved_hash(cursor,contract)
            approve_payload(cursor,contract,approved_by="unit-test")
            self.assertTrue(require_approved_hash(cursor,contract))
            changed=copy.deepcopy(contract); changed.program["program_name"]="Changed"
            self.assertNotEqual(changed.payload_sha256,contract.payload_sha256)
            with self.assertRaisesRegex(ValueError,"not approved"): require_approved_hash(cursor,changed)
            connection.rollback()

    def test_auto_clean_is_eligible_without_approval(self):
        with get_connection() as connection, connection.cursor() as cursor:
            self.assertTrue(require_approved_hash(cursor,self.contract(review="auto-clean")))

    def test_declarative_writer_is_idempotent(self):
        contract=self.contract(program_id="WRITERTEST",review="auto-clean")
        with get_connection() as connection, connection.cursor() as cursor:
            write_common_contract(cursor,contract); first=dry_run_diff(cursor,contract)
            write_common_contract(cursor,contract); second=dry_run_diff(cursor,contract)
            self.assertEqual(first,second)
            cursor.execute("SELECT COUNT(*) FROM curriculum_components WHERE program_id=%s AND component_name='Governance test'",("WRITERTEST",))
            self.assertEqual(cursor.fetchone()[0],1)
            connection.rollback()

    def test_activation_and_rollback_leave_append_only_audit(self):
        first=self.contract(review="auto-clean"); second=copy.deepcopy(first); second.program["program_name"]="Electronics revised"
        with get_connection() as connection, connection.cursor() as cursor:
            one=record_import_revision(cursor,first,importer="unit-test"); activate_revision(cursor,one,changed_by="unit-test")
            two=record_import_revision(cursor,second,importer="unit-test"); activate_revision(cursor,two,changed_by="unit-test")
            self.assertEqual(rollback_revision(cursor,"8900BTECH",changed_by="unit-test"),one)
            cursor.execute("SELECT revision_id FROM program_active_import_revisions WHERE program_id='8900BTECH'")
            self.assertEqual(cursor.fetchone()[0],one)
            cursor.execute("SELECT to_status FROM program_import_revision_transitions WHERE revision_id IN (%s,%s) ORDER BY transition_id",(one,two))
            states=[row[0] for row in cursor.fetchall()]
            self.assertIn("superseded",states); self.assertIn("rolled-back",states); self.assertIn("active",states)
            connection.rollback()

    def test_aliases_and_relationships_are_database_managed_and_independent(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT program_id FROM program_advisor_aliases WHERE normalized_alias='applied computing msc' AND active")
            self.assertEqual(cursor.fetchone()[0],"M600MSC")
            cursor.execute("SELECT program_id FROM program_advisor_aliases WHERE normalized_alias='regular nursing degree' AND active")
            self.assertEqual(cursor.fetchone()[0],"8875BSN")
            cursor.execute("SELECT COUNT(*),BOOL_AND(independent_program) FROM program_relationships WHERE relationship_key='specialty_nursing' AND active")
            count,independent=cursor.fetchone(); self.assertEqual(count,12); self.assertTrue(independent)
            cursor.execute("SELECT COUNT(DISTINCT program_id) FROM program_relationships WHERE relationship_key='nursing' AND active")
            self.assertEqual(cursor.fetchone()[0],13)


if __name__ == "__main__": unittest.main()
