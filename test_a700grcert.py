import unittest
from academic_rules import get_course_requirements,get_program_curriculum,get_program_rules
from ai_advisor import find_programs,get_program_details,get_program_progression_requirements,resolve_academic_context
from database import get_connection
from eligibility import check_course_eligibility

class BusinessAdministrationGraduateCertificateTests(unittest.TestCase):
    PROGRAM_ID="A700GRCERT"
    def test_identity_routing_and_credential_family(self):
        details=get_program_details(self.PROGRAM_ID)
        self.assertEqual((details["program_name"],details["credential"]),("Business Administration","Graduate Certificate")); self.assertEqual(details["study_mode"],"Full-time"); self.assertIn("Vancouver",details["campus"])
        for query in ("Business Administration Graduate Certificate","graduate business certificate","business admin grad certificate"):
            self.assertEqual([p["program_id"] for p in find_programs(query)],[self.PROGRAM_ID])
        self.assertEqual(
            [p["program_id"] for p in find_programs("graduate certificate programs")],
            ["A200GRCERT", self.PROGRAM_ID, "A600GRCERT", "A500GRCERT"],
        )
    def test_admissions_and_international_rules(self):
        admissions=get_program_rules(self.PROGRAM_ID,"ADMISSION")["rule_sets"]; conditions=[c for r in admissions for g in r["groups"] for c in g["conditions"]]; by_type={c["condition_type"]:c for c in conditions}
        self.assertTrue(by_type["PRIOR_DEGREE"]["parameters"]["executable"]); self.assertEqual(by_type["ENGLISH_GRADE"]["minimum_value"],67)
        international=get_program_rules(self.PROGRAM_ID,"INTERNATIONAL")["rule_sets"]
        self.assertTrue(any("not PGWP eligible" in (r["notes"] or "") for r in international)); self.assertTrue(any(c["condition_type"]=="INTERNATIONAL_CREDENTIAL_EVALUATION" for r in international for g in r["groups"] for c in g["conditions"]))
    def test_complete_matrix_and_capstone_prerequisites(self):
        curriculum=get_program_curriculum(self.PROGRAM_ID); self.assertEqual({c["component_name"] for c in curriculum["components"]},{"Term 1 (15 weeks)","Term 2 (20 weeks)"})
        self.assertEqual({course["course_id"] for comp in curriculum["components"] for course in comp["courses"]},{"ECON9100","FMGT9152","MKTG9120","FMGT9260","GLBL9200","OPMT9170"})
        reqs=get_course_requirements("GLBL9200")["groups"][0]["conditions"]; self.assertEqual({(r["prerequisite_course_id"],float(r["minimum_grade"])) for r in reqs},{("ECON9100",60.0),("FMGT9152",60.0),("MKTG9120",60.0)})
        result=check_course_eligibility("GLBL9200",[{"course_id":"ECON9100","grade":60},{"course_id":"FMGT9152","grade":59},{"course_id":"MKTG9120","grade":70}],self.PROGRAM_ID); self.assertFalse(result["eligible"])
    def test_progression_completion_and_context_switching(self):
        progression=get_program_progression_requirements(self.PROGRAM_ID); self.assertTrue(any(r.get("type")=="PROGRAM_COURSE_GRADE" and "60%" in r["description"] for r in progression)); self.assertTrue(get_program_rules(self.PROGRAM_ID,"COMPLETION")["rule_sets"])
        conversation=[{"role":"user","content":"Tell me about Applied Computing MSc"},{"role":"assistant","content":"It is a master's program."}]
        self.assertEqual(resolve_academic_context("What about the graduate business certificate?",conversation,"M600MSC")["program_id"],self.PROGRAM_ID)
        reverse=[{"role":"user","content":"Tell me about the graduate business certificate"},{"role":"assistant","content":"It is a graduate certificate."}]
        self.assertEqual(resolve_academic_context("Switch to Applied Computing MSc",reverse,self.PROGRAM_ID)["program_id"],"M600MSC")
    def test_governed_revision_is_active_and_exact_hash_approved(self):
        with get_connection() as connection,connection.cursor() as cursor:
            cursor.execute("SELECT r.payload_sha256,r.lifecycle_status,a.approval_status FROM program_active_import_revisions ar JOIN program_import_revisions r USING(revision_id) JOIN program_import_approvals a ON a.program_id=r.program_id AND a.payload_sha256=r.payload_sha256 WHERE ar.program_id=%s",(self.PROGRAM_ID,)); payload_hash,status,approval=cursor.fetchone()
        self.assertEqual((len(payload_hash),status,approval),(64,"active","approved"))

if __name__=="__main__": unittest.main()
