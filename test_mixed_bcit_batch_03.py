import unittest

from mixed_bcit_batch_03 import SPECS


class MixedBcitBatch03Tests(unittest.TestCase):
    def test_manifest_has_50_unique_official_candidates(self):
        self.assertEqual(50, len(SPECS))
        self.assertEqual(50, len({item["url"] for item in SPECS.values()}))
        self.assertTrue(all(item["url"].startswith("https://www.bcit.ca/programs/") for item in SPECS.values()))

    def test_manifest_is_diverse_and_not_apprenticeship_heavy(self):
        self.assertGreaterEqual(len({item["area"] for item in SPECS.values()}), 7)
        self.assertGreaterEqual(len({item["level"] for item in SPECS.values()}), 8)
        self.assertTrue(any("part-time" in item["url"] for item in SPECS.values()))
        self.assertTrue(any("full-time" in item["url"] for item in SPECS.values()))
        self.assertFalse(any("apprenticeship" in item["url"] for item in SPECS.values()))

    def test_classification_is_complete_before_import(self):
        self.assertEqual({"GREEN", "YELLOW"}, {item["status"] for item in SPECS.values()})
        self.assertTrue(all(item["custom"] for item in SPECS.values()))
        self.assertTrue(all("existing Batch 01" in item["custom"] for item in SPECS.values() if item["status"] == "YELLOW"))


if __name__ == "__main__":
    unittest.main()
