import unittest

from bs4 import BeautifulSoup

from bcit_course_gap_enrichment import (
    course_discoveries_from_page,
    normalize_code,
    section_text,
)


class GapExtractorTests(unittest.TestCase):
    def test_normalize_code_preserves_display_space(self):
        self.assertEqual(normalize_code("elex-7010"), ("ELEX7010", "ELEX 7010"))

    def test_program_matrix_links_are_official_and_deduplicated(self):
        soup = BeautifulSoup(
            '<a href="/courses/engineering-statistics-elex-7010/">ELEX 7010</a>'
            '<a href="https://www.bcit.ca/courses/engineering-statistics-elex-7010/">ELEX 7010</a>'
            '<a href="https://example.com/courses/fake-abcd-1000/">ABCD 1000</a>',
            "html.parser",
        )
        found = course_discoveries_from_page(soup, "https://www.bcit.ca/programs/example/")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].course_id, "ELEX7010")

    def test_section_text_stops_at_next_named_heading(self):
        soup = BeautifulSoup(
            "<h2>Course Overview</h2><p>Exact overview.</p>"
            "<h3>Prerequisite(s)</h3><ul><li>No prerequisites are required.</li></ul>"
            "<h3>Credits</h3><p>3.0</p>",
            "html.parser",
        )
        self.assertEqual(
            section_text(soup, r"^Course Overview$", ("Prerequisite", "Credits")),
            "Exact overview.",
        )
        self.assertEqual(
            section_text(soup, r"^Prerequisite\(s\)$", ("Credits",)),
            "No prerequisites are required.",
        )


if __name__ == "__main__":
    unittest.main()
