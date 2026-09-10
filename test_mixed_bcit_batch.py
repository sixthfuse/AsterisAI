import unittest
from types import SimpleNamespace

from bs4 import BeautifulSoup

from mixed_bcit_batch import SPECS, curriculum_roles, hero_metadata, normalize_contract


class MixedBcitBatchTests(unittest.TestCase):
    def test_batch_has_twelve_unique_official_non_active_candidates(self):
        self.assertEqual(12, len(SPECS))
        self.assertEqual(12, len({item["url"] for item in SPECS.values()}))
        self.assertTrue(all(item["url"].startswith("https://www.bcit.ca/programs/") for item in SPECS.values()))
        self.assertEqual({"GREEN", "YELLOW", "RED"}, {item["status"] for item in SPECS.values()})

    def test_hero_metadata_is_read_from_official_page_structure(self):
        soup = BeautifulSoup("""<div><h1>Example</h1><p class='page-hero__meta'>
            <span>Diploma</span><span>Part-time</span><span>School of Computing</span></p></div>""", "html.parser")
        self.assertEqual(["Diploma", "Part-time", "School of Computing"], hero_metadata(soup))

    def test_connector_alternatives_are_non_required(self):
        soup = BeautifulSoup("""<table id='programmatrix'>
          <tr><th class='level'>Required Courses</th></tr>
          <tr><td class='course_number'>COMP 1000</td></tr>
          <tr><td>or</td></tr>
          <tr><td class='course_number'>COMP 1001</td></tr>
        </table>""", "html.parser")
        roles, paths = curriculum_roles(soup)
        self.assertEqual("ALTERNATIVE", roles["COMP1000"])
        self.assertEqual("ALTERNATIVE", roles["COMP1001"])
        self.assertEqual(["COMP1000", "COMP1001"], paths[0]["course_ids"])

    def test_named_pathway_courses_are_not_marked_required(self):
        soup = BeautifulSoup("""<table id='programmatrix'>
          <tr><th class='level'>Level 3</th></tr>
          <tr><td>Artificial Intelligence Option:</td></tr>
          <tr><td class='course_number'>COMP 3000</td></tr>
        </table>""", "html.parser")
        roles, _ = curriculum_roles(soup)
        self.assertEqual("PATHWAY", roles["COMP3000"])

    def test_missing_published_total_uses_component_credit_sum(self):
        audit = SimpleNamespace(
            program_id="TEST1", program_name="Test Program", total_credits="",
            components=[SimpleNamespace(required_credits="23.0"), SimpleNamespace(required_credits="15.0")],
            entrance_requirements_raw="Admission is reviewed by BCIT.", program_details_raw="",
            overview_raw="", total_credits_raw="",
        )
        soup = BeautifulSoup("""<div><h1>Test Program</h1><p class='page-hero__meta'>
            <span>Certificate</span><span>Part-time</span><span>School of Business + Media</span></p></div>""", "html.parser")
        audit.components = []
        component = {
            "name": "Required courses", "order": 1, "required_credits": "38.0", "raw_text": "",
            "rule_type": "ALL_LISTED_COURSES", "courses": [],
        }
        class Component:
            required_credits = "38.0"
            courses = []
            def __dict__(self):
                return component
        # normalize_contract serializes dataclass-like components, so exercise the fallback through a minimal dataclass.
        from dataclasses import make_dataclass
        C = make_dataclass("C", [(k, type(v)) for k, v in component.items()])
        audit.components = [C(**component)]
        contract = normalize_contract(audit, soup, set(), {
            "url": "https://www.bcit.ca/programs/test-certificate-part-time-test1/", "campus": "Online",
            "delivery": "Online", "status": "GREEN",
        })
        self.assertEqual("38.0", str(contract.program["total_credits"]))

    def test_duplicate_published_component_orders_get_unique_rule_codes(self):
        from dataclasses import make_dataclass
        component = {
            "name": "Requirement", "order": 1, "required_credits": "3.0", "raw_heading": "",
            "raw_text": "", "rule_type": "ALL_LISTED_COURSES", "courses": [],
        }
        C = make_dataclass("DuplicateOrderComponent", [(k, type(v)) for k, v in component.items()])
        audit = SimpleNamespace(
            program_id="TEST2", program_name="Test Program", total_credits="6.0",
            components=[C(**component), C(**component)], entrance_requirements_raw="Reviewed by BCIT.",
            program_details_raw="", overview_raw="",
        )
        soup = BeautifulSoup("""<div><h1>Test Program</h1><p class='page-hero__meta'>
            <span>Certificate</span><span>Part-time</span><span>School of Business + Media</span></p></div>""", "html.parser")
        contract = normalize_contract(audit, soup, set(), {
            "url": "https://www.bcit.ca/programs/test-certificate-part-time-test2/", "campus": "Online",
            "delivery": "Online", "status": "GREEN",
        })
        self.assertEqual(["COMPONENT_1", "COMPONENT_2"], [rule["code"] for rule in contract.rules["completion"]])


if __name__ == "__main__":
    unittest.main()
