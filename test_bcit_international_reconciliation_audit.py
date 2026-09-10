import json
import unittest

import bcit_international_enrichment_planner as planner
import bcit_international_reconciliation_audit as audit


class InternationalReconciliationAuditTests(unittest.TestCase):
    def test_six_blockers_are_exact_and_unique(self):
        self.assertEqual(6, len(audit.BLOCKERS))
        self.assertEqual(6, len(set(audit.BLOCKERS)))
        self.assertEqual("M600MSC", audit.BLOCKERS[-1])

    def test_url_corrections_preserve_exact_program_identity(self):
        for program_id, (old, new) in audit.URL_CHANGES.items():
            self.assertNotEqual(old, new)
            self.assertTrue(new.rstrip("/").lower().endswith("-" + program_id.lower()))
            self.assertEqual("https://www.bcit.ca", new.split("/programs/")[0])

    def test_missing_delivery_fact_is_not_deterministic(self):
        self.assertEqual(planner.UNKNOWN, planner.status_from_text(None))
        self.assertFalse(planner.status_from_text(None) != planner.UNKNOWN)

    def test_discrepancy_is_exactly_three_batch_05_insert_preconditions(self):
        report = json.loads((audit.ROOT / "BCIT_INTERNATIONAL_ENRICHMENT_BATCH_05.json").read_text(encoding="utf-8"))
        missing = {
            row["program_id"] for row in report["programs"]
            if row["before_state"]["delivery_facts"] is None and not row["before_state"]["international_rule_sets"]
        }
        self.assertEqual({"8660BENG", "8800BTECH", "8900BTECH"}, missing)

    def test_final_report_reconciles_all_programs(self):
        report = json.loads(audit.REPORT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(374, report["accepted_available"] + report["conditional_restricted"] + report["not_accepted"] + report["unknown_not_published"] + report["blocked_unresolved"])
        self.assertEqual(266, report["deterministic_status_count"])
        self.assertEqual([], report["idempotency_replay_actions"])
        self.assertTrue(report["certified"])


if __name__ == "__main__":
    unittest.main()
