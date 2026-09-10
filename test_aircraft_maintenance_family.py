import unittest
from academic_rules import get_program_rules
from ai_advisor import compare_programs, find_programs, get_program_details, resolve_academic_context
from database import get_connection

IDS={"1165DIPMA","1230DIPMA","1205DIPMA"}
class AircraftMaintenanceFamilyTests(unittest.TestCase):
    def test_three_program_family_listing_is_neutral(self):
        self.assertEqual({p["program_id"] for p in find_programs("show me all aircraft maintenance engineer programs")},IDS)
    def test_specialty_aliases_are_isolated(self):
        cases={"aircraft maintenance electronics":"1165DIPMA","category E aircraft maintenance":"1165DIPMA","maintenance category M":"1230DIPMA","structures aircraft maintenance":"1205DIPMA"}
        for query,pid in cases.items(): self.assertEqual([p["program_id"] for p in find_programs(query)],[pid])
    def test_identity_delivery_and_curriculum_are_independent(self):
        expected={"1165DIPMA":18,"1230DIPMA":22,"1205DIPMA":20}
        for pid,count in expected.items():
            details=get_program_details(pid); self.assertEqual(details["credential"],"Diploma"); self.assertEqual(details["study_mode"],"Full-time"); self.assertIn("Richmond",details["campus"]); self.assertEqual(len(details["courses"]),count)
    def test_regulatory_practical_and_attendance_rules(self):
        for pid in IDS:
            self.assertTrue(get_program_rules(pid,"REGULATORY")["rule_sets"])
            progression=get_program_rules(pid,"PROGRESSION")["rule_sets"]
            values={float(c["minimum_value"]) for rule in progression for g in rule["groups"] for c in g["conditions"] if c["minimum_value"] is not None}
            self.assertIn(70.0,values)
            attendance=get_program_rules(pid,"ATTENDANCE")["rule_sets"][0]
            self.assertIn("95%",attendance["notes"])
    def test_admissions_and_context_switching(self):
        for pid in IDS: self.assertTrue(get_program_rules(pid,"ADMISSION")["rule_sets"])
        e=resolve_academic_context("category E aircraft maintenance",[],None); self.assertEqual(e["program_id"],"1165DIPMA")
        m=resolve_academic_context("switch to maintenance category M",[],e["program_id"]); self.assertEqual(m["program_id"],"1230DIPMA")
        s=resolve_academic_context("now structures aircraft maintenance",[],m["program_id"]); self.assertEqual(s["program_id"],"1205DIPMA")
    def test_governed_revisions_are_active_and_approved(self):
        with get_connection() as c,c.cursor() as q:
            q.execute("SELECT r.program_id,r.lifecycle_status,a.approval_status FROM program_import_revisions r JOIN program_active_import_revisions x USING(revision_id) JOIN program_import_approvals a ON a.program_id=r.program_id AND a.payload_sha256=r.payload_sha256 WHERE r.program_id=ANY(%s)",(list(IDS),))
            rows=q.fetchall()
        self.assertEqual({r[0] for r in rows},IDS); self.assertTrue(all(r[1:]==("active","approved") for r in rows))
    def test_family_delivery_comparison(self):
        result=compare_programs("compare aircraft maintenance program delivery","aircraft_maintenance_engineer")
        self.assertEqual({p["program_id"] for p in result["programs"]},IDS)

if __name__ == '__main__': unittest.main()
