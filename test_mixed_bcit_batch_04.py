import unittest

from mixed_bcit_batch_04 import load_specs


class MixedBcitBatch04Tests(unittest.TestCase):
    def setUp(self):
        self.discovery, self.specs = load_specs()

    def test_manifest_has_100_unique_official_candidates(self):
        self.assertEqual(100, len(self.specs))
        self.assertEqual(100, len({item["url"] for item in self.specs.values()}))
        self.assertTrue(all(item["url"].startswith("https://www.bcit.ca/programs/") for item in self.specs.values()))

    def test_manifest_is_cross_school_and_not_apprenticeship_filled(self):
        schools = {row["school"] for row in self.discovery["selected"] if row["school"]}
        self.assertEqual(6, len(schools))
        self.assertFalse(any(program_id.endswith("APPR") for program_id in self.specs))

    def test_natural_red_is_held_and_every_other_candidate_is_importable(self):
        statuses = [item["status"] for item in self.specs.values()]
        self.assertEqual(1, statuses.count("RED"))
        self.assertEqual(99, statuses.count("GREEN") + statuses.count("YELLOW"))


if __name__ == "__main__":
    unittest.main()
