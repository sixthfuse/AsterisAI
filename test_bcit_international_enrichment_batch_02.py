import json
import tempfile
import unittest
from pathlib import Path

import bcit_international_enrichment_batch_02 as batch


class Batch02Tests(unittest.TestCase):
    def test_approved_scope_is_exact(self):
        plan, rows, ids, entries = batch.load_approved()
        self.assertEqual(50, len(ids))
        self.assertEqual(ids, [row["program_id"] for row in rows])
        self.assertFalse(set(ids) & batch.BLOCKED)
        self.assertEqual({"INSERT": 2, "UPDATE": 48}, dict(__import__("collections").Counter(entries[pid]["action"] for pid in ids)))
        batch_01_ids = set(json.loads(batch.BATCH_01_SUMMARY.read_text(encoding="utf-8"))["approved_program_ids"])
        self.assertFalse(set(ids) & batch_01_ids)

    def test_approved_database_actions_are_schema_limited(self):
        _, _, ids, entries = batch.load_approved()
        actions = [action for pid in ids for action in entries[pid]["proposed_db_actions"]]
        self.assertEqual(99, len(actions))
        self.assertEqual({"program_delivery_facts", "academic_rule_sets"}, {action["table"] for action in actions})
        self.assertTrue(all(action["action"] in ("INSERT", "UPDATE") for action in actions))

    def test_pgwp_wording_is_eligible_to_apply(self):
        _, _, ids, entries = batch.load_approved()
        values = []
        for pid in ids:
            rule = next(action for action in entries[pid]["proposed_db_actions"] if action["table"] == "academic_rule_sets")
            values.append(json.loads(rule["values"]["notes"])["pgwp"])
        self.assertEqual(19, values.count("ELIGIBLE_TO_APPLY"))
        self.assertEqual(31, values.count("UNKNOWN_NOT_PUBLISHED"))

    def test_unittest_log_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.log"
            path.write_text("Ran 14 tests in 1.0s\n\nOK\n", encoding="utf-8")
            parsed = batch.parse_unittest(path, "focused")
        self.assertEqual((14, 14, 0, 0, "PASS"), (parsed["run"], parsed["passed"], parsed["failures"], parsed["errors"], parsed["status"]))


if __name__ == "__main__":
    unittest.main()
