import unittest
from bs4 import BeautifulSoup

from bcit_program_extractor import parse_matrix, parse_program_page, parse_component_heading


class ProgramExtractorTests(unittest.TestCase):
    def test_component_heading_supports_nursing_credit_format(self):
        self.assertEqual(parse_component_heading('Required Courses: (27.0 credits)', 1), (1, 'Required Courses', '27.0'))
        self.assertEqual(parse_component_heading('2. Electives: (9.0 credits required)', 1), (2, 'Electives', '9.0'))
    def test_matrix_preserves_credit_pool_rule(self):
        soup = BeautifulSoup('''<table id="programmatrix"><tr><th class="level">2. Specialization Electives: (9.0 credits required)</th><th>Credits</th></tr><tr><td></td><td class="course_number"><a href="/courses/example-elex-8010/">ELEX 8010</a></td><td><strong class="course_name">Data Communication</strong></td><td class="credits">3.0</td></tr><tr><th class="level">Total Credits:</th><th>73.0</th></tr></table>''', 'html.parser')
        components, total = parse_matrix(soup, 'https://www.bcit.ca/programs/example-8900btech/')
        self.assertEqual(components[0].required_credits, '9.0')
        self.assertEqual(components[0].rule_type, 'MINIMUM_CREDITS_FROM_POOL')
        self.assertEqual(components[0].courses[0].role, 'ELECTIVE_POOL')
        self.assertEqual(total, '73.0')

    def test_proof_page_semantics_and_reconciliation(self):
        with open('program_extractor_audit/8900btech_source.html', encoding='utf-8') as handle:
            soup = BeautifulSoup(handle.read(), 'html.parser')
        refs, _ = parse_matrix(soup, 'https://www.bcit.ca/programs/electronics-bachelor-of-technology-part-time-8900btech/')
        ids = {c.course_id for component in refs for c in component.courses}
        audit = parse_program_page(soup, 'https://www.bcit.ca/programs/electronics-bachelor-of-technology-part-time-8900btech/', ids)
        self.assertEqual(audit.program_id, '8900BTECH')
        self.assertEqual(audit.total_credits, '73.0')
        self.assertEqual(len(audit.discovered_course_ids), 29)
        self.assertEqual(audit.missing_course_ids, [])
        self.assertTrue(audit.import_ready)
        specialized = next(c for c in audit.components if c.name == 'Specialization Electives')
        self.assertEqual(specialized.required_credits, '9.0')
        self.assertIn('ELEX8300', audit.discovered_course_ids)

    def test_evaluator_gaps_are_explicit(self):
        with open('program_extractor_audit/8900btech_source.html', encoding='utf-8') as handle:
            soup = BeautifulSoup(handle.read(), 'html.parser')
        audit = parse_program_page(soup, 'https://www.bcit.ca/programs/electronics-bachelor-of-technology-part-time-8900btech/', set())
        codes = {flag['code'] for flag in audit.review_flags}
        self.assertIn('ADMISSION_AGGREGATE_GRADE_EVALUATOR_GAP', codes)
        self.assertIn('CREDIT_POOL_COMPLETION_EVALUATOR_GAP', codes)
        self.assertIn('WORK_EXPERIENCE_COMPLETION_ONLY', codes)

    def test_project_course_none_does_not_erase_program_sequence(self):
        with open('program_extractor_audit/8900btech_source.html', encoding='utf-8') as handle:
            soup = BeautifulSoup(handle.read(), 'html.parser')
        components, _ = parse_matrix(soup, 'https://www.bcit.ca/programs/electronics-bachelor-of-technology-part-time-8900btech/')
        project = next(c for x in components for c in x.courses if c.course_id == 'ELEX8300')
        self.assertIn('No prerequisites are required', project.prerequisite_raw)
        self.assertIn('After completing the prescribed course work', next(x.raw_text for x in components if x.name == 'Industry Project'))


if __name__ == '__main__':
    unittest.main()
