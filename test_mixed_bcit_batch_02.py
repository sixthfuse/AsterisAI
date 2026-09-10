import unittest

from mixed_bcit_batch_02 import SPECS


class MixedBcitBatch02Tests(unittest.TestCase):
    def test_manifest_has_24_unique_official_candidates(self):
        self.assertEqual(24, len(SPECS))
        self.assertEqual(24, len({item["url"] for item in SPECS.values()}))
        self.assertTrue(all(item["url"].startswith("https://www.bcit.ca/programs/") for item in SPECS.values()))

    def test_manifest_is_deliberately_diverse(self):
        self.assertGreaterEqual(len({item["area"] for item in SPECS.values()}), 6)
        self.assertGreaterEqual(len({item["level"] for item in SPECS.values()}), 8)
        self.assertTrue(any("Part-time" in item["url"] or "part-time" in item["url"] for item in SPECS.values()))
        self.assertTrue(any("full-time" in item["url"] for item in SPECS.values()))
        self.assertTrue(any("co-op" in item["shape"] for item in SPECS.values()))
        self.assertTrue(any("practicum" in item["shape"] for item in SPECS.values()))

    def test_batch_wide_classification_precedes_import(self):
        self.assertEqual({"GREEN", "YELLOW"}, {item["status"] for item in SPECS.values()})
        self.assertEqual(14, sum(item["status"] == "GREEN" for item in SPECS.values()))
        self.assertEqual(10, sum(item["status"] == "YELLOW" for item in SPECS.values()))
        self.assertTrue(all("no new code" in item["custom"] for item in SPECS.values() if item["status"] == "YELLOW"))


if __name__ == "__main__":
    unittest.main()
