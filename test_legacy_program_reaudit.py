import json
import unittest

from database import get_connection
from legacy_program_reaudit import (
    CLASSIFICATIONS,
    CONTRACT_VERSION,
    REPORT_JSON,
    active_without_revision,
    canonical_url,
    sha256_json,
    snapshot_diff,
)


class LegacyProgramReauditTests(unittest.TestCase):
    def test_canonical_url_removes_fragment_and_normalizes_case(self):
        self.assertEqual("https://www.bcit.ca/programs/example/", canonical_url("HTTPS://WWW.BCIT.CA/programs/Example/#overview"))

    def test_payload_hash_is_order_independent(self):
        self.assertEqual(sha256_json({"a": 1, "b": 2}), sha256_json({"b": 2, "a": 1}))

    def test_snapshot_diff_detects_zero_diff(self):
        self.assertEqual({"changed_tables": 0, "changes": [], "zero_diff": True}, snapshot_diff({"programs": [{"id": 1}]}, {"programs": [{"id": 1}]}))

    def test_contract_version_fits_database_column(self):
        self.assertLessEqual(len(CONTRACT_VERSION), 16)

    def test_report_has_exact_legacy_set_and_hashes(self):
        report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(19, report["programs_audited"])
        self.assertEqual(19, len(set(report["exact_program_ids"])))
        self.assertTrue(all(len(item["payload_sha256"]) == 64 for item in report["programs"]))
        self.assertTrue(all(set(item["classifications"]) <= set(CLASSIFICATIONS) for item in report["programs"]))

    def test_all_programs_are_governed_and_zero_diff(self):
        report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(19, report["successfully_governed"])
        self.assertEqual(0, report["held"])
        self.assertTrue(report["all_zero_diff"])
        self.assertTrue(report["all_replays_idempotent"])
        with get_connection() as connection, connection.cursor() as cursor:
            self.assertEqual([], active_without_revision(cursor))

    def test_certified_totals_and_international_consistency(self):
        report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(374, report["final_active_programs"])
        self.assertEqual(3976, report["final_active_courses"])
        self.assertEqual(0, report["international_mismatches"])
        self.assertEqual(0, report["new_courses_added"])


if __name__ == "__main__":
    unittest.main()
