import unittest

from mixed_bcit_batch_06 import load_specs


class MixedBcitBatch06Tests(unittest.TestCase):
    def setUp(self):
        self.discovery, self.specs = load_specs()

    def test_manifest_has_65_unique_official_candidates(self):
        self.assertEqual(65, len(self.specs))
        self.assertEqual(65, len({item["url"] for item in self.specs.values()}))
        self.assertTrue(all(item["url"].startswith("https://www.bcit.ca/programs/") for item in self.specs.values()))

    def test_manifest_matches_final_remaining_school_set_and_excludes_apprenticeships(self):
        schools = {row["school"] for row in self.discovery["selected"] if row["school"]}
        self.assertEqual({
            "School of Business + Media",
            "School of Construction and the Environment",
            "School of Health Sciences",
        }, schools)
        self.assertFalse(any(program_id.endswith("APPR") for program_id in self.specs))

    def test_refresh_classifies_every_selected_candidate(self):
        statuses = [item["status"] for item in self.specs.values()]
        self.assertEqual(65, statuses.count("GREEN") + statuses.count("YELLOW") + statuses.count("RED"))


if __name__ == "__main__":
    unittest.main()
