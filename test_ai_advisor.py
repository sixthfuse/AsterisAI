"""Unit tests for Phase 5 AI routing; no live API or database required."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

from ai_advisor import (
    AdvisorIntent,
    answer_student_question,
    add_credit_requirement_presentations,
    authoritative_course_overview_answer,
    build_verification_metadata,
    classify_intent,
    compare_programs,
    execute_tool,
    extract_conversation_completed_courses,
    find_programs,
    get_program_electives,
    get_program_progression_requirements,
    get_program_details,
    get_student_level_requirements,
    get_student_level_readiness,
    hide_internal_program_ids,
    current_message_language,
    is_global_catalog_question,
    is_global_course_discovery_question,
    is_cross_program_comparison,
    is_program_set_question,
    is_out_of_scope_question,
    normalize_course_id,
    resolve_academic_context,
    requested_target_level,
    student_verification_metadata,
    catalog_count_answer,
    course_detail_answer,
    course_prerequisites_answer,
    finalize_student_answer,
    format_embedded_course_codes,
    is_course_count_question,
    is_conversational_stop,
)
from advisor import clean_course_title, display_course_code


class CourseAuthorityTests(unittest.TestCase):
    CARD_OVERVIEW = (
        "This online course introduces related health disciplines. "
        "Concepts in preceptoring/mentoring, and professional responsibility will be covered."
    )

    def test_libs_7001_preserves_all_or_alternatives(self):
        from advisor import get_course_details

        course, prerequisites = get_course_details("LIBS7001")
        answer = course_prerequisites_answer(course, prerequisites)

        self.assertIn("ENGL 1177", answer)
        self.assertIn("6 credits of BCIT Communication at 1100-level or above", answer)
        self.assertIn("3 credits of first-year university/college social science or humanities", answer)
        self.assertEqual(answer.count(" OR "), 2)
        self.assertNotIn("None", answer)

    def test_finalization_does_not_choose_between_same_title_course_identities(self):
        final = finalize_student_answer("Engineering Economics is included.", "What is included?", [{
            "courses": [
                {"course_id": "CIVL7000", "display_course_code": "CIVL 7000",
                 "course_name": "Engineering Economics"},
                {"course_id": "UBCCIVL7000", "display_course_code": "UBC CIVL 7000",
                 "course_name": "Engineering Economics"},
            ]
        }])

        self.assertEqual(final, "Engineering Economics is included.")
        self.assertNotIn("UBC", final)

    def test_finalization_does_not_replace_title_substrings_with_other_course_codes(self):
        final = finalize_student_answer(
            "UBC CHEM 203 — Introduction to Organic Chemistry is required.",
            "Which courses are required?",
            [{"courses": [
                {"course_id": "UBC-CHEM-203", "display_course_code": "UBC CHEM 203",
                 "course_name": "Introduction to Organic Chemistry"},
                {"course_id": "UBC-CHEM-213", "display_course_code": "UBC CHEM 213",
                 "course_name": "Organic Chemistry"},
            ]}],
        )
        self.assertEqual(final, "UBC CHEM 203 — Introduction to Organic Chemistry is required.")

    def test_finalization_keeps_civil_statistics_identity(self):
        final = finalize_student_answer(
            "MATH 2423 — Introductory Statistics for Civil Engineering is required.",
            "Which courses are required?",
            [{"courses": [
                {"course_id": "MATH2423", "display_course_code": "MATH 2423",
                 "course_name": "Introductory Statistics for Civil Engineering"},
                {"course_id": "CIVL1020", "display_course_code": "CIVL 1020",
                 "course_name": "Statistics for Civil Engineering"},
            ]}],
        )
        self.assertEqual(final, "MATH 2423 — Introductory Statistics for Civil Engineering is required.")

    def test_null_pathway_level_course_tool_returns_program_clarification(self):
        result = execute_tool("get_program_level_courses", {"level": 1}, {
            "program_id": None, "pathway": None,
        })
        self.assertIn("which program", result["error"].lower())

    def test_civil_credential_award_is_bound_separately_from_level_five_progression(self):
        result = execute_tool("get_program_details", {"program_id": "8660BENG"}, {
            "program_id": "8660BENG", "academic_scope": "admission",
        })["program"]
        boundaries = result["academic_scope_boundaries"]

        self.assertTrue(any("Diploma in Civil Engineering credential" in sentence
                            for sentence in boundaries["credential_award_evidence"]))
        self.assertTrue(any(rule["to_level"] == 5
                            for rule in boundaries["later_level_progression_requirements"]))
        self.assertIn("not conditions for an earlier credential", boundaries["binding_rule"])
        self.assertNotIn("curriculum", result)

    def test_stop_intent_handles_plain_compound_and_question_override(self):
        for text in ("Stop.", "Thanks, that's all.", "Okay, no more for now.", "Let's stop here."):
            self.assertTrue(is_conversational_stop(text), text)
        self.assertFalse(is_conversational_stop("Never mind, where is the program taught?"))

    def test_card_3365_overview_is_verbatim_and_uses_raw_prerequisite_fallback(self):
        result = authoritative_course_overview_answer("Give me the course overview", [{
            "course": {
                "course_id": "CARD3365",
                "display_course_code": "CARD 3365",
                "course_name": "Interprofessional Practice for Cardiac Sciences",
                "course_overview": self.CARD_OVERVIEW,
                "prerequisite_source": "authoritative_raw_text",
                "prerequisite_text": "S in CARD 3252",
            },
            "prerequisites": [],
        }])

        self.assertIn(self.CARD_OVERVIEW, result)
        self.assertIn("responsibility will be covered.", result)
        self.assertIn("Prerequisites: S in CARD 3252", result)
        self.assertTrue(result.startswith("CARD 3365 "))

    def test_empty_structured_rows_do_not_mean_none_when_source_is_unknown(self):
        result = authoritative_course_overview_answer("Course overview", [{
            "course": {
                "course_id": "CARD3365",
                "course_name": "Interprofessional Practice for Cardiac Sciences",
                "course_overview": self.CARD_OVERVIEW,
                "prerequisite_source": "unknown",
            },
            "prerequisites": [],
        }])

        self.assertIn("Prerequisite information is unavailable", result)
        self.assertNotIn("None listed", result)

    def test_explicit_none_is_the_only_empty_rule_case_reported_as_none(self):
        result = authoritative_course_overview_answer("Course overview", [{
            "course": {
                "course_id": "TEST1000",
                "course_name": "Test Course",
                "course_overview": "Test overview.",
                "prerequisite_source": "explicit_none",
            },
            "prerequisites": [],
        }])

        self.assertIn("Prerequisites: None listed.", result)

    def test_duplicate_embedded_codes_are_removed_case_insensitively(self):
        self.assertEqual(
            clean_course_title("CARD3365 Interprofessional Practice", "CARD3365"),
            "Interprofessional Practice",
        )
        self.assertEqual(
            clean_course_title("CLRK2500 — Healthcare Unit Clerk Practicum", "CLRK2500"),
            "Healthcare Unit Clerk Practicum",
        )

    def test_canonical_course_keys_are_spaced_for_students(self):
        self.assertEqual(display_course_code("SURV2205"), "SURV 2205")
        self.assertEqual(
            format_embedded_course_codes("Take CHEM0108 after MATH-1001."),
            "Take CHEM 0108 after MATH 1001.",
        )
        url = "https://www.bcit.ca/courses/civil-3d-introduction-SURV2205/"
        self.assertEqual(format_embedded_course_codes(url), url)

    def test_global_course_detail_renderer_includes_all_available_fields(self):
        answer = course_detail_answer({
            "course_id": "SURV2205",
            "display_course_code": "SURV 2205",
            "course_name": "SURV2205 Civil 3D: Introduction",
            "course_overview": "An introductory Civil 3D course.",
            "credits": "3.00",
            "status": "Active",
            "source_url": "https://example.test/SURV2205",
            "prerequisite_source": "authoritative_raw_text",
            "prerequisite_text": "Prior completion of SURV1100.",
        }, [])
        self.assertIn("SURV 2205 — Civil 3D: Introduction", answer)
        self.assertIn("Credits: 3.00", answer)
        self.assertIn("Prerequisites: Prior completion of SURV 1100.", answer)
        self.assertIn("Status: Active", answer)
        self.assertIn("https://example.test/SURV2205", answer)

    def test_direct_course_api_includes_clean_title_and_display_code(self):
        response = TestClient(app).get("/courses/SURV2205")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["course_id"], "SURV2205")
        self.assertEqual(payload["display_course_code"], "SURV 2205")
        self.assertEqual(payload["course_name"], "Civil 3D: Introduction")


class VerificationMetadataTests(unittest.TestCase):
    def test_student_footer_is_suppressed_without_successful_academic_data(self):
        self.assertIsNone(student_verification_metadata([], []))
        self.assertIsNone(student_verification_metadata(
            ["get_student_program_advice"],
            [{"error": "Please tell me which program you are taking."}],
        ))

    def test_student_generic_fallback_remains_for_successful_unknown_shape(self):
        metadata = student_verification_metadata(
            ["future_academic_tool"], [{"verified": True}]
        )

        self.assertIsNotNone(metadata)
        self.assertFalse(metadata["exact_count_available"])

    def test_simple_catalog_result_counts_one_academic_fact(self):
        metadata = build_verification_metadata(
            ["search_programs"],
            [{"programs": [{"program_id": "8800BTECH"}]}],
        )

        self.assertEqual(
            metadata,
            {"count": 1, "kind": "fact", "exact_count_available": True},
        )

    def test_program_advice_counts_structured_evaluation_units(self):
        metadata = build_verification_metadata(
            ["get_student_program_advice"],
            [{
                "program_complete": False,
                "next_courses": [{"course_id": "A"}, {"course_id": "B"}],
                "missing_requirements": [{"course_id": "C"}],
                "unsatisfied_choice_groups": [{"group_id": 1}],
                "optional_requirements": [{"course_id": "D"}],
            }],
        )

        self.assertEqual(metadata["count"], 6)
        self.assertEqual(metadata["kind"], "requirement")
        self.assertTrue(metadata["exact_count_available"])

    def test_rule_leaves_and_choice_relationship_are_counted_and_deduplicated(self):
        red_seal = {
            "condition_id": 101, "condition_type": "RED_SEAL_TRADE",
            "accepted_values": ["electrician"],
        }
        math = {
            "condition_id": 102, "condition_type": "MATH_OPTION_GRADE",
            "minimum_value": 60, "unit": "PERCENT",
        }
        rules = {"requirements": [{
            "rule_set_id": 7,
            "groups": [{
                "rule_group_id": 8, "operator": "AND", "label": "Pathway D",
                "conditions": [red_seal, math],
                "children": [{
                    "rule_group_id": 9, "operator": "OR",
                    "label": "Choose one final project",
                    "conditions": [
                        {"condition_id": 103, "condition_type": "COURSE", "subject_id": "CMGT8800"},
                        {"condition_id": 104, "condition_type": "COURSE", "subject_id": "CMGT8810"},
                    ],
                }],
            }],
        }]}

        metadata = build_verification_metadata(
            ["get_program_progression_requirements", "get_program_progression_requirements"],
            [rules, rules],
        )

        self.assertEqual(metadata["count"], 5)
        self.assertEqual(metadata["kind"], "requirement")

    def test_red_seal_scenario_counts_leaf_conditions_not_three_rule_sets(self):
        condition_types = (
            "RED_SEAL_TRADE", "MATH_OPTION_GRADE", "BRIDGING_CREDENTIAL_GPA",
            "WORK_EXPERIENCE", "ENGLISH_GRADE", "PRE_ENTRY_ASSESSMENT",
            "PROGRAM_COURSES_COMPLETE_EXCEPT", "INDUSTRY_TOPIC", "INDUSTRY_SPONSOR",
        )
        payload = {"requirements": [{
            "rule_set_id": 1,
            "groups": [{
                "rule_group_id": 10, "operator": "AND", "label": "Pathway D",
                "conditions": [
                    {"condition_id": index, "condition_type": condition_type}
                    for index, condition_type in enumerate(condition_types, 1)
                ],
            }],
        }]}

        metadata = build_verification_metadata(
            ["get_program_progression_requirements"], [payload]
        )

        self.assertEqual(metadata["count"], len(condition_types))
        self.assertGreater(metadata["count"], len(payload["requirements"]))

    def test_unknown_result_shape_uses_generic_fallback(self):
        metadata = build_verification_metadata(
            ["future_academic_tool"], [{"verified": True}]
        )

        self.assertIsNone(metadata["count"])
        self.assertFalse(metadata["exact_count_available"])

    def test_error_result_is_not_counted(self):
        metadata = build_verification_metadata(
            ["search_programs"], [{"error": "lookup failed"}]
        )

        self.assertIsNone(metadata["count"])
        self.assertFalse(metadata["exact_count_available"])


class FakeResponses:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return next(self._responses)


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


class AiAdvisorTests(unittest.TestCase):
    def _advisor_client(self, tool_name, arguments, final_answer="Verified catalog results."):
        call = SimpleNamespace(
            type="function_call", name=tool_name,
            arguments=json.dumps(arguments), call_id=f"{tool_name}-call",
        )
        return FakeClient([
            SimpleNamespace(id="tool-request", output=[call], output_text=""),
            SimpleNamespace(id="final-answer", output=[], output_text=final_answer),
        ])

    @patch("ai_advisor.get_connection")
    def test_explicit_program_and_course_mentions_override_stale_entity_context(
        self, get_connection
    ):
        cursor = get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ("8900BTECH", "Electronics Bachelor of Technology", "Bachelor of Technology"),
            ("8660BENG", "Civil Engineering Bachelor of Engineering", "Bachelor's Degree"),
        ]
        course_conversation = [
            {"role": "user", "content": "tell me about ELEX 7010"},
            {"role": "assistant", "content": "ELEX 7010 — Engineering Statistics"},
        ]

        same_course = resolve_academic_context(
            "more about this course", course_conversation, None
        )
        self.assertEqual(same_course["course_id"], "ELEX7010")
        self.assertIsNone(same_course["program_id"])

        program_phrases = (
            "more about the electronics program",
            "more about the bachelor degree of electronics",
            "more about the electronics bachelor of technology degree",
            "the electronics degree",
        )
        for phrase in program_phrases:
            with self.subTest(phrase=phrase):
                switched = resolve_academic_context(phrase, course_conversation, None)
                self.assertEqual(switched["program_id"], "8900BTECH")
                self.assertIsNone(switched["course_id"])

        program_conversation = course_conversation + [
            {"role": "user", "content": "more about the electronics program"},
            {"role": "assistant", "content": "Electronics Bachelor of Technology details."},
        ]
        admissions = resolve_academic_context(
            "what are the admission requirements?", program_conversation, None
        )
        self.assertEqual(admissions["program_id"], "8900BTECH")
        self.assertIsNone(admissions["course_id"])

        named_course = resolve_academic_context(
            "tell me about ELEX 7010", program_conversation, None
        )
        self.assertEqual(named_course["course_id"], "ELEX7010")
        self.assertIsNone(named_course["program_id"])

    def test_global_course_discovery_overrides_stale_program_context(self):
        conversation = [
            {"role": "user", "content": "Tell me about the Civil Engineering Diploma program."},
            {"role": "assistant", "content": "Here is the Civil Engineering Diploma."},
        ]
        for question in (
            "do you offer any biology courses?",
            "does BCIT offer any chemistry courses?",
            "show me BCIT-wide wood courses",
            "do you have any Civil 3D/CAD courses?",
        ):
            with self.subTest(question=question):
                context = resolve_academic_context(question, conversation, "5410DIPLT")
                self.assertTrue(is_global_course_discovery_question(question))
                self.assertTrue(context["global_catalog"])
                self.assertIsNone(context["program_id"])
                self.assertEqual(classify_intent(question), AdvisorIntent.COURSE_INFO)

    def test_all_of_bcit_correction_resets_program_scope(self):
        conversation = [
            {"role": "user", "content": "Tell me about Civil Engineering."},
            {"role": "assistant", "content": "Here is the Civil Engineering program."},
            {"role": "user", "content": "do you offer any biology courses?"},
            {"role": "assistant", "content": "I could not find biology in that program."},
        ]
        question = "not the civil engineering program, all of BCIT"
        context = resolve_academic_context(question, conversation, "5410DIPLT")
        self.assertTrue(is_global_course_discovery_question(question))
        self.assertTrue(context["global_catalog"])
        self.assertIsNone(context["program_id"])

    def test_explicit_program_scoped_course_discovery_keeps_program(self):
        conversation = [
            {"role": "user", "content": "Tell me about the Civil Engineering Diploma program."},
        ]
        for question in (
            "what biology courses are in Civil Engineering?",
            "what chemistry courses are in this program?",
            "what CAD courses are within this program?",
        ):
            with self.subTest(question=question):
                context = resolve_academic_context(question, conversation, "5410DIPLT")
                self.assertFalse(is_global_course_discovery_question(question))
                self.assertFalse(context["global_catalog"])
                self.assertEqual(context["program_id"], "5410DIPLT")

    def test_global_course_search_forces_course_search_tool(self):
        client = self._advisor_client(
            "search_courses", {"query": "biology"},
            "BHSC 0012 and FSCT 8150 are relevant biology courses.",
        )
        result = answer_student_question(
            "does BCIT offer any biology courses?", [],
            program_id="5410DIPLT", client=client,
        )
        request = client.responses.requests[0]
        self.assertEqual(request["tool_choice"], {"type": "function", "name": "search_courses"})
        self.assertEqual(result["resolved_program"], None)

    @patch("ai_advisor.get_course_details")
    @patch("ai_advisor.get_connection")
    def test_global_search_then_selected_course_follow_up_keeps_active_course(
        self, get_connection, get_details
    ):
        cursor = get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ("5410DIPLT", "Civil Engineering Diploma", "Diploma"),
        ]
        get_details.return_value = ({
            "course_id": "FSCT8150", "display_course_code": "FSCT 8150",
            "course_name": "Forensic Biology: DNA Typing Theory", "course_overview": "Overview.",
            "credits": "3.00", "status": "Active", "source_url": "https://example.test/fsct8150",
            "prerequisite_source": "authoritative_raw_text",
            "prerequisite_text": "3 credits of a university/college biology course.",
        }, [])
        conversation = [
            {"role": "user", "content": "does BCIT offer any biology courses?"},
            {"role": "assistant", "content": "BHSC 0012 and FSCT 8150 are relevant."},
            {"role": "user", "content": "tell me about FSCT 8150"},
            {"role": "assistant", "content": "FSCT 8150 — Forensic Biology: DNA Typing Theory."},
        ]
        result = answer_student_question("what are its prerequisites?", [], conversation=conversation)
        self.assertIsNone(result["resolved_program"])
        self.assertEqual(result["tools_used"], ["get_course_details"])
        self.assertIn("3 credits of a university/college biology course.", result["answer"])

    @patch("ai_advisor.get_catalog_counts", return_value={
        "course_record_count": 1152, "active_program_count": 4,
    })
    def test_course_count_variants_are_deterministic(self, get_counts):
        for question in (
            "How many courses does BCIT offer?",
            "How many courses do you have?",
            "How many courses do you offer?",
        ):
            self.assertTrue(is_course_count_question(question))
            result = answer_student_question(question, [])
            self.assertEqual(
                result["answer"],
                "BCIT has 1,152 active courses in the catalog Asteris uses.",
            )
            self.assertEqual(result["tools_used"], ["get_catalog_counts"])
        self.assertEqual(get_counts.call_count, 3)

    @patch("ai_advisor.get_catalog_counts", return_value={
        "course_record_count": 1152, "active_program_count": 4,
    })
    def test_spanish_course_count_variants_are_deterministic(self, get_counts):
        for question in (
            "¿Cuántos cursos ofrecen?",
            "¿Cuántos cursos tiene BCIT?",
            "¿Cuántos cursos tienen en BCIT?",
            "¿Cuántos cursos tienen?",
            "¿Cuántos cursos tenés?",
            "¿Cuantos cursos tenes?",
            "¿Cuántos cursos hay?",
        ):
            with self.subTest(question=question):
                self.assertTrue(is_course_count_question(question))
                result = answer_student_question(question, [])
                self.assertEqual(
                    result["answer"],
                    "BCIT tiene 1,152 cursos activos en el catálogo que usa Asteris.",
                )
                self.assertEqual(result["tools_used"], ["get_catalog_counts"])
                self.assertNotIn("search_courses", result["tools_used"])
                self.assertIsNone(result["resolved_program"])
        self.assertEqual(get_counts.call_count, 7)

    @patch("ai_advisor.get_catalog_counts", return_value={
        "course_record_count": 1152, "active_program_count": 4,
    })
    def test_compound_program_and_course_count_returns_both_live_counts(self, _):
        result = answer_student_question(
            "How many programs do you offer, and how many courses?", []
        )
        self.assertEqual(
            result["answer"],
            "BCIT has 4 active programs and 1,152 active courses in the catalog Asteris uses.",
        )
        self.assertEqual(result["verification"]["count"], 2)

    @patch("ai_advisor.get_catalog_counts", return_value={
        "course_record_count": 1152, "active_program_count": 4,
    })
    def test_spanish_compound_program_and_course_count_returns_both_live_counts(self, _):
        result = answer_student_question(
            "¿Cuántos programas y cursos tienen?", []
        )
        self.assertEqual(
            result["answer"],
            "BCIT tiene 4 programas activos y 1,152 cursos activos en el catálogo que usa Asteris.",
        )
        self.assertEqual(result["tools_used"], ["get_catalog_counts"])
        self.assertEqual(result["verification"]["count"], 2)

    @patch("ai_advisor.get_course_details")
    @patch("ai_advisor.get_connection")
    def test_search_then_more_details_resolves_global_active_course_from_history(
        self, get_connection, get_details
    ):
        cursor = get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ("8660BENG", "Civil Engineering Bachelor of Engineering", "Bachelor's Degree")
        ]
        get_details.return_value = ({
            "course_id": "SURV2205", "display_course_code": "SURV 2205",
            "course_name": "Civil 3D: Introduction", "course_overview": "Overview.",
            "credits": "3.00", "status": "Active", "source_url": "https://example.test/surv",
            "prerequisite_source": "explicit_none",
        }, [])
        result = answer_student_question(
            "more about this course", [],
            conversation=[
                {"role": "user", "content": "do you offer civil 3d?"},
                {"role": "assistant", "content": "SURV 2205 — Civil 3D: Introduction is available."},
            ],
        )
        get_details.assert_called_once_with("SURV2205")
        self.assertEqual(result["tools_used"], ["get_course_details"])
        self.assertIn("SURV 2205 — Civil 3D: Introduction", result["answer"])

    @patch("ai_advisor.get_course_details")
    @patch("ai_advisor.get_connection")
    def test_multiturn_global_course_context_overrides_old_program_for_credits(
        self, get_connection, get_details
    ):
        cursor = get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ("8660BENG", "Civil Engineering Bachelor of Engineering", "Bachelor's Degree")
        ]
        get_details.return_value = ({
            "course_id": "SURV2205", "display_course_code": "SURV 2205",
            "course_name": "Civil 3D: Introduction", "course_overview": "Overview.",
            "credits": "3.00", "status": "Active", "source_url": "https://example.test/surv",
            "prerequisite_source": "authoritative_raw_text",
            "prerequisite_text": "Prior CAD experience is required.",
        }, [])
        conversation = [
            {"role": "user", "content": "Tell me about the Civil Engineering program."},
            {"role": "assistant", "content": "Here is the Civil Engineering Bachelor program."},
            {"role": "user", "content": "do you offer civil 3d?"},
            {"role": "assistant", "content": "Yes. SURV 2205 — Civil 3D: Introduction."},
            {"role": "user", "content": "more about this course"},
            {"role": "assistant", "content": "SURV 2205 — Civil 3D: Introduction\n\nOverview.\n\nCredits: 3.00"},
            {"role": "user", "content": "what are the pre requisites of surv2205"},
            {"role": "assistant", "content": "SURV 2205 requires prior CAD experience."},
        ]
        result = answer_student_question(
            "how many credits for this course?", [], conversation=conversation
        )
        self.assertEqual(result["resolved_program"], None)
        self.assertEqual(result["tools_used"], ["get_course_details"])
        self.assertEqual(
            result["answer"],
            "SURV 2205 — Civil 3D: Introduction is worth 3.00 credits.",
        )

    @patch("ai_advisor.find_courses")
    def test_chemistry_search_preserves_display_codes(self, find):
        find.return_value = [
            {"course_id": "CHEM0108", "display_course_code": "CHEM 0108",
             "course_name": "Chemistry 11 Topics Refresher"},
            {"course_id": "FSCT8156", "display_course_code": "FSCT 8156",
             "course_name": "Instrumental Analysis for Forensic Chemistry"},
        ]
        result = execute_tool(
            "search_courses", {"query": "chemistry"}, {"completed_courses": []}
        )
        self.assertEqual(
            [course["display_course_code"] for course in result["courses"]],
            ["CHEM 0108", "FSCT 8156"],
        )

    def test_fresh_next_courses_question_asks_naturally_without_verification(self):
        result = answer_student_question("What can I take next?", [])

        self.assertIn("Which program are you taking?", result["answer"])
        self.assertNotIn("friendly name", result["answer"].lower())
        self.assertEqual(result["tools_used"], [])
        self.assertNotIn("verification", result)

    def test_program_follow_up_keeps_substantive_verification_available(self):
        client = self._advisor_client(
            "get_student_program_advice", {}, "Here are the courses you can take next."
        )

        with patch("ai_advisor.run_advisor_engine") as advisor_engine:
            advisor_engine.return_value = {
                "program_id": "5410DIPLT",
                "program_complete": False,
                "program_progress": {"missing_requirements": []},
                "eligible_courses": [{"course_id": "CIVL1010"}],
                "blocked_courses": [],
            }
            result = answer_student_question(
                "Civil Engineering Diploma",
                [],
                conversation=[
                    {"role": "user", "content": "What can I take next?"},
                    {"role": "assistant", "content": "Which program are you taking?"},
                ],
                client=client,
            )

        self.assertEqual(result["tools_used"], ["get_student_program_advice"])
        self.assertTrue(result["verification"]["exact_count_available"])
        self.assertGreater(result["verification"]["count"], 0)

    @patch("ai_advisor.OpenAI")
    def test_advisor_returns_every_stored_program_url(self, openai_client):
        client = self._advisor_client("search_programs", {"query": "all programs"})
        openai_client.return_value = client
        response = TestClient(app).post(
            "/advisor", json={"question": "Give me the web links for all 374 programs."}
        )
        self.assertEqual(response.status_code, 200)
        answer = response.json()["answer"]
        payload = json.loads(client.responses.requests[1]["input"][0]["output"])
        self.assertEqual(payload["active_program_count"], 374)
        self.assertTrue(all(program["source_url"] for program in payload["programs"]))
        for program in payload["programs"]:
            self.assertIn(program["source_url"], answer)

    @patch("ai_advisor.OpenAI")
    def test_advisor_explicit_program_id_request_returns_all_real_ids(self, openai_client):
        client = self._advisor_client("search_programs", {"query": "all programs"})
        openai_client.return_value = client
        response = TestClient(app).post(
            "/advisor", json={"question": "Give me the IDs for all 4 programs."}
        )
        self.assertEqual(response.status_code, 200)
        answer = response.json()["answer"]
        for program_id in ("0816CM", "8660BENG", "5410DIPLT"):
            self.assertIn(program_id, answer)
        self.assertNotIn("the program", answer.lower())

    def test_course_id_request_is_not_misclassified_as_program_id_request(self):
        from ai_advisor import explicitly_requests_program_ids

        self.assertFalse(explicitly_requests_program_ids(
            "Give me all course IDs and credits for the Civil Engineering bachelor program."
        ))
        self.assertTrue(explicitly_requests_program_ids(
            "Give me the IDs for the 4 programs."
        ))

    @patch("ai_advisor.OpenAI")
    def test_advisor_normal_program_answer_can_still_hide_program_id(self, openai_client):
        client = self._advisor_client(
            "get_program_details", {"program_id": "8660BENG"},
            "Civil Engineering Bachelor of Engineering uses program 8660BENG.",
        )
        openai_client.return_value = client
        response = TestClient(app).post(
            "/advisor", json={"question": "Tell me about the Civil Engineering bachelor program."}
        )
        answer = response.json()["answer"]
        self.assertNotIn("8660BENG", answer)
        self.assertIn("the program", answer)

    @patch("ai_advisor.OpenAI")
    def test_advisor_course_name_is_always_paired_with_course_code(self, openai_client):
        client = self._advisor_client(
            "get_course_details", {"course_id": "CIVL2025"},
            "Applied Hydraulics covers fluid mechanics applications.",
        )
        openai_client.return_value = client
        response = TestClient(app).post(
            "/advisor", json={"question": "Tell me about Applied Hydraulics."}
        )
        self.assertIn("CIVL 2025", response.json()["answer"])
        self.assertIn("Applied Hydraulics", response.json()["answer"])

    @patch("ai_advisor.OpenAI")
    def test_advisor_beng_course_credit_list_uses_enriched_database_values(self, openai_client):
        final_answer = (
            "The list includes CIVL2020 Mechanics of Materials 1 — 6.50 credits, "
            "and CIVL2025 Applied Hydraulics — 5.50 credits."
        )
        client = self._advisor_client(
            "get_program_details", {"program_id": "8660BENG"}, final_answer,
        )
        openai_client.return_value = client
        response = TestClient(app).post("/advisor", json={
            "question": "Give me all course IDs and credits for the Civil Engineering bachelor program."
        })
        self.assertEqual(response.status_code, 200)
        answer = response.json()["answer"]
        payload = json.loads(client.responses.requests[1]["input"][0]["output"])["program"]
        self.assertEqual(len(payload["courses"]), 73)
        courses = {course["course_id"]: course for course in payload["courses"]}
        self.assertEqual(courses["CIVL2025"]["credits"], "5.50")
        self.assertEqual(courses["CIVL2020"]["credits"], "6.50")
        for field in ("course_name", "credits", "source_url", "level", "term",
                      "course_type", "required", "notes"):
            self.assertIn(field, courses["CIVL2025"])
        self.assertIn("CIVL 2025", answer)
        self.assertIn("5.50", answer)
        self.assertNotIn("credits unavailable", answer.lower())
        self.assertNotIn("not available", answer.lower())

    def test_spanish_and_english_missing_level_questions_route_to_progress(self):
        questions = (
            "What do I still need for Level 3?",
            "¿Qué me falta para el nivel 3?",
            "Que necesito para el nivel tres?",
        )
        for question in questions:
            self.assertEqual(classify_intent(question), AdvisorIntent.PROGRAM_PROGRESS)
            self.assertEqual(requested_target_level(question), 3)
        for question in (
            "What do I need to finish Level 6?",
            "What remains to finish level six?",
            "Which requirements are left for Level 6?",
        ):
            self.assertEqual(classify_intent(question), AdvisorIntent.PROGRAM_PROGRESS)

    def test_noisy_spanish_completed_list_is_temporary_conversation_context(self):
        text = (
            "Terminé estas clases (copiado del portal): CIVL-2020 ✓ | CIVL 2024; "
            "CIVL:2025, CIVL_2026 / COMM 2242 y MATH-2422. INVALID 9999"
        )
        courses, added = extract_conversation_completed_courses(text, [], [])
        self.assertEqual(
            set(added),
            {"CIVL2020", "CIVL2024", "CIVL2025", "CIVL2026", "COMM2242", "MATH2422"},
        )
        self.assertEqual({course["course_id"] for course in courses}, set(added))

    def test_have_taken_course_list_is_temporary_conversation_context(self):
        text = "I have taken these courses: CIVL 7001, CIVL 7011, CIVL 7020, CIVL 7022, CIVL 7040"
        courses, added = extract_conversation_completed_courses(text, [], [])
        self.assertEqual(len(courses), 5)
        self.assertEqual(len(added), 5)

    def test_course_in_incomplete_question_is_not_completed(self):
        text = (
            "I haven't completed my 1st year of civil engineering program, "
            "can I take this course? COMM 3342"
        )
        courses, added = extract_conversation_completed_courses(text, [], [])
        self.assertEqual(courses, [])
        self.assertEqual(added, [])
        result = execute_tool(
            "check_course_eligibility",
            {"course_id": "COMM 3342"},
            {"program_id": "8660BENG", "completed_courses": courses},
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["course_id"], "COMM3342")
        self.assertNotIn("completed_courses", result)
        self.assertEqual(result["missing_requirements"][0]["type"], "PROGRAM_LEVEL")

    def test_follow_up_uses_completion_from_temporary_conversation_context(self):
        courses, added = extract_conversation_completed_courses(
            "Can I take the next course?",
            [{"role": "user", "content": "I completed CIVL 7001 last term."}],
            [],
        )
        self.assertEqual(added, ["CIVL7001"])
        self.assertEqual(courses, [{"course_id": "CIVL7001", "grade": None}])

    def test_student_answer_never_mentions_academic_profile(self):
        client = FakeClient([
            SimpleNamespace(
                id="r1", output=[],
                output_text="Your academic profile lists COMM3342 as completed.",
            )
        ])
        result = answer_student_question("Can I take COMM 3342?", [], client=client)
        self.assertNotIn("academic profile", result["answer"].lower())
        self.assertEqual(result.get("error"), "verification_failed")
        self.assertIn("couldn't verify", result["answer"].lower())
        self.assertFalse(result["orchestration"]["answer_released"])

    def test_app_contains_chat_only_and_no_profile_controls(self):
        response = TestClient(app).get("/app")
        self.assertEqual(response.status_code, 200)
        html = response.text.lower()
        self.assertIn('id="chat-form"', html)
        for forbidden in (
            "academic profile", 'id="program"', 'id="courses"', 'id="gpa"',
            'id="hours"', 'id="diploma"',
        ):
            self.assertNotIn(forbidden, html)

    def test_level_three_readiness_returns_exact_missing_level_two_courses(self):
        completed = [
            {"course_id": course_id, "grade": None}
            for course_id in (
                "CIVL2020", "CIVL2024", "CIVL2025", "CIVL2026", "COMM2242", "MATH2422"
            )
        ]
        result = get_student_level_readiness("8660BENG", 3, completed)
        self.assertFalse(result["ready"])
        self.assertEqual(
            [course["course_id"] for course in result["missing_courses"]],
            ["MATH2423", "PHYS2192", "SURV2230"],
        )

    def test_level_ampersand_gets_specific_clarification(self):
        result = answer_student_question(
            "I have 600 hours of work experience, can I move on to level &?", []
        )
        self.assertEqual(result["answer"], "Did you mean Level 7?")
        self.assertEqual(result["tools_used"], [])

    def test_program_website_follow_up_exposes_program_detail_tool(self):
        client = FakeClient([SimpleNamespace(id="r1", output=[], output_text="Program link")])
        answer_student_question(
            "Do you have a website for it?",
            [],
            conversation=[
                {"role": "user", "content": "Tell me about Applied Circular Economy: Zero Waste Buildings."},
                {"role": "assistant", "content": "Applied Circular Economy: Zero Waste Buildings is a microcredential."},
            ],
            client=client,
        )
        tool_names = {tool["name"] for tool in client.responses.requests[0]["tools"]}
        self.assertIn("get_program_details", tool_names)

    def test_paraphrases_route_to_structural_advisor_tools(self):
        for text in ("Which electives can I choose?", "Show me the choice groups"):
            self.assertEqual(classify_intent(text), AdvisorIntent.ELECTIVES)
        for text in ("How much practical work do I need?", "What lets me move to level 7?"):
            self.assertEqual(classify_intent(text), AdvisorIntent.PROGRESSION)
        for text in ("Do you have microcredentials?", "What programs are available?"):
            self.assertEqual(classify_intent(text), AdvisorIntent.PROGRAM_CATEGORY)

    def test_category_discovery_uses_program_credentials(self):
        programs = find_programs("Do you offer any microcredentials?")
        self.assertTrue(programs)
        self.assertTrue(all("microcredential" in p["credential"].lower() for p in programs))
        self.assertGreaterEqual(len(find_programs("What programs are available?")), 3)

    def test_global_catalog_queries_use_all_active_program_records(self):
        questions = (
            "how many programs do you offer?",
            "give me a list of all credentials",
            "give me a list of all programs you offer",
        )
        for question in questions:
            self.assertTrue(is_global_catalog_question(question))
            self.assertEqual(classify_intent(question), AdvisorIntent.PROGRAM_CATEGORY)
            self.assertEqual(len(find_programs(question)), 374)
        self.assertEqual(
            {program["credential"] for program in find_programs(questions[1])},
            {"Associate Certificate", "Advanced Certificate", "Advanced Diploma", "Bachelor's Degree", "Bachelor of Architectural Science", "Bachelor of Business Administration", "Bachelor of Creative Industries", "Bachelor of Engineering", "Bachelor of Environmental Public Health", "Bachelor of Health Science", "Bachelor of Interior Design", "Bachelor of Science", "Bachelor of Science in Nursing", "Bachelor of Technology", "Bachelor of Technology / Bachelor's Degree", "BCIT/Industry Partnership Certificate", "Certificate", "Diploma", "Graduate Certificate", "Master of Applied Science", "Master of Engineering", "Master of Science", "Master of Science / Master's Degree", "Microcredential"},
        )

    def test_nursing_family_list_returns_all_programs_without_resolving_one(self):
        question = "list all nursing programs"
        programs = find_programs(question)

        self.assertTrue(is_program_set_question(question))
        self.assertEqual(classify_intent(question), AdvisorIntent.PROGRAM_CATEGORY)
        self.assertEqual(len(programs), 28)
        self.assertEqual(len({program["program_id"] for program in programs}), 28)
        program_ids = {program["program_id"] for program in programs}
        self.assertTrue({
            "8875BSN", "680XADCERT", "680FASCERT", "680PASCERT", "810GBSN",
        }.issubset(program_ids))
        self.assertTrue(all("nursing" in program["program_name"].lower()
                            for program in programs))
        self.assertIn("Advanced Certificate", {program["credential"] for program in programs})
        names = {program["program_name"] for program in programs}
        self.assertTrue(any("Perinatal - Standard Option" in name for name in names))
        self.assertTrue(any("Specialty Nursing (Perioperative)" in name for name in names))

        context = resolve_academic_context(question, [], None)
        self.assertTrue(context["program_set_query"])
        self.assertIsNone(context["program_id"])
        self.assertIsNone(context["program_name"])

    def test_nursing_family_list_does_not_use_or_change_active_program_context(self):
        question = "can you list all the nursing programs?"
        context = resolve_academic_context(question, [], "5410DIPLT")

        self.assertIsNone(context["program_id"])
        self.assertIsNone(context["program_name"])

        follow_up = resolve_academic_context(
            "How many credits does it have?",
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": "Here are the 12 Specialty Nursing programs."},
            ],
            None,
        )
        self.assertIsNone(follow_up["program_id"])
        self.assertIsNone(follow_up["program_name"])

    def test_nursing_family_answer_has_no_arbitrary_resolved_program(self):
        question = "list all nursing programs"
        client = self._advisor_client(
            "search_programs", {"query": question}, "Here are all 28 nursing programs."
        )
        result = answer_student_question(question, [], client=client)

        payload = result["program_evidence"]
        self.assertEqual(payload["active_program_count"], 28)
        self.assertEqual(len(payload["programs"]), 28)
        self.assertEqual(client.responses.requests, [])
        self.assertEqual(result["resolved_program"], None)
        self.assertNotIn("resolved program", result["answer"].lower())
        self.assertNotIn("total credits", result["answer"].lower())

    def test_nursing_family_delivery_follow_ups_reuse_neutral_set(self):
        conversation = [
            {"role": "user", "content": "how many nursing programs do you offer?"},
            {"role": "assistant", "content": "We offer 28 nursing programs."},
        ]
        cases = (
            ("which ones are online?", 27, {"8875BSN"}),
            ("which are in person?", 1, set()),
            ("which one is full time?", 1, set()),
        )
        for question, matching_count, excluded in cases:
            with self.subTest(question=question):
                context = resolve_academic_context(question, conversation, None)
                self.assertTrue(context["program_set_query"])
                self.assertIsNone(context["program_id"])
                result = compare_programs(question, context["program_set_scope"])
                self.assertEqual(result["program_count"], 28)
                self.assertEqual(len(result["matching_programs"]), matching_count)
                self.assertTrue(excluded.isdisjoint({p["program_id"] for p in result["matching_programs"]}))
        self.assertEqual(
            {p["program_id"] for p in compare_programs("which are in person?", "nursing programs")["matching_programs"]},
            {"8875BSN"},
        )
        self.assertEqual(
            {p["program_id"] for p in compare_programs("which one is full time?", "nursing programs")["matching_programs"]},
            {"8875BSN"},
        )

    def test_family_delivery_follow_up_forces_comparison_without_activating_member(self):
        question = "which ones are online?"
        conversation = [
            {"role": "user", "content": "list all nursing programs"},
            {"role": "assistant", "content": "Here are all 28 nursing programs."},
        ]
        client = self._advisor_client("compare_programs", {"query": question}, "The online programs are listed.")
        result = answer_student_question(question, [], conversation=conversation, client=client)
        self.assertEqual(client.responses.requests[0]["tool_choice"], {"type": "function", "name": "compare_programs"})
        payload = json.loads(client.responses.requests[1]["input"][0]["output"])
        self.assertEqual(payload["program_count"], 28)
        self.assertEqual(len(payload["matching_programs"]), 27)
        self.assertIsNone(result["resolved_program"])

    def test_nursing_international_comparison_checks_all_programs_and_810gbsn(self):
        result = compare_programs("Which nursing programs accept international students?")
        self.assertEqual(result["program_count"], 28)
        self.assertEqual(len(result["programs"]), 28)
        perinatal = next(p for p in result["programs"] if p["program_id"] == "810GBSN")
        self.assertEqual(perinatal["classification"], "conditional/restricted")
        self.assertIn("valid work permit", " ".join(perinatal["evidence"]).lower())

    def test_specialty_nursing_international_comparison_includes_active_certificates(self):
        result = compare_programs("Which Specialty Nursing programs accept international students?")
        self.assertEqual(result["program_count"], 27)
        self.assertNotIn("8875BSN", {p["program_id"] for p in result["programs"]})
        self.assertTrue({"680XADCERT", "680FASCERT"}.issubset(
            {program["program_id"] for program in result["programs"]}
        ))

    def test_full_time_bsn_admissions_scenario_uses_resolved_program_details(self):
        question = (
            "I have English Studies 12 with 78%, a recent Biology 12 course, and I meet the other "
            "academic prerequisites. I’m an international applicant currently living in Canada on "
            "a valid work permit. Can I apply to the full-time Nursing BSN, and what requirements "
            "would still need human or institutional confirmation?"
        )
        client = self._advisor_client(
            "get_program_details", {"program_id": "8875BSN"},
            "The structured admission requirements were evaluated.",
        )
        result = answer_student_question(question, [], client=client)
        self.assertEqual(classify_intent(question), AdvisorIntent.PROGRAM_INFO)
        self.assertEqual(client.responses.requests, [])
        evaluation = result["admission_evaluation"]
        self.assertEqual(evaluation["program_id"], "8875BSN")
        self.assertEqual(evaluation["requirements"]["english"]["status"], "MET")
        self.assertTrue(evaluation["evidence"]["rule_set_ids"])
        self.assertEqual(result["resolved_program"], evaluation["evidence"]["program_name"])

    def test_nursing_english_comparison_evaluates_every_member(self):
        result = compare_programs("Which nursing programs accept English Studies 12 at 72%?")
        self.assertEqual(result["program_count"], 28)
        main = next(p for p in result["programs"] if p["program_id"] == "8875BSN")
        specialty = [p for p in result["programs"]
                     if p["credential"] == "Bachelor of Science in Nursing"
                     and p["program_id"] != "8875BSN"]
        certificates = [p for p in result["programs"]
                        if p["credential"] == "Advanced Certificate"]
        self.assertEqual(main["minimum_value"], 67)
        self.assertEqual(main["classification"], "clearly meets")
        self.assertTrue(all(p["minimum_value"] == 73 for p in specialty))
        self.assertTrue(all(p["difference"] == -1 for p in specialty))
        self.assertEqual(len(certificates), 15)
        self.assertTrue(all(p["classification"] == "unknown" for p in certificates))

    def test_family_comparison_forces_aggregate_tool_without_program_context(self):
        question = "Which nursing programs accept international students?"
        client = self._advisor_client("compare_programs", {"query": question}, "All matching programs were compared.")
        result = answer_student_question(question, [], program_id="5410DIPLT", client=client)
        self.assertEqual(client.responses.requests, [])
        payload = result["program_evidence"]
        self.assertEqual(payload["program_count"], 28)
        self.assertIsNone(result["resolved_program"])

    @patch("ai_advisor.find_programs")
    @patch("ai_advisor.get_program_rules", return_value={"program_id": "X", "rule_sets": []})
    def test_family_comparison_labels_missing_data_unknown(self, _, find):
        find.return_value = [{"program_id": "X", "program_name": "Fixture Business", "credential": "Diploma", "study_mode": "Full-time", "campus": None, "source_url": None}]
        result = compare_programs("Which business programs accept English Studies 12 at 70%?")
        self.assertEqual(result["programs"][0]["classification"], "unknown")

    def test_credential_family_attribute_comparison_routes_as_program_set(self):
        question = "Which diplomas are open to international students?"
        self.assertTrue(is_program_set_question(question))
        self.assertTrue(is_cross_program_comparison(question))
        self.assertEqual(classify_intent(question), AdvisorIntent.PROGRAM_CATEGORY)

    def test_spanish_global_catalog_paraphrases_use_full_catalog(self):
        questions = (
            "¿Cuántos programas ofrecen en BCIT?",
            "¿Qué programas ofrecen?",
            "¿Cuántas carreras ofrecen en BCIT?",
            "lista de programas",
            "Dame una lista de todas las carreras",
        )
        for question in questions:
            with self.subTest(question=question):
                self.assertTrue(is_global_catalog_question(question))
                self.assertEqual(classify_intent(question), AdvisorIntent.PROGRAM_CATEGORY)
                self.assertEqual(len(find_programs(question)), 374)

    def test_current_turn_language_overrides_conversation_language(self):
        cases = (
            (
                "How many programs are offered at BCIT?",
                [{"role": "user", "content": "¿Qué programas ofrecen?"}],
                "English",
            ),
            (
                "¿Cuántos programas ofrecen en BCIT?",
                [{"role": "user", "content": "What programs are available?"}],
                "Spanish",
            ),
        )
        for question, conversation, expected_language in cases:
            with self.subTest(question=question):
                client = self._advisor_client("search_programs", {"query": question})
                result = answer_student_question(question, [], conversation=conversation, client=client)
                self.assertEqual(current_message_language(question), expected_language)
                self.assertEqual(client.responses.requests, [])
                self.assertIn("374", result["answer"])
                if expected_language == "Spanish":
                    self.assertIn("programas activos", result["answer"])
                else:
                    self.assertIn("active programs", result["answer"])

    @patch("ai_advisor.OpenAI")
    def test_general_knowledge_questions_are_declined_without_model_or_tools(self, openai_client):
        for question in ("Do you know who Shakira is?", "Who won the World Cup?"):
            with self.subTest(question=question):
                result = answer_student_question(question, [])
                self.assertEqual(result["intent"], AdvisorIntent.OUT_OF_SCOPE.value)
                self.assertEqual(result["tools_used"], [])
                self.assertIn("BCIT", result["answer"])
        openai_client.assert_not_called()

    def test_bcit_career_question_remains_in_scope(self):
        question = "I'm interested in becoming a structural engineer; what BCIT program should I look at?"
        self.assertFalse(is_out_of_scope_question(question))
        self.assertNotEqual(classify_intent(question), AdvisorIntent.OUT_OF_SCOPE)

    def test_global_catalog_turn_overrides_microcredential_context(self):
        conversation = [
            {"role": "user", "content": "Tell me about the microcredential."},
            {"role": "assistant", "content": "Applied Circular Economy: Zero Waste Buildings."},
        ]
        for question in (
            "how many programs do you offer?",
            "give me a list of all credentials",
            "give me a list of all programs you offer",
        ):
            context = resolve_academic_context(question, conversation, "0816CM")
            self.assertTrue(context["global_catalog"])
            self.assertIsNone(context["program_id"])
            self.assertIsNone(context["program_name"])

    def test_global_catalog_tool_summary_is_derived_from_program_rows(self):
        result = execute_tool(
            "search_programs", {"query": "microcredential"}, {"global_catalog": True}
        )
        self.assertEqual(result["active_program_count"], 374)
        self.assertEqual(len(result["programs"]), 374)
        self.assertEqual(
            set(result["distinct_credentials"]),
            {"Associate Certificate", "Advanced Certificate", "Advanced Diploma", "Bachelor's Degree", "Bachelor of Architectural Science", "Bachelor of Business Administration", "Bachelor of Creative Industries", "Bachelor of Engineering", "Bachelor of Environmental Public Health", "Bachelor of Health Science", "Bachelor of Interior Design", "Bachelor of Science", "Bachelor of Science in Nursing", "Bachelor of Technology", "Bachelor of Technology / Bachelor's Degree", "BCIT/Industry Partnership Certificate", "Certificate", "Diploma", "Graduate Certificate", "Master of Applied Science", "Master of Engineering", "Master of Science", "Master of Science / Master's Degree", "Microcredential"},
        )

    def test_student_ui_builds_safe_clickable_links_without_inner_html(self):
        with open("static/app.js", encoding="utf-8") as source:
            javascript = source.read()
        self.assertIn('document.createElement("a")', javascript)
        self.assertIn("anchor.textContent =", javascript)
        self.assertIn('anchor.rel = "noopener noreferrer"', javascript)
        self.assertNotIn("innerHTML", javascript)

    def test_internal_program_ids_are_hidden_from_students(self):
        self.assertEqual(
            hide_internal_program_ids("You are enrolled in 8660BENG."),
            "You are enrolled in the program.",
        )
        source_url = (
            "https://www.bcit.ca/programs/applied-circular-economy-zero-waste-"
            "buildings-microcredential-part-time-0816cm/"
        )
        self.assertEqual(hide_internal_program_ids(source_url), source_url)

    def test_elective_groups_exclude_work_terms(self):
        groups = get_program_electives("8660BENG")
        self.assertTrue(groups)
        serialized = json.dumps(groups).lower()
        self.assertNotIn("work term", serialized)
        self.assertNotIn("civl5990", serialized)
        self.assertTrue(all(group["choose"] for group in groups))

    @patch("ai_advisor.get_program_curriculum")
    @patch("ai_advisor.get_connection")
    def test_credit_based_elective_pool_is_not_presented_as_choose_n(
        self, get_connection, get_curriculum
    ):
        cursor = get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        get_curriculum.return_value = {
            "components": [{
                "component_name": "Specialization Electives",
                "courses": [
                    {"course_id": "ELEX8010", "credits": "3.0"},
                    {"course_id": "ELEX8285", "credits": "4.0"},
                ],
            }],
            "credit_requirements": [{
                "requirement_name": "Specialization Electives",
                "minimum_credits": "9.0",
                "study_mode": "ALL",
                "allows_external_courses": False,
                "approval_required": False,
                "notes": "9.0 credits required",
            }],
        }

        group = get_program_electives("8900BTECH")[0]
        self.assertEqual(group["type"], "CREDIT_BASED")
        self.assertEqual(group["rule_type"], "MINIMUM_CREDITS_FROM_POOL")
        self.assertEqual(
            group["requirement_text"],
            "Complete at least 9 credits from the approved specialization elective pool.",
        )
        self.assertIsNone(group["course_count"])
        self.assertNotIn("choose", group)
        forbidden = ("choose 3", "three courses", "one option for each 3-credit course needed")
        self.assertTrue(all(phrase not in json.dumps(group).lower() for phrase in forbidden))
        elex_8285 = next(course for course in group["courses"] if course["course_id"] == "ELEX8285")
        self.assertEqual(elex_8285["credits"], "4.0")
        self.assertEqual(group["minimum_credits"], "9.0")

    def test_genuine_choose_n_group_remains_course_count_based(self):
        curriculum = add_credit_requirement_presentations({
            "components": [], "credit_requirements": []
        })
        self.assertEqual(curriculum["credit_requirements"], [])
        group = {"type": "ELECTIVE", "choose": 2, "courses": [{}, {}, {}]}
        self.assertEqual(group["choose"], 2)
        self.assertNotIn("minimum_credits", group)

    def test_progression_returns_practical_work_rules_and_sources(self):
        requirements = get_program_progression_requirements("8660BENG")
        work = [r for r in requirements if r["type"] == "WORK_EXPERIENCE"]
        self.assertEqual([r["value"] for r in work], ["300 hours", "700 hours"])
        self.assertTrue(all(r["source_url"] for r in work))

    def test_program_context_persists_across_natural_follow_up(self):
        context = resolve_academic_context(
            "What electives can I choose?",
            [{"role": "user", "content": "Tell me about the Civil Engineering bachelor."},
             {"role": "assistant", "content": "The Civil Engineering Bachelor of Engineering is active."}],
            None,
        )
        self.assertEqual(context["program_name"], "Civil Engineering Bachelor of Engineering")

    def test_level_four_elective_follow_up_inherits_structured_context(self):
        context = resolve_academic_context(
            "what are the options of the electives?",
            [{"role": "user", "content": "How many electives do I need to choose from the level 4, civil engineering program?"},
             {"role": "assistant", "content": "At Level 4, choose 2 electives."}],
            None,
        )
        self.assertEqual(context["program_name"], "Civil Engineering Bachelor of Engineering")
        self.assertEqual(context["level"], 4)
        self.assertEqual(context["requirement_type"], "electives")
        groups = get_program_electives(context["program_id"], context["level"])
        self.assertEqual(groups[0]["choose"], 2)
        self.assertEqual(
            [course["course_id"] for course in groups[0]["courses"]],
            ["CHEM6020", "CIVL4024", "CIVL4053", "MATH6010"],
        )
        self.assertNotIn("CIVL5990", json.dumps(groups))

    def test_level_six_completion_aggregates_core_choice_and_optional(self):
        completed = [{"course_id": course_id} for course_id in (
            "CIVL7001", "CIVL7011", "CIVL7020", "CIVL7022", "CIVL7040"
        )]
        result = get_student_level_requirements("8660BENG", 6, completed)
        self.assertEqual([item["course_id"] for item in result["missing_required_courses"]],
                         ["CIVL7092"])
        self.assertEqual(result["unsatisfied_choice_groups"][0]["required"], 1)
        self.assertEqual(
            [item["course_id"] for item in result["unsatisfied_choice_groups"][0]["available_options"]],
            ["LIBS7005", "LIBS7007"],
        )
        self.assertEqual([item["course_id"] for item in result["optional_requirements"]],
                         ["CIVL6990"])

    def test_microcredential_details_aggregate_courses_and_source(self):
        programs = find_programs("Applied Circular Economy Zero Waste Buildings")
        details = get_program_details(programs[0]["program_id"])
        self.assertTrue(details["courses"])
        self.assertTrue(details["source_url"])

    def test_microcredential_detail_questions_resolve_and_force_aggregate_tool(self):
        questions = (
            "can you give me more information on the Applied Circular Economy: Zero Waste Buildings microcredential?",
            "Can you provide course names and IDs for the Applied Circular Economy: Zero Waste Buildings microcredential?",
        )
        for question in questions:
            call = SimpleNamespace(
                type="function_call", name="get_program_details",
                arguments='{"program_id":"0816CM"}', call_id="program-details",
            )
            final_answer = (
                "Applied Circular Economy: Zero Waste Buildings includes "
                "XCIR7510 Deconstruction Management, XCIR7520 Design for Disassembly, "
                "and XCIR7530 Construction Material Flows. "
                "https://www.bcit.ca/programs/applied-circular-economy-zero-waste-buildings-microcredential-part-time-0816cm/"
            )
            client = FakeClient([
                SimpleNamespace(id="r1", output=[call], output_text=""),
                SimpleNamespace(id="r2", output=[], output_text=final_answer),
            ])

            result = answer_student_question(question, [], client=client)

            self.assertEqual(result["intent"], "PROGRAM_INFO")
            self.assertEqual(result["resolved_program"], "Applied Circular Economy: Zero Waste Buildings")
            self.assertEqual(result["tools_used"], ["get_program_details"])
            self.assertEqual(
                client.responses.requests[0]["tool_choice"],
                {"type": "function", "name": "get_program_details"},
            )
            tool_payload = json.loads(client.responses.requests[1]["input"][0]["output"])["program"]
            self.assertEqual(
                [(course["course_id"], course["course_name"]) for course in tool_payload["courses"]],
                [
                    ("XCIR7510", "Deconstruction Management"),
                    ("XCIR7520", "Design for Disassembly"),
                    ("XCIR7530", "Construction Material Flows"),
                ],
            )
            self.assertTrue(tool_payload["source_url"])
            for expected in (
                "XCIR7510", "Deconstruction Management", "XCIR7520",
                "Design for Disassembly", "XCIR7530", "Construction Material Flows",
                tool_payload["source_url"],
            ):
                self.assertIn(format_embedded_course_codes(expected), result["answer"])

    def test_microcredential_follow_up_inherits_resolved_program(self):
        conversation = [
            {"role": "user", "content": "can you give me more information on Applied Circular Economy: Zero Waste Buildings?"},
            {"role": "assistant", "content": "Applied Circular Economy: Zero Waste Buildings is the microcredential."},
        ]
        context = resolve_academic_context(
            "Can you provide course names and IDs for Applied Circular Economy: Zero Waste Buildings?",
            conversation,
            None,
        )
        self.assertEqual(context["program_id"], "0816CM")
        self.assertEqual(context["program_name"], "Applied Circular Economy: Zero Waste Buildings")

    @patch("ai_advisor.OpenAI")
    def test_ui_advisor_endpoint_returns_microcredential_details_across_follow_up(
        self, openai_client
    ):
        source_url = (
            "https://www.bcit.ca/programs/applied-circular-economy-zero-waste-"
            "buildings-microcredential-part-time-0816cm/"
        )
        first_answer = (
            "Applied Circular Economy: Zero Waste Buildings includes XCIR7510 "
            "Deconstruction Management, XCIR7520 Design for Disassembly, and "
            f"XCIR7530 Construction Material Flows. {source_url}"
        )
        second_answer = (
            "The courses are XCIR7510 Deconstruction Management, XCIR7520 Design "
            "for Disassembly, and XCIR7530 Construction Material Flows."
        )

        def detail_client(answer, call_id):
            call = SimpleNamespace(
                type="function_call", name="get_program_details",
                arguments='{"program_id":"0816CM"}', call_id=call_id,
            )
            return FakeClient([
                SimpleNamespace(id=f"{call_id}-1", output=[call], output_text=""),
                SimpleNamespace(id=f"{call_id}-2", output=[], output_text=answer),
            ])

        openai_client.side_effect = [
            detail_client(first_answer, "details-first"),
            detail_client(second_answer, "details-follow-up"),
        ]
        http = TestClient(app)
        first_question = "can you give me more information on the microcredential program you offer?"
        first = http.post("/advisor", json={"question": first_question})
        self.assertEqual(first.status_code, 200)
        first_result = first.json()
        follow_up = http.post("/advisor", json={
            "question": "Can you provide course names and IDs for the microcredential program you offer?",
            "conversation": [
                {"role": "user", "content": first_question},
                {"role": "assistant", "content": first_result["answer"]},
            ],
        })
        self.assertEqual(follow_up.status_code, 200)
        follow_up_result = follow_up.json()

        for result in (first_result, follow_up_result):
            self.assertEqual(result["tools_used"], ["get_program_details"])
            for expected in (
                "XCIR7510", "Deconstruction Management", "XCIR7520",
                "Design for Disassembly", "XCIR7530", "Construction Material Flows",
            ):
                self.assertIn(format_embedded_course_codes(expected), result["answer"])
        self.assertIn(source_url, first_result["answer"])

    def test_student_language_routes_to_specific_modes(self):
        self.assertEqual(classify_intent("Hydraulics"), AdvisorIntent.COURSE_INFO)
        self.assertEqual(
            classify_intent("Tell me about the Civil Engineering diploma program"),
            AdvisorIntent.PROGRAM_INFO,
        )
        self.assertEqual(
            classify_intent("What are the prerequisites for Hydraulics?"),
            AdvisorIntent.PREREQUISITES,
        )
        self.assertEqual(
            classify_intent("Can I take Hydraulics next?"),
            AdvisorIntent.ELIGIBILITY_NEXT_COURSES,
        )
        self.assertEqual(
            classify_intent("How much of my program is complete?"),
            AdvisorIntent.PROGRAM_PROGRESS,
        )
        self.assertEqual(
            classify_intent(
                "I just finished all my level two courses, what percentage of the "
                "program am I in, for the whole bachelor degree program?"
            ),
            AdvisorIntent.PROGRAM_PROGRESS,
        )

    def test_hydraulics_info_cannot_invoke_student_progress_tools(self):
        client = FakeClient([SimpleNamespace(id="r1", output=[], output_text="Course info")])

        result = answer_student_question("Hydraulics", [], client=client)

        request = client.responses.requests[0]
        tool_names = {tool["name"] for tool in request["tools"]}
        self.assertEqual(tool_names, {"search_courses", "get_course_details"})
        self.assertNotIn("Completed course count", request["input"])
        self.assertEqual(result["intent"], "COURSE_INFO")

    def test_program_name_query_cannot_invoke_progress_tools_or_request_id(self):
        client = FakeClient([SimpleNamespace(id="r1", output=[], output_text="Program info")])

        result = answer_student_question(
            "Tell me about the Civil Engineering diploma program", [], client=client
        )

        request = client.responses.requests[0]
        tool_names = {tool["name"] for tool in request["tools"]}
        self.assertEqual(
            tool_names,
            {"search_programs", "get_program_details", "get_program_level_courses"},
        )
        self.assertNotIn("Completed course count", request["input"])
        self.assertIn("never ask a student for a program ID", request["instructions"])
        self.assertEqual(result["intent"], "PROGRAM_INFO")

    @patch("ai_advisor.infer_completed_levels")
    @patch("ai_advisor.resolve_civil_engineering_context")
    def test_whole_bachelor_progress_resolves_pathway_and_uses_level_claim(
        self, resolve_context, infer_levels
    ):
        resolve_context.return_value = {
            "program_id": "8660BENG",
            "pathway": {"name": "Civil Engineering"},
        }
        inferred = [{"course_id": "CIVL1012", "grade": None}]
        infer_levels.return_value = (inferred, [1, 2])
        call = SimpleNamespace(
            type="function_call", name="get_student_program_advice",
            arguments="{}", call_id="progress-1",
        )
        client = FakeClient([
            SimpleNamespace(id="r1", output=[call], output_text=""),
            SimpleNamespace(id="r2", output=[], output_text="You have completed 25%."),
        ])

        with patch("ai_advisor.execute_tool", return_value={"completion_percentage": 25}) as tool:
            result = answer_student_question(
                "I just finished all my level two courses, what percentage of the "
                "program am I in, for the whole bachelor degree program?",
                [],
                conversation=[
                    {"role": "user", "content": "Tell me about Civil Engineering."}
                ],
                client=client,
            )

        self.assertEqual(result["intent"], "PROGRAM_PROGRESS")
        self.assertEqual(result["tools_used"], ["get_student_program_advice"])
        context = tool.call_args.args[2]
        self.assertEqual(context["program_id"], "8660BENG")
        self.assertEqual(context["completed_courses"], inferred)
        self.assertIn("through Level 2", client.responses.requests[0]["input"])
        self.assertNotIn("official outline", result["answer"].lower())

    @patch("ai_advisor.resolve_civil_engineering_context")
    def test_shared_level_three_query_lists_courses_without_credential_question(
        self, resolve_context
    ):
        resolve_context.return_value = {
            "program_id": "8660BENG",
            "pathway": {"name": "Civil Engineering"},
        }
        call = SimpleNamespace(
            type="function_call", name="get_program_level_courses",
            arguments='{"level": 3}', call_id="level-3",
        )
        client = FakeClient([
            SimpleNamespace(id="r1", output=[call], output_text=""),
            SimpleNamespace(id="r2", output=[], output_text="Level 3 includes CIVL 3012."),
        ])

        with patch("ai_advisor.execute_tool", return_value={"level": 3, "courses": []}) as tool:
            result = answer_student_question(
                "what are all the level 3 courses for the civil engineering program?",
                [], client=client,
            )

        self.assertEqual(result["intent"], "PROGRAM_INFO")
        self.assertEqual(result["tools_used"], ["get_program_level_courses"])
        self.assertEqual(tool.call_args.args[2]["program_id"], "8660BENG")
        self.assertNotIn("which program", result["answer"].lower())

    def test_course_codes_are_normalized(self):
        self.assertEqual(normalize_course_id("civl 2020"), "CIVL2020")
        self.assertEqual(normalize_course_id("CIVL-2020"), "CIVL2020")

    @patch("ai_advisor.run_advisor_engine")
    @patch("ai_advisor.check_course_eligibility")
    def test_course_eligibility_uses_program_level_and_hides_history(
        self, prerequisite_check, advisor_engine
    ):
        prerequisite_check.return_value = {
            "course_id": "CIVL3012",
            "course_name": "Sustainability in Engineering",
            "eligible": True,
            "completed_courses": [{"course_id": "CIVL1012", "grade": 70}],
            "missing_requirements": [],
        }
        advisor_engine.return_value = {
            "current_level": 1,
            "evaluation_level": 2,
            "eligible_courses": [],
            "blocked_courses": [
                {
                    "course_id": "CIVL3012",
                    "course_name": "Sustainability in Engineering",
                    "missing_requirements": [
                        {"type": "PROGRAM_LEVEL", "required_level": 3}
                    ],
                }
            ],
        }
        context = {
            "program_id": "8660BENG",
            "completed_courses": [{"course_id": "CIVL1012", "grade": 70}],
        }

        result = execute_tool(
            "check_course_eligibility", {"course_id": "CIVL 3012"}, context
        )

        self.assertFalse(result["eligible"])
        self.assertEqual(result["missing_requirements"][0]["type"], "PROGRAM_LEVEL")
        self.assertNotIn("completed_courses", result)
        self.assertNotIn("grade", json.dumps(result))

    @patch("ai_advisor.check_course_eligibility")
    def test_course_eligibility_requires_program_for_full_verdict(
        self, prerequisite_check
    ):
        prerequisite_check.return_value = {
            "course_name": "Example Course",
            "eligible": True,
            "missing_requirements": [],
        }

        result = execute_tool(
            "check_course_eligibility",
            {"course_id": "TEST 1000"},
            {"program_id": None, "completed_courses": []},
        )

        self.assertIsNone(result["eligible"])
        self.assertTrue(result["prerequisites_satisfied"])
        self.assertIn("program", result["message"].lower())

    def test_plain_answer_does_not_send_a_catalog(self):
        client = FakeClient(
            [SimpleNamespace(id="r1", output=[], output_text="Please provide a program.")]
        )

        result = answer_student_question(
            "What can I take next?", [], client=client
        )

        self.assertEqual(client.responses.requests, [])
        self.assertIn("Which program are you taking?", result["answer"])
        self.assertEqual(result["tools_used"], [])

    def test_recent_conversation_is_available_for_follow_up_questions(self):
        client = FakeClient(
            [SimpleNamespace(id="r1", output=[], output_text="It is a core course.")]
        )

        answer_student_question(
            "Is it required?",
            [],
            conversation=[
                {"role": "user", "content": "Tell me about CIVL 2020."},
                {"role": "assistant", "content": "CIVL 2020 is Mechanics of Materials 1."},
            ],
            client=client,
        )

        request_text = client.responses.requests[0]["input"]
        self.assertIn("Recent conversation:", request_text)
        self.assertIn("CIVL 2020", request_text)

    def test_model_can_ask_for_missing_program_without_using_a_tool(self):
        client = FakeClient(
            [
                SimpleNamespace(
                    id="r1",
                    output=[],
                    output_text="Which program are you enrolled in?",
                )
            ]
        )

        result = answer_student_question(
            "What should I take next?", [], client=client
        )

        self.assertEqual(result["tools_used"], [])
        self.assertIn("program", result["answer"].lower())

    @patch("ai_advisor.execute_tool")
    def test_model_can_call_engine_tool_and_receive_structured_output(self, tool):
        tool.return_value = {
            "program_id": "8660BENG",
            "next_courses": [{"course_id": "CIVL2020"}],
        }
        call = SimpleNamespace(
            type="function_call",
            name="get_student_program_advice",
            arguments="{}",
            call_id="call-1",
        )
        client = FakeClient(
            [
                SimpleNamespace(id="r1", output=[call], output_text=""),
                SimpleNamespace(id="r2", output=[], output_text="You can take CIVL 2020."),
            ]
        )

        result = answer_student_question(
            "I finished level 1. What is next?",
            [{"course_id": "CIVL1012", "grade": 75}],
            program_id="8660beng",
            client=client,
        )

        self.assertEqual(result["tools_used"], ["get_student_program_advice"])
        self.assertEqual(result["answer"], "You can take CIVL 2020.")
        tool.assert_called_once()
        context = tool.call_args.args[2]
        self.assertEqual(context["program_id"], "8660BENG")

        follow_up = client.responses.requests[1]
        self.assertEqual(follow_up["previous_response_id"], "r1")
        supplied_result = json.loads(follow_up["input"][0]["output"])
        self.assertEqual(supplied_result["next_courses"][0]["course_id"], "CIVL2020")


if __name__ == "__main__":
    unittest.main(verbosity=2)
