"""Phase 2C model-free gates for bounded long-session memory."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_advisor import (
    _remember_verified_conclusions, _update_user_profile,
    answer_student_question, resolve_academic_context,
)
from conversation_state import AdvisorConclusion, TopicState


ROOT = Path(__file__).resolve().parent


def resolve(question, state=None, history=None):
    return resolve_academic_context(question, history or [], None, state)


class EmptyResponses:
    def create(self, **kwargs):
        return SimpleNamespace(id='done', output=[], output_text='Concise verified answer.')


CLIENT = SimpleNamespace(responses=EmptyResponses())
NEUTRAL_HISTORY = [
    {'role': 'user', 'content': f'Unrelated message {index}'}
    for index in range(14)
]


class Phase2CLongMemoryTests(unittest.TestCase):
    def test_routine_program_facts_and_switches_skip_model_calls(self):
        class FailIfCalled:
            def create(self, **kwargs):
                raise AssertionError('routine deterministic turn called the model')
        client = SimpleNamespace(responses=FailIfCalled())
        state = resolve('Tell me about Applied Computing MSc.')['conversation_state']
        credential = answer_student_question(
            'What credential does it lead to?', [], conversation_state=state, client=client,
        )
        self.assertIn('Master of Science', credential['answer'])
        switched = answer_student_question(
            'Switch to Construction Management BTech.', [],
            conversation_state=credential['conversation_state'], client=client,
        )
        self.assertEqual(switched['conversation_state']['program_id'], '8800BTECH')
        self.assertLess(len(switched['answer'].split()), 12)

    def test_return_to_first_subject_after_multiple_switches_and_truncation(self):
        state = resolve('Tell me about Applied Computing MSc.')['conversation_state']
        state = resolve('Switch to Construction Management BTech.', state)['conversation_state']
        state = resolve('Tell me about ELEX 7010.', state)['conversation_state']
        state = resolve('List all BCIT campuses.', state)['conversation_state']
        result = resolve('Go back to the first program.', state, NEUTRAL_HISTORY)
        self.assertEqual(result['program_id'], 'M600MSC')

    def test_explicit_topic_switch_overrides_historical_memory(self):
        state = resolve('Tell me about Applied Computing MSc.')['conversation_state']
        state = resolve('Tell me about Construction Management BTech.', state)['conversation_state']
        result = resolve('Start a new topic: Accounting Bachelor degree.', state, NEUTRAL_HISTORY)
        self.assertEqual(result['program_id'], '8630BACC')

    def test_comparison_set_returns_after_unrelated_subject_and_truncation(self):
        state = resolve(
            'Compare the Construction Management diploma and Bachelor of Technology.'
        )['conversation_state']
        expected = state['comparison_program_ids']
        state = resolve('Tell me about Applied Computing MSc.', state)['conversation_state']
        result = resolve('Which of those accepts international students?', state, NEUTRAL_HISTORY)
        self.assertEqual(result['comparison_program_ids'], expected)

    def test_comparison_ordinal_and_credential_references(self):
        state = resolve(
            'Compare the Construction Management diploma and Bachelor of Technology.'
        )['conversation_state']
        diploma = resolve('Go back to the diploma we discussed earlier.', state)
        self.assertEqual(diploma['program_id'], '7710DIPMA')
        state = resolve('Compare Applied Computing MSc and Construction Management BTech.')['conversation_state']
        second = resolve('Tell me about the second one.', state, NEUTRAL_HISTORY)
        self.assertEqual(second['program_id'], '8800BTECH')

    def test_user_course_grade_correction_overwrites_and_invalidates(self):
        state = TopicState(scope='program', program_id='8800BTECH')
        courses, _ = _update_user_profile(
            state, 'I passed COMM 1142 with 65%.',
            [{'course_id': 'COMM1142', 'grade': None}],
        )
        self.assertEqual(courses[0]['grade'], 65.0)
        state.conclusions = [AdvisorConclusion(
            key='admission:8800BTECH', program_id='8800BTECH',
            summary='The reported grade meets the threshold.',
            dependency_keys=['grade:COMM1142'],
        )]
        self.assertTrue(state.conclusions[0].valid)
        courses, _ = _update_user_profile(state, 'Correction: COMM 1142 was 78%.', courses)
        self.assertEqual(courses[0]['grade'], 78.0)
        self.assertFalse(state.conclusions[0].valid)

    def test_verified_missing_course_conclusion_is_recorded_and_invalidated(self):
        state = TopicState(scope='program', program_id='8800BTECH')
        _remember_verified_conclusions(state, 'What am I missing?', '8800BTECH', [{
            'missing_requirements': [
                {'course_id': 'COMM1142', 'course_name': 'Communication'},
            ],
        }])
        self.assertEqual(state.conclusions[0].source, 'asteris_derived')
        self.assertIn('COMM 1142', state.conclusions[0].summary)
        _update_user_profile(
            state, 'I passed COMM 1142 with 78%.',
            [{'course_id': 'COMM1142', 'grade': 78}],
        )
        self.assertFalse(state.conclusions[0].valid)

    def test_user_reported_facts_keep_provenance_and_corrections(self):
        state = TopicState(scope='program', program_id='M600MSC')
        _update_user_profile(state, "I'm an international applicant and I prefer online.", [])
        _update_user_profile(state, "Correction: I'm a domestic applicant.", [])
        facts = {item.key: item for item in state.student_facts}
        self.assertEqual(facts['applicant_status'].value, 'domestic')
        self.assertEqual(facts['applicant_status'].source, 'user_reported')
        self.assertEqual(facts['delivery_preference'].value, 'online')

    def test_completed_course_survives_history_truncation_with_grade(self):
        state = resolve('Tell me about Construction Management BTech.')['conversation_state']
        first = answer_student_question(
            'I passed COMM 1142 with 78%.', [], conversation_state=state, client=CLIENT,
        )
        later = answer_student_question(
            'Which program are we discussing?', [], conversation=NEUTRAL_HISTORY,
            conversation_state=first['conversation_state'], client=CLIENT,
        )
        fact = later['conversation_state']['reported_completed_courses'][0]
        self.assertEqual((fact['course_id'], fact['grade'], fact['source']),
                         ('COMM1142', 78.0, 'user_reported'))

    def test_family_program_unrelated_return_sequence(self):
        family = resolve('Show me nursing programs.')['conversation_state']
        program = resolve('Tell me about Applied Computing MSc.', family)['conversation_state']
        unrelated = resolve('Tell me about ELEX 7010.', program)['conversation_state']
        returned_family = resolve('Go back to the family we discussed.', unrelated, NEUTRAL_HISTORY)
        self.assertEqual(returned_family['conversation_state']['scope'], 'program_family')
        returned_program = resolve('Return to the previous program.', unrelated, NEUTRAL_HISTORY)
        self.assertEqual(returned_program['program_id'], 'M600MSC')

    def test_stop_preserves_context_and_later_resume(self):
        state = resolve('Tell me about Applied Computing MSc.')['conversation_state']
        stopped = answer_student_question('Stop here.', [], conversation_state=state)
        self.assertTrue(stopped['conversation_state']['stopped'])
        resumed = resolve('Actually, where is it taught?', stopped['conversation_state'], NEUTRAL_HISTORY)
        self.assertEqual(resumed['program_id'], 'M600MSC')
        self.assertFalse(resumed['conversation_state']['stopped'])

    def test_all_frozen_long_scenarios_are_structurally_valid(self):
        corpus = json.loads((ROOT / 'human_advisor_benchmark' / 'corpus.json').read_text(encoding='utf-8'))
        scenarios = [item for item in corpus['scenarios'] if item['id'].startswith('LONG-')]
        self.assertEqual(len(scenarios), 12)
        for scenario in scenarios:
            state = None
            history = []
            with self.subTest(scenario=scenario['id']):
                for index, turn in enumerate(scenario['turns'], 1):
                    result = resolve(turn['question'], state, history[-10:])
                    state = result['conversation_state']
                    for check in turn.get('checks', []):
                        if check['op'] == 'state_in':
                            self.assertIn(state.get(check['field']), check['value'],
                                          f"{scenario['id']}/{index}")
                    history.extend([
                        {'role': 'user', 'content': turn['question']},
                        {'role': 'assistant', 'content': 'Concise verified response.'},
                    ])


if __name__ == '__main__':
    unittest.main()
