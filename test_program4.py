import unittest

from academic_rules import get_course_requirements, get_program_curriculum, get_program_rules
from ai_advisor import (
    answer_student_question,
    find_programs,
    get_program_details,
    get_program_electives,
    get_program_progression_requirements,
    resolve_academic_context,
)


def flatten_groups(groups):
    for group in groups:
        yield group
        yield from flatten_groups(group.get("children", []))


class Program4RegressionTests(unittest.TestCase):
    PROGRAM_ID = "8800BTECH"

    def test_degree_completion_not_direct_from_high_school(self):
        program = get_program_details(self.PROGRAM_ID)
        self.assertIn("degree-completion", (program["program_overview"] + " " + program["academic_rules"]["rule_sets"][0]["notes"]).lower())
        self.assertTrue(any("Construction Management" in p["program_name"] for p in find_programs("construction management")))

    def test_admission_common_rules_and_all_four_pathways(self):
        rules = get_program_rules(self.PROGRAM_ID, "ADMISSION")["rule_sets"][0]
        self.assertEqual(rules["exact_choice_count"], 1)
        groups = list(flatten_groups(rules["groups"]))
        labels = {g["label"] for g in groups}
        self.assertTrue({"Pathway A", "Pathway B", "Pathway C", "Pathway D"}.issubset(labels))
        descriptions = " ".join(c["description"] for g in groups for c in g["conditions"])
        self.assertIn("pre-entry assessment", descriptions.lower())
        self.assertIn("73%", descriptions)
        self.assertIn("1 year", descriptions)
        self.assertIn("8 years", descriptions)

    def test_red_seal_math_is_one_or_list(self):
        rules = get_program_rules(self.PROGRAM_ID, "ADMISSION")["rule_sets"][0]
        pathway = next(g for g in flatten_groups(rules["groups"]) if g["label"] == "Pathway D")
        math = next(c for c in pathway["conditions"] if c["condition_type"] == "MATH_OPTION_GRADE")
        self.assertEqual(float(math["minimum_value"]), 60)
        self.assertEqual(len(math["accepted_values"]), 5)
        self.assertIn("BLDT 1011", math["accepted_values"])

    def test_management_elective_credit_requirement(self):
        electives = get_program_electives(self.PROGRAM_ID)
        credit_group = next(g for g in electives if g.get("type") == "CREDIT_BASED")
        self.assertEqual(float(credit_group["minimum_credits"]), 4)
        self.assertTrue(credit_group["allows_external_courses"])
        self.assertTrue(credit_group["approval_required"])

    def test_part_time_libs_substitution(self):
        curriculum = get_program_curriculum(self.PROGRAM_ID)
        substitution = curriculum["substitutions"][0]
        self.assertEqual(substitution["study_mode"], "Part-time")
        self.assertEqual(substitution["replaced_course_id"], "LIBS7013")
        self.assertEqual(float(substitution["replacement_credits"]), 3)

    def test_capstone_two_year_experience(self):
        rules = get_program_rules(self.PROGRAM_ID, "CONTINUATION")["rule_sets"][0]
        condition = next(c for g in flatten_groups(rules["groups"]) for c in g["conditions"])
        self.assertEqual(condition["condition_type"], "WORK_EXPERIENCE")
        self.assertEqual(float(condition["minimum_value"]), 2)
        self.assertTrue(condition["parameters"]["admission_experience_counts"])

    def test_cmgt_8700_generalized_conditions(self):
        requirements = get_course_requirements("CMGT8700")
        types = {c["condition_type"] for g in requirements["groups"] for c in g["conditions"]}
        self.assertTrue({"PROGRAM_COURSES_COMPLETE_EXCEPT", "WORK_EXPERIENCE", "INDUSTRY_TOPIC", "INDUSTRY_SPONSOR"}.issubset(types))
        completion = next(
            c for g in requirements["groups"] for c in g["conditions"]
            if c["condition_type"] == "PROGRAM_COURSES_COMPLETE_EXCEPT"
        )
        self.assertEqual(set(completion["parameters"]["except"]), {"CMGT8800", "CMGT8810"})
        self.assertNotIn("except cmgt 8800", completion["description"].lower())

    def test_cmgt_8800_or_8810(self):
        rules = get_program_rules(self.PROGRAM_ID, "COMPLETION")["rule_sets"][0]
        choice = next(g for g in flatten_groups(rules["groups"]) if g["label"] == "Choose one final project")
        self.assertEqual(choice["operator"], "OR")
        self.assertEqual({c["subject_id"] for c in choice["conditions"]}, {"CMGT8800", "CMGT8810"})

    def test_advisor_progression_payload_preserves_final_project_or_group(self):
        payload = get_program_progression_requirements(self.PROGRAM_ID)
        rule_sets = [item for item in payload if item.get("rule_set_id")]
        completion = next(item for item in rule_sets if item["scope"] == "COMPLETION")
        choice = next(g for g in flatten_groups(completion["groups"]) if g["label"] == "Choose one final project")
        self.assertEqual(choice["operator"], "OR")
        self.assertEqual({c["subject_id"] for c in choice["conditions"]}, {"CMGT8800", "CMGT8810"})

    def test_program_admission_is_non_course_condition(self):
        requirements = get_course_requirements("CMGT7211")
        conditions = [c for g in requirements["groups"] for c in g["conditions"]]
        admission = next(c for c in conditions if c["condition_type"] == "PROGRAM_ADMISSION")
        self.assertIsNone(admission["prerequisite_course_id"])
        self.assertEqual(admission["required_program_id"], self.PROGRAM_ID)

    def test_libs_prerequisites_preserve_or_alternatives(self):
        requirements = get_course_requirements("LIBS7001")
        self.assertEqual(requirements["groups"][0]["group_type"], "OR")
        self.assertEqual(
            {c["condition_type"] for c in requirements["groups"][0]["conditions"]},
            {"COURSE", "COMMUNICATION_CREDITS", "POSTSECONDARY_SUBJECT_CREDITS"},
        )

    def test_final_projects_require_department_approval(self):
        for course_id in ("CMGT8800", "CMGT8810"):
            requirements = get_course_requirements(course_id)
            types = {c["condition_type"] for g in requirements["groups"] for c in g["conditions"]}
            self.assertIn("DEPARTMENT_APPROVAL", types)

    def test_program4_paraphrase_resolution(self):
        for phrase in ("Construction Management", "construction management degree", "programa de construction management"):
            self.assertIn(self.PROGRAM_ID, {program["program_id"] for program in find_programs(phrase)})

    def test_btech_credential_synonyms_are_exact_in_fresh_chat(self):
        phrases = (
            "technology programs", "bachelor of technology programs", "BTech programs",
            "B.Tech programs", "technology degrees", "do you offer a BTech?",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                programs = find_programs(phrase)
                self.assertEqual(
                    [p["program_id"] for p in programs],
                    [self.PROGRAM_ID, "8900BTECH", "8120BTECH", "847ABTECH",
                     "847CBTECH", "847BBTECH", "8310BTECH", "8350BTECH"],
                )
                self.assertNotIn("8660BENG", {p["program_id"] for p in programs})

    def test_applicant_credential_mention_does_not_switch_program(self):
        conversation = [{"role": "user", "content": "Tell me about the Construction Management Bachelor of Technology."}]
        for question in (
            "What if my diploma was in civil engineering instead?",
            "Would a Civil Engineering diploma qualify me?",
            "I took a Civil Engineering course; does it count?",
        ):
            with self.subTest(question=question):
                context = resolve_academic_context(question, conversation, None)
                self.assertEqual(context["program_id"], self.PROGRAM_ID)

    def test_explicit_switch_clears_prior_program_topic_and_courses(self):
        conversation = [
            {"role": "user", "content": "Tell me about the Construction Management Bachelor of Technology."},
            {"role": "user", "content": "After CMGT8700, explain CMGT8800 or CMGT8810."},
            {"role": "assistant", "content": "Choose CMGT8800 or CMGT8810."},
        ]
        context = resolve_academic_context(
            "What about the Civil Engineering Bachelor of Engineering?", conversation, None
        )
        self.assertEqual(context["program_id"], "8660BENG")
        self.assertIsNone(context["course_id"])
        self.assertNotEqual(context["requirement_type"], "final_project_options")
        self.assertEqual(context["subject_course_ids"], [])

        switched_conversation = conversation + [
            {"role": "user", "content": "What about the Civil Engineering Bachelor of Engineering?"},
            {"role": "assistant", "content": "Here are the Civil Engineering BEng details."},
        ]
        follow_up = resolve_academic_context(
            "What about the capstone requirements?", switched_conversation, None
        )
        self.assertEqual(follow_up["program_id"], "8660BENG")
        self.assertIsNone(follow_up["course_id"])
        self.assertEqual(follow_up["subject_course_ids"], [])

    def test_final_project_subtopic_persists_for_credit_follow_up(self):
        conversation = [
            {"role": "user", "content": "Tell me about the Construction Management Bachelor of Technology."},
            {"role": "user", "content": "After CMGT8700, do I take both project courses?"},
            {"role": "assistant", "content": "Choose one: CMGT8800 or CMGT8810."},
        ]
        context = resolve_academic_context("How many credits is each option?", conversation, None)
        self.assertEqual(context["program_id"], self.PROGRAM_ID)
        self.assertEqual(context["requirement_type"], "final_project_options")
        self.assertEqual(context["subject_course_ids"], ["CMGT8800", "CMGT8810"])

    def test_cmgt8700_does_not_inherit_department_approval(self):
        requirements = get_course_requirements("CMGT8700")
        types = {c["condition_type"] for g in requirements["groups"] for c in g["conditions"]}
        self.assertNotIn("DEPARTMENT_APPROVAL", types)
        self.assertTrue({"WORK_EXPERIENCE", "INDUSTRY_TOPIC", "INDUSTRY_SPONSOR"}.issubset(types))

    def test_part_time_libs_wording_data_is_non_contradictory(self):
        curriculum = get_program_curriculum(self.PROGRAM_ID)
        libs = next(r for r in curriculum["credit_requirements"] if "liberal" in r["requirement_name"].lower())
        self.assertEqual(float(libs["minimum_credits"]), 12)
        substitution = curriculum["substitutions"][0]
        self.assertEqual(substitution["replaced_course_id"], "LIBS7013")
        self.assertEqual(float(substitution["replacement_credits"]), 3)

    def test_active_program_stays_sticky_for_long_natural_conversation(self):
        follow_ups = (
            "can you do the same, but with credits beside it?",
            "can you give me the list of courses for this program, including the credits for each one?",
            "What are the admission requirements?",
            "I have a business diploma and two years in construction. Can I get in?",
            "Can I enter this program straight from high school?",
            "I'm part-time. What are my Liberal Studies requirements?",
            "What about electives?",
            "How many management elective credits do I need?",
            "What if I'm a Red Seal carpenter?",
            "What math do I need?",
            "What if I'm an electrician?",
            "Do apprenticeship hours count?",
            "Can I do the capstone?",
            "Do I need both final-project courses?",
            "What do I need before CMGT 8700?",
            "I have only 18 months of related work experience. Can I do the final project?",
            "How short am I?",
            "Does my admission experience count?",
            "What does the industry sponsor do?",
            "Can you show the course credits again?",
        )
        conversation = [
            {"role": "user", "content": "Tell me about the Construction Management Bachelor of Technology."},
            {"role": "assistant", "content": "Construction Management is a Bachelor of Technology program."},
        ]
        for question in follow_ups:
            with self.subTest(question=question):
                context = resolve_academic_context(question, conversation, None)
                self.assertEqual(context["program_id"], self.PROGRAM_ID)
                self.assertNotEqual(context["program_id"], "0816CM")
            conversation.extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": "Here is the verified answer."},
            ])

    def test_global_scope_persists_until_explicit_program_switch(self):
        conversation = [
            {"role": "user", "content": "Tell me about the Construction Management Bachelor of Technology."},
            {"role": "assistant", "content": "Construction Management is available."},
            {"role": "user", "content": "How many programs do you offer?"},
            {"role": "assistant", "content": "There are four active programs, including Applied Circular Economy."},
            {"role": "assistant", "content": "An empty fallback lookup returned 0816CM."},
        ]
        catalog = resolve_academic_context("List all programs", conversation, None)
        self.assertTrue(catalog["global_catalog"])
        self.assertIsNone(catalog["program_id"])
        follow_up = resolve_academic_context("What about its electives?", conversation, None)
        self.assertTrue(follow_up["global_catalog"])
        self.assertIsNone(follow_up["program_id"])
        switched = resolve_academic_context("Back to the Construction Management Bachelor of Technology", conversation, None)
        self.assertEqual(switched["program_id"], self.PROGRAM_ID)

    def test_explicit_program_switch_is_sticky(self):
        conversation = [
            {"role": "user", "content": "Tell me about the Construction Management Bachelor of Technology."},
            {"role": "assistant", "content": "Construction Management is available."},
            {"role": "user", "content": "What about Civil Engineering?"},
            {"role": "assistant", "content": "The Civil Engineering pathway has two credentials."},
        ]
        switched = resolve_academic_context("What electives can I take?", conversation, None)
        self.assertIn(switched["program_id"], {"5410DIPLT", "8660BENG"})
        self.assertNotEqual(switched["program_id"], self.PROGRAM_ID)

    def test_credits_follow_up_uses_one_resolved_program_tool(self):
        class Responses:
            def __init__(self):
                self.requests = []

            def create(self, **kwargs):
                self.requests.append(kwargs)
                if len(self.requests) == 1:
                    from types import SimpleNamespace
                    import json
                    call = SimpleNamespace(
                        type="function_call", name="get_program_details",
                        arguments=json.dumps({"program_id": "0816CM"}), call_id="details",
                    )
                    return SimpleNamespace(id="r1", output=[call], output_text="")
                from types import SimpleNamespace
                return SimpleNamespace(id="r2", output=[], output_text="Construction Management credits.")

        class Client:
            def __init__(self):
                self.responses = Responses()

        client = Client()
        result = answer_student_question(
            "can you do the same, but with credits beside it?", [],
            conversation=[{"role": "user", "content": "List Construction Management Bachelor of Technology courses."}],
            client=client,
        )
        self.assertEqual(result["resolved_program"], "Construction Management")
        self.assertEqual(result["tools_used"], ["get_program_details"])
        self.assertEqual(len(client.responses.requests), 2)
        payload = client.responses.requests[1]["input"][0]["output"]
        self.assertIn("8800BTECH", payload)
        self.assertNotIn("0816CM", payload)


if __name__ == "__main__":
    unittest.main()
