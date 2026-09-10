"""Subject transitions against the catalog, with model calls replaced by fixtures."""
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from fastapi.testclient import TestClient
from main import app
from conversation_state import TopicState
from ai_advisor import resolve_academic_context, answer_student_question, execute_tool


def client_for(tool, arguments):
    class Responses:
        def __init__(self):
            self.requests = []
        def create(self, **kwargs):
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                return SimpleNamespace(id='first', output_text='', output=[SimpleNamespace(
                    type='function_call', name=tool, arguments=json.dumps(arguments), call_id='call')])
            return SimpleNamespace(id='second', output=[], output_text='Verified result.')
    return SimpleNamespace(responses=Responses())


def resolve(question, state=None, history=None, selected='9940BSC'):
    return resolve_academic_context(question, history or [], selected, state)


class ConversationStateTests(unittest.TestCase):
    def test_same_name_clarification_lists_credentials_and_resolves_reply(self):
        first = answer_student_question("Tell me about Civil Technology.", [], client=client_for(
            'search_programs', {'query': 'Civil Technology'}
        ))
        self.assertEqual(first['conversation_state']['scope'], 'ambiguous')
        self.assertIn('Associate Certificate', first['answer'])
        self.assertIn('Certificate', first['answer'])

        resolved = resolve("The associate certificate.", first['conversation_state'], selected=None)
        self.assertEqual(resolved['program_id'], '5430ACERT')

        certificate = resolve("Now the Civil Technology certificate.",
                              resolved['conversation_state'], selected=None)
        self.assertEqual(certificate['program_id'], '5430CERT')

    def test_structured_state_returns_to_first_program_beyond_text_window(self):
        first = resolve("Tell me about Applied Computing MSc.", None, selected=None)
        second = resolve("Now tell me about Construction Management BTech.",
                         first['conversation_state'], selected=None)
        neutral_history = [{'role': 'user', 'content': f'Neutral follow-up {i}'} for i in range(30)]
        returned = resolve("Let's return to the first program I mentioned today.",
                           second['conversation_state'], neutral_history, selected=None)
        self.assertEqual(returned['program_id'], 'M600MSC')

    def test_structured_state_keeps_reported_courses_beyond_text_window(self):
        state = resolve("Tell me about Civil Engineering Bachelor of Engineering.",
                        None, selected=None)['conversation_state']
        first = answer_student_question("I passed CIVL 1012.", [], conversation_state=state,
                                        client=client_for('get_program_details', {'program_id': '8660BENG'}))
        self.assertIn('CIVL1012', first['conversation_state']['reported_completed_course_ids'])
        advice_client = client_for('get_student_program_advice', {})
        with patch('ai_advisor.execute_tool', return_value={'completion_percentage': 10}) as tool:
            later = answer_student_question(
                "What can I take next?", [],
                conversation=[{'role': 'user', 'content': f'Neutral follow-up {i}'} for i in range(30)],
                conversation_state=first['conversation_state'],
                client=advice_client,
            )
        completed = {item['course_id'] for item in tool.call_args.args[2]['completed_courses']}
        self.assertIn('CIVL1012', completed)
        self.assertIn('CIVL1012', later['conversation_state']['reported_completed_course_ids'])

    def test_program_family_comparison_scope_outlives_text_window(self):
        state = resolve("Which nursing programs are available?", None, selected=None)['conversation_state']
        later = resolve("Which of those accept international applicants?", state,
                        [{'role': 'user', 'content': f'Neutral {i}'} for i in range(30)], selected=None)
        self.assertTrue(later['program_set_query'])
        self.assertEqual(later['program_set_scope'], 'nursing programs')

    def test_named_comparison_set_persists_and_credential_reply_selects_member(self):
        compared = resolve(
            "Compare the Construction Management diploma and Bachelor of Technology.",
            None, selected=None,
        )
        self.assertEqual(set(compared['comparison_program_ids']), {'7710DIPMA', '8800BTECH'})
        follow_up = resolve("Is the other one also a degree?", compared['conversation_state'],
                            selected=None)
        self.assertEqual(set(follow_up['comparison_program_ids']), {'7710DIPMA', '8800BTECH'})
        selected = resolve("I mean the diploma.", follow_up['conversation_state'], selected=None)
        self.assertEqual(selected['program_id'], '7710DIPMA')

    def test_three_named_comparison_members_are_not_replaced_by_family_search(self):
        compared = resolve(
            "Compare the Nursing BSN full-time, Applied Computing MSc, and Construction Management BTech.",
            None, selected=None,
        )
        self.assertEqual(set(compared['comparison_program_ids']),
                         {'8875BSN', 'M600MSC', '8800BTECH'})
    def test_real_sequence_uses_all_nursing_international_records(self):
        state = None
        history = []
        for question in ['Tell me about biochemistry 9940BSC',
                         'Can international students apply to this program?',
                         'What about nursing programs?']:
            result = resolve(question, state, history)
            state = result['conversation_state']
            history.extend([{'role': 'user', 'content': question},
                            {'role': 'assistant', 'content': '9940BSC and CHEM 1110 were discussed earlier.'}])
        client = client_for('compare_programs', {'query': 'Can international students apply?'})
        answer = answer_student_question('Can international students apply?', [],
                                         conversation=history, conversation_state=state, client=client)
        self.assertEqual(client.responses.requests, [])
        data = answer['program_evidence']
        self.assertEqual(data['program_count'], 28)
        self.assertIsNone(answer['resolved_program'])
        encoded = json.dumps(data)
        self.assertIn('8875BSN', encoded)
        self.assertIn('explicitly unavailable', encoded)
        self.assertNotIn('9940BSC', encoded)
        self.assertEqual(answer['conversation_state']['scope'], 'program_family')

    def test_reverse_sequence_forces_biochemistry_details(self):
        history = [{'role': 'user', 'content': text} for text in [
            'Tell me about nursing programs', 'Can international students apply?',
            'Tell me about 9940BSC', 'Can international students apply?']]
        state = None
        for message in history[:-1]:
            state = resolve(message['content'], state)['conversation_state']
        client = client_for('get_program_details', {'program_id': '8875BSN'})
        result = answer_student_question(history[-1]['content'], [], conversation=history[:-1],
                                         conversation_state=state, client=client)
        self.assertEqual(client.responses.requests[0]['tool_choice']['name'], 'get_program_details')
        data = json.loads(client.responses.requests[1]['input'][0]['output'])
        self.assertEqual(data['program']['program_id'], '9940BSC')
        self.assertEqual(result['conversation_state']['program_id'], '9940BSC')

    def test_structured_state_outlives_thirty_neutral_turns(self):
        for subject in ['What about nursing programs?', 'Tell me about 9940BSC',
                        'Tell me about ELEX 7010', 'List all programs', 'List all BCIT campuses']:
            with self.subTest(subject=subject):
                state = resolve(subject)['conversation_state']
                expected = TopicState.from_value(state).identity()
                history = [{'role': 'assistant', 'content': 'Old 9940BSC and ELEX 7010 details.'}]
                for _ in range(30):
                    state = resolve('Tell me more', state, history)['conversation_state']
                    self.assertEqual(TopicState.from_value(state).identity(), expected)

    def test_legacy_history_replay_respects_boundaries(self):
        subjects = ['Tell me about 9940BSC', 'Tell me about nursing programs',
                    'Tell me about ELEX 7010', 'List all BCIT campuses',
                    'List all programs', 'Tell me about 8630BACC']
        history = []
        state = None
        for subject in subjects:
            state = resolve(subject, state)['conversation_state']
            history.append({'role': 'user', 'content': subject})
            history.append({'role': 'assistant', 'content': 'Earlier 9940BSC and ELEX 7010 information.'})
            for _ in range(3):
                history.append({'role': 'user', 'content': 'Tell me more'})
            actual = resolve('Can international students apply?', history=history)['conversation_state']
            self.assertEqual(TopicState.from_value(actual).identity(), TopicState.from_value(state).identity())

    def test_unresolved_state_allows_recent_turn_fallback(self):
        result = resolve('Can international students apply?', TopicState(scope='none'),
                         [{'role': 'user', 'content': 'What about nursing programs?'}])
        self.assertEqual(result['conversation_state']['scope'], 'program_family')
        self.assertIsNone(result['program_id'])

    def test_family_search_ignores_stale_model_query(self):
        state = resolve('What about nursing programs?')
        result = execute_tool('search_programs', {'query': '9940BSC'}, state)
        self.assertEqual(result['active_program_count'], 28)
        self.assertNotIn('9940BSC', [p['program_id'] for p in result['programs']])

    def test_ambiguous_explicit_switch_does_not_reuse_old_program(self):
        previous = resolve('Tell me about 9940BSC')['conversation_state']
        result = resolve('Tell me about the Specialty Nursing Emergency option', previous)
        self.assertIsNone(result['program_id'])
        self.assertEqual(result['conversation_state']['scope'], 'ambiguous')

    def test_applicant_credential_does_not_switch_subject(self):
        state = resolve('Tell me about 9940BSC')['conversation_state']
        self.assertEqual(resolve('I have a business diploma. Can I apply?', state)['program_id'], '9940BSC')

    def test_state_does_not_store_language(self):
        state = resolve('Tell me about 9940BSC')['conversation_state']
        for question, language in [('¿Cuáles son los requisitos?', 'Spanish'),
                                   ('What are the prerequisites?', 'English')]:
            client = client_for('get_program_details', {'program_id': '9940BSC'})
            result = answer_student_question(question, [], conversation_state=state, client=client)
            self.assertIn(language, client.responses.requests[0]['input'])
            self.assertNotIn('language', result['conversation_state'])

    def test_api_roundtrip_and_fresh_reset(self):
        http = TestClient(app)
        with patch('ai_advisor.OpenAI', return_value=client_for('search_programs', {'query': 'nursing programs'})):
            first = http.post('/advisor', json={'question': 'What about nursing programs?'}).json()
        self.assertEqual(first['conversation_state']['scope'], 'program_family')
        model = client_for('compare_programs', {'query': 'Can international students apply?'})
        with patch('ai_advisor.OpenAI', return_value=model):
            second = http.post('/advisor', json={'question': 'Can international students apply?',
                'conversation_state': first['conversation_state'],
                'conversation': [{'role': 'assistant', 'content': 'Old 9940BSC details.'}]}).json()
        self.assertEqual(second['conversation_state']['scope'], 'program_family')
        fresh = http.post('/advisor', json={'question': 'How many programs do you offer?'}).json()
        self.assertEqual(fresh['conversation_state']['scope'], 'global')
        self.assertIsNone(fresh['conversation_state']['scope_query'])

    def test_malformed_state_is_rejected_at_api_boundary(self):
        response = TestClient(app).post('/advisor', json={'question': 'Tell me more',
            'conversation_state': {'scope': 'program'}})
        self.assertEqual(response.status_code, 422)

    def test_named_campus_persists(self):
        state = resolve('Tell me about Burnaby campus')['conversation_state']
        answer = answer_student_question('Tell me more', [], conversation_state=state)
        self.assertEqual(len(answer['campuses']), 1)
        self.assertIn('Burnaby', answer['answer'])

    def test_course_tool_ignores_stale_model_course_argument(self):
        state = resolve('Tell me about ELEX 7010')
        with patch('ai_advisor.get_course_details', return_value=({}, [])) as lookup:
            execute_tool('get_course_details', {'course_id': 'SURV2205'}, state)
        lookup.assert_called_once_with('ELEX7010')

    def test_named_campus_switch_does_not_require_word_campus(self):
        state = resolve('Tell me about Burnaby campus')['conversation_state']
        state = resolve('What about Downtown?', state)['conversation_state']
        self.assertEqual(state['scope'], 'campus')
        self.assertEqual(state['campus_name'], 'Downtown Campus')
        answer = answer_student_question('What is its address?', [], conversation_state=state)
        self.assertIn('555 Seymour', answer['answer'])

    def test_course_prerequisite_within_program_requirement_keeps_program_subject(self):
        state = resolve('Tell me about the Construction Management Bachelor of Technology')['conversation_state']
        state = resolve('Can I do the capstone?', state)['conversation_state']
        result = answer_student_question('What do I need before CMGT 8700?', [], conversation_state=state)
        self.assertEqual(result['tools_used'], ['get_course_details'])
        self.assertEqual(result['conversation_state']['program_id'], '8800BTECH')


    def test_family_alias_without_plural_is_an_explicit_switch(self):
        state = resolve('Tell me about 9940BSC')['conversation_state']
        result = resolve('What about nursing specialties?', state)
        self.assertEqual(result['conversation_state']['scope'], 'program_family')
        self.assertIsNone(result['program_id'])

    def test_bare_family_names_use_catalog_aliases(self):
        prior = resolve('Tell me about 9940BSC')['conversation_state']
        for phrase in ['What about nursing?', 'What about aircraft maintenance?']:
            with self.subTest(phrase=phrase):
                result = resolve(phrase, prior)
                self.assertEqual(result['conversation_state']['scope'], 'program_family')
                self.assertIsNone(result['program_id'])

    def test_current_eligibility_question_overrides_stale_model_comparison_query(self):
        state = resolve('What about nursing programs?')['conversation_state']
        client = client_for('compare_programs', {'query': 'admission requirements for biochemistry'})
        answer = answer_student_question('International eligibility?', [], conversation_state=state, client=client)
        self.assertEqual(client.responses.requests, [])
        data = answer['program_evidence']
        self.assertEqual(data['program_count'], 28)
        self.assertIn('explicitly unavailable', json.dumps(data))
        self.assertNotIn('9940BSC', json.dumps(data))

    def test_compound_family_eligibility_retains_clean_scope(self):
        result = resolve('Can international students apply to nursing programs?')
        self.assertEqual(result['program_set_scope'], 'nursing programs')
        data = execute_tool('compare_programs', {'query': 'Can international students apply?'}, result)
        self.assertEqual(data['program_count'], 28)

    def test_global_eligibility_uses_complete_catalog(self):
        state = resolve('List all programs')['conversation_state']
        client = client_for('compare_programs', {'query': 'Can international students apply?'})
        answer_student_question('Can international students apply?', [], conversation_state=state, client=client)
        self.assertEqual(client.responses.requests[0]['tool_choice']['name'], 'compare_programs')
        data = json.loads(client.responses.requests[1]['input'][0]['output'])
        self.assertEqual(data['program_count'], 374)

    def test_single_verified_course_search_result_is_persisted(self):
        client = client_for('search_courses', {'query': 'civil 3d'})
        with patch('ai_advisor.find_courses', return_value=[{'course_id': 'SURV2205',
            'course_name': 'Civil 3D: Introduction', 'display_course_code': 'SURV 2205'}]):
            answer = answer_student_question('Do you offer civil 3d?', [],
                conversation_state=resolve('Tell me about 9940BSC')['conversation_state'], client=client)
        self.assertEqual(answer['conversation_state']['scope'], 'course')
        self.assertEqual(answer['conversation_state']['course_id'], 'SURV2205')
        following = resolve('What are its prerequisites?', answer['conversation_state'])
        self.assertEqual(following['course_id'], 'SURV2205')
        self.assertIsNone(following['program_id'])

    def test_all_catalog_program_names_override_family_and_course(self):
        from ai_advisor import _topic_catalog
        catalog = _topic_catalog()[0]
        name_counts = {}
        for _, name, _ in catalog:
            name_counts[name] = name_counts.get(name, 0) + 1
        for pid, name, credential in catalog:
            for prior in [resolve('What about nursing programs?')['conversation_state'],
                          TopicState(scope='course', course_id='ELEX7010')]:
                with self.subTest(program=pid, prior=prior):
                    result = resolve(f'What are the admission requirements for {name}?', prior)
                    if name_counts[name] == 1:
                        self.assertEqual(result['program_id'], pid)
                    else:
                        self.assertIsNone(result['program_id'])
                    self.assertIsNone(result['course_id'])


TRANSITIONS = [
    ('program_program', 'Tell me about 9940BSC', 'Tell me about 8630BACC', 'program', '8630BACC'),
    ('family_program', 'What about nursing programs?', 'Tell me about 9940BSC', 'program', '9940BSC'),
    ('program_family', 'Tell me about 9940BSC', 'What about nursing programs?', 'program_family', None),
    ('course_program', 'Tell me about ELEX 7010', 'Tell me about 9940BSC', 'program', '9940BSC'),
    ('campus_program', 'List all BCIT campuses', 'Tell me about 9940BSC', 'program', '9940BSC'),
    ('global_program', 'List all programs', 'Tell me about 9940BSC', 'program', '9940BSC'),
    ('program_course', 'Tell me about 9940BSC', 'Tell me about ELEX 7010', 'course', None),
    ('program_campus', 'Tell me about 9940BSC', 'List all BCIT campuses', 'campus_directory', None),
    ('family_global', 'What about nursing programs?', 'List all programs', 'global', None),
    ('family_family', 'What about nursing programs?', 'What about aircraft maintenance programs?', 'program_family', None),
]
FOLLOWUPS = ['Tell me more', 'Can international students apply?', 'What are the prerequisites?',
             'What is its location?', 'What about them?', 'Those', 'This program', 'These programs',
             'It', 'What are their requirements?', 'What about that course?']


def transition_test(first, second, scope, program, followup):
    def test(self):
        prior = resolve(first)['conversation_state']
        switched = resolve(second, prior)['conversation_state']
        history = [{'role': 'user', 'content': first},
                   {'role': 'assistant', 'content': 'Old 9940BSC and ELEX 7010 information.'}]
        result = resolve(followup, switched, history)
        self.assertEqual(result['conversation_state']['scope'], scope)
        self.assertEqual(result['program_id'], program)
        if scope != 'course':
            self.assertIsNone(result['course_id'])
        fresh = resolve(second)['conversation_state']
        fresh_result = resolve(followup, fresh)
        # Explicit switches must produce the same active resolution. Historical
        # memory fields are intentionally retained for later "return" requests.
        for value in (result, fresh_result):
            for memory_field in (
                'prior_program_ids', 'reported_completed_course_ids',
                'reported_completed_courses', 'subject_history', 'student_facts',
                'conclusions', 'answered_facets', 'stopped', 'turn_index',
            ):
                value['conversation_state'].pop(memory_field, None)
        self.assertEqual(result, fresh_result)
    return test


for name, first, second, scope, program in TRANSITIONS:
    for index, followup in enumerate(FOLLOWUPS):
        setattr(ConversationStateTests, f'test_matrix_{name}_{index:02}',
                transition_test(first, second, scope, program, followup))

if __name__ == '__main__':
    unittest.main()
