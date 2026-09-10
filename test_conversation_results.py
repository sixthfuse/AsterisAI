"""Advisor and HTTP regressions for retained search results."""
import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from ai_advisor import answer_student_question, find_programs, resolve_academic_context
from conversation_state import TopicState
from test_conversation_state import client_for


class ResultStateTests(unittest.TestCase):
    def ask(self, question, state=None, tool='search_programs', history=None):
        model = client_for(tool, {'query': 'stale nursing query', 'program_id': '8875BSN'})
        with patch('ai_advisor.OpenAI', return_value=model):
            response = TestClient(app).post('/advisor', json={
                'question': question, 'conversation_state': state, 'conversation': history or []})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        if model.responses.requests:
            self.assertEqual(model.responses.requests[0]['tool_choice']['name'], tool)
            self.payload = json.loads(model.responses.requests[1]['input'][0]['output'])
        elif data.get('program_evidence') is not None:
            self.payload = data['program_evidence']
        return data

    def test_exact_live_transcript(self):
        state = self.ask('What about nursing programs?')['conversation_state']
        answer = self.ask("Do you have any programs with a master's degree?", state)
        self.assertEqual(self.payload['programs'], [])
        self.assertIsNone(answer['conversation_state']['unique_result_program_id'])
        answer = self.ask("ok, what about BCIT programs overall, does bcit have any master's degree programs?", answer['conversation_state'])
        self.assertEqual([p['program_id'] for p in self.payload['programs']], ['M600MSC', 'M220MASC', 'M120MENG', 'M410MSC', 'M500MENG'])
        state = answer['conversation_state']
        self.assertEqual(state['scope'], 'global')
        self.assertIsNone(state['unique_result_program_id'])
        answer = self.ask('Tell me about Applied Computing', state, 'get_program_details')
        state = answer['conversation_state']
        for question in ['give me more information about this program',
                         'do you have more information about this program on your asteris database?',
                         'I need more information about this program from asteris.']:
            answer = self.ask(question, state, 'get_program_details')
            self.assertEqual(self.payload['program']['program_id'], 'M600MSC')
            self.assertGreater(len(self.payload['program']), 8)
            state = answer['conversation_state']
        answer = self.ask('ok, i give up.', state)
        self.assertEqual(answer['tools_used'], [])
        self.assertNotIn('Applied Computing', answer['answer'])
        answer = self.ask('do you have any biotechnology or biochemistry programs?', answer['conversation_state'])
        self.assertIn('9940BSC', [p['program_id'] for p in self.payload['programs']])
        self.ask('do you have any biochemistry programs?', answer['conversation_state'])
        self.assertIn('9940BSC', [p['program_id'] for p in self.payload['programs']])

    def test_generic_single_result_scopes_and_followups(self):
        for scope in [TopicState(scope='global', catalog_kind='programs'),
                      TopicState(scope='program_family', scope_query='a test category')]:
            for pid in ['9940BSC', '8630BACC', 'M600MSC']:
                with self.subTest(scope=scope.scope, pid=pid):
                    record = {'program_id': pid, 'program_name': 'Fixture', 'credential': 'Fixture'}
                    with patch('ai_advisor.find_programs', return_value=[record]):
                        answer = self.ask('Are there any others?', scope.model_dump())
                    state = answer['conversation_state']
                    self.assertEqual(state['unique_result_program_id'], pid)
                    for q in ['this program', 'it', 'tell me more', 'more information',
                              'requirements', 'courses', 'admissions', 'where is it offered?']:
                        self.ask(q, state, 'get_program_details')
                        self.assertEqual(self.payload['program']['program_id'], pid)

    def test_result_reference_outlives_browser_window(self):
        state = TopicState(scope='global', catalog_kind='programs', result_query='master', unique_result_program_id='M600MSC').model_dump()
        history = []
        for _ in range(16):
            answer = self.ask('tell me more', state, 'get_program_details', history[-10:])
            self.assertEqual(self.payload['program']['program_id'], 'M600MSC')
            state = answer['conversation_state']
            history.extend([{'role': 'user', 'content': 'tell me more'}, {'role': 'assistant', 'content': 'Details.'}])

    def test_zero_and_multiple_results_clear_reference(self):
        for count in [0, 2]:
            state = TopicState(scope='program_family', scope_query='nursing', unique_result_program_id='M600MSC')
            with patch('ai_advisor.find_programs', return_value=[{'program_id': str(i), 'credential': 'test'} for i in range(count)]):
                answer = self.ask('Are there any others?', state.model_dump())
            self.assertIsNone(answer['conversation_state']['unique_result_program_id'])

    def test_others_preserves_filtered_global_scope(self):
        state = TopicState(scope='global', catalog_kind='programs', result_query='master', unique_result_program_id='M600MSC')
        answer = self.ask('Are there any others?', state.model_dump())
        self.assertEqual([p['program_id'] for p in self.payload['programs']], ['M600MSC', 'M220MASC', 'M120MENG', 'M410MSC', 'M500MENG'])
        self.assertEqual(answer['conversation_state']['result_query'], 'master')

    def test_others_preserves_family_scope(self):
        state = TopicState(scope='program_family', scope_query='nursing programs', unique_result_program_id='8875BSN')
        answer = self.ask('Are there any others?', state.model_dump())
        self.assertEqual(len(self.payload['programs']), 28)
        self.assertEqual(answer['conversation_state']['scope_query'], 'nursing programs')

    def test_explicit_topics_override_result(self):
        state = TopicState(scope='global', catalog_kind='programs', unique_result_program_id='M600MSC')
        for q, scope in [('Tell me about 9940BSC', 'program'), ('Tell me about ELEX 7010', 'course'),
                         ('What about nursing programs?', 'program_family'), ('List all BCIT campuses', 'campus_directory')]:
            resolved = resolve_academic_context(q, [], None, state)
            self.assertEqual(resolved['conversation_state']['scope'], scope)
            self.assertIsNone(resolved['conversation_state']['unique_result_program_id'])

    def test_stop_avoids_all_retrieval_and_keeps_state(self):
        state = TopicState(scope='global', catalog_kind='programs', unique_result_program_id='M600MSC').model_dump()
        for q in ['ok, I give up', 'never mind', "that's enough", "thanks, I'm done"]:
            with patch('ai_advisor.resolve_academic_context', side_effect=AssertionError('retrieval')):
                answer = answer_student_question(q, [], conversation_state=state)
            self.assertEqual(answer['tools_used'], [])
            stopped = answer['conversation_state']
            self.assertTrue(stopped['stopped'])
            self.assertEqual(stopped['turn_index'], state['turn_index'] + 1)
            for field in ('scope', 'program_id', 'course_id', 'scope_query',
                          'unique_result_program_id', 'student_facts', 'conclusions'):
                self.assertEqual(stopped[field], state[field])

    def test_stop_prefix_with_new_request_is_not_swallowed(self):
        self.ask('Never mind, tell me about 9940BSC', tool='get_program_details')
        self.assertEqual(self.payload['program']['program_id'], '9940BSC')

    def test_compound_union_matches_independent_searches(self):
        for left, right in [('biotechnology', 'biochemistry'), ('nursing', 'biochemistry'),
                            ('diploma', 'master'), ('biochemistry', 'biochemistry')]:
            expected = {p['program_id'] for term in [left, right] for p in find_programs(term)}
            actual = find_programs(f'do you have any {left} or {right} programs?')
            self.assertEqual({p['program_id'] for p in actual}, expected)
            self.assertEqual(len(actual), len(expected))

    def test_filtered_set_comparison_keeps_search_constraint(self):
        state = TopicState(scope='global', catalog_kind='programs', result_query='master', unique_result_program_id='M600MSC')
        self.ask('Can international students apply to these programs?', state.model_dump(), 'compare_programs')
        self.assertEqual(self.payload['program_count'], 5)
        self.assertNotIn('8875BSN', json.dumps(self.payload))

    def test_unknown_explicit_search_clears_previous_result(self):
        state = TopicState(scope='global', catalog_kind='programs', result_query='master', unique_result_program_id='M600MSC')
        answer = self.ask('Do you have any underwater basketweaving programs?', state.model_dump())
        self.assertEqual(self.payload['programs'], [])
        self.assertIsNone(answer['conversation_state']['unique_result_program_id'])
        self.assertIsNone(answer['conversation_state']['result_query'])

    def test_explicit_all_credential_programs_overrides_family(self):
        state = TopicState(scope='program_family', scope_query='nursing programs')
        answer = self.ask('List all master programs', state.model_dump())
        self.assertEqual(answer['conversation_state']['scope'], 'global')
        self.assertEqual([p['program_id'] for p in self.payload['programs']], ['M600MSC', 'M220MASC', 'M120MENG', 'M410MSC', 'M500MENG'])

    def test_old_state_payload_remains_valid(self):
        state = TopicState.model_validate({'version': 1, 'scope': 'global', 'catalog_kind': 'programs'})
        self.assertIsNone(state.unique_result_program_id)

if __name__ == '__main__':
    unittest.main()
