from collections import defaultdict

from database import get_connection


def get_program_curriculum(program_id):
    program_id = program_id.upper()
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT cc.component_id, cc.component_name, cc.component_order,
                   cc.required_credits, cc.notes, ccc.course_role,
                   ccc.study_mode, c.course_id, c.course_name, c.credits,
                   c.source_url, c.institution_key, c.native_course_code
            FROM curriculum_components cc
            LEFT JOIN curriculum_component_courses ccc USING (component_id)
            LEFT JOIN courses c ON c.course_id = ccc.course_id
            WHERE cc.program_id = %s
            ORDER BY cc.component_order, ccc.course_role, c.course_id
            """,
            (program_id,),
        )
        rows = cursor.fetchall()
        cursor.execute(
            """
            SELECT requirement_name, minimum_credits, study_mode,
                   allows_external_courses, approval_required, notes
            FROM credit_requirements WHERE program_id = %s
            ORDER BY requirement_name
            """,
            (program_id,),
        )
        credit_requirements = [
            dict(zip(("requirement_name", "minimum_credits", "study_mode",
                      "allows_external_courses", "approval_required", "notes"), row))
            for row in cursor.fetchall()
        ]
        cursor.execute(
            """
            SELECT study_mode, replaced_course_id, replacement_type,
                   replacement_credits, description
            FROM curriculum_substitutions WHERE program_id = %s
            ORDER BY study_mode, replaced_course_id
            """,
            (program_id,),
        )
        substitutions = [
            dict(zip(("study_mode", "replaced_course_id", "replacement_type",
                      "replacement_credits", "description"), row))
            for row in cursor.fetchall()
        ]
        cursor.execute(
            """
            SELECT r.component_id, rc.course_id, r.requirement_code,
                   r.minimum_credits, r.exact_course_count, r.description,
                   r.institution_key
            FROM curriculum_requirements r
            JOIN curriculum_requirement_courses rc USING(curriculum_requirement_id)
            WHERE r.program_id = %s
              AND LOWER(r.requirement_type) IN
                  ('alternative_courses', 'alternative_path', 'any_of', 'or')
            """,
            (program_id,),
        )
        required_alternatives = {
            row[1]: {
                "requirement_code": row[2], "minimum_credits": row[3],
                "exact_course_count": row[4], "description": row[5],
                "institution_key": row[6], "required": True,
                "individual_option_mandatory": False,
            }
            for row in cursor.fetchall()
        }
        cursor.execute(
            """
            SELECT r.requirement_code, r.requirement_type, r.minimum_credits,
                   r.exact_course_count, r.double_count_prohibited,
                   r.parent_requirement_code, r.executable, r.verification_method, r.description,
                   r.institution_key, r.parameters, r.source_url, r.sort_order,
                   ARRAY_REMOVE(ARRAY_AGG(rc.course_id ORDER BY rc.course_id), NULL)
            FROM curriculum_requirements r
            LEFT JOIN curriculum_requirement_courses rc USING(curriculum_requirement_id)
            WHERE r.program_id = %s
            GROUP BY r.curriculum_requirement_id
            ORDER BY r.sort_order, r.requirement_code
            """,
            (program_id,),
        )
        requirements = [
            dict(zip((
                "requirement_code", "requirement_type", "minimum_credits",
                "exact_course_count", "double_count_prohibited", "parent_requirement_code",
                "executable", "verification_method", "description", "institution_key",
                "parameters", "source_url", "sort_order", "course_ids",
            ), row))
            for row in cursor.fetchall()
        ]
    components = {}
    for row in rows:
        component = components.setdefault(row[0], {
            "component_id": row[0], "component_name": row[1],
            "component_order": row[2], "required_credits": row[3],
            "notes": row[4], "courses": [],
        })
        if row[7]:
            course = {
                "course_role": row[5], "study_mode": row[6],
                "course_id": row[7], "course_name": row[8],
                "credits": row[9], "source_url": row[10],
                "institution_key": row[11], "native_course_code": row[12],
            }
            alternative = required_alternatives.get(row[7])
            if alternative:
                course["course_role"] = "REQUIRED_ALTERNATIVE"
                course["alternative_requirement"] = alternative
            component["courses"].append(course)
    return {"program_id": program_id, "components": list(components.values()),
            "requirements": requirements,
            "credit_requirements": credit_requirements,
            "substitutions": substitutions}


def get_program_rules(program_id, scope=None):
    program_id = program_id.upper()
    params = [program_id]
    scope_clause = ""
    if scope:
        scope_clause = " AND ars.rule_scope = %s"
        params.append(scope.upper())
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT ars.rule_set_id, ars.rule_scope, ars.rule_name,
                   ars.study_mode, ars.exact_choice_count, ars.notes,
                   arg.rule_group_id, arg.parent_group_id, arg.operator,
                   arg.label, arg.sort_order, arc.condition_id,
                   arc.condition_type, arc.subject_id, arc.minimum_value,
                   arc.unit, arc.accepted_values, arc.parameters,
                   arc.description, arc.sort_order
            FROM academic_rule_sets ars
            LEFT JOIN academic_rule_groups arg USING (rule_set_id)
            LEFT JOIN academic_rule_conditions arc USING (rule_group_id)
            WHERE ars.program_id = %s {scope_clause}
            ORDER BY ars.rule_scope, ars.rule_set_id, arg.sort_order,
                     arg.rule_group_id, arc.sort_order, arc.condition_id
            """,
            params,
        )
        rows = cursor.fetchall()
    sets = {}
    for row in rows:
        rule_set = sets.setdefault(row[0], {
            "rule_set_id": row[0], "scope": row[1], "name": row[2],
            "study_mode": row[3], "exact_choice_count": row[4],
            "notes": row[5], "groups": {},
        })
        if row[6] is None:
            continue
        group = rule_set["groups"].setdefault(row[6], {
            "rule_group_id": row[6], "parent_group_id": row[7],
            "operator": row[8], "label": row[9], "sort_order": row[10],
            "conditions": [], "children": [],
        })
        if row[11] is not None:
            group["conditions"].append({
                "condition_id": row[11], "condition_type": row[12],
                "subject_id": row[13], "minimum_value": row[14],
                "unit": row[15], "accepted_values": row[16],
                "parameters": row[17], "description": row[18],
                "sort_order": row[19],
            })
    result = []
    for rule_set in sets.values():
        groups = rule_set.pop("groups")
        roots = []
        for group in groups.values():
            parent = groups.get(group["parent_group_id"])
            (parent["children"] if parent else roots).append(group)
        rule_set["groups"] = roots
        result.append(rule_set)
    return {"program_id": program_id, "rule_sets": result}


def get_course_requirements(course_id):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT pg.prerequisite_group_id, pg.group_type,
                   pc.prerequisite_course_id, pc.minimum_grade,
                   pc.required_program_id, pc.condition_type,
                   pc.parameters, COALESCE(pc.description, pc.notes)
            FROM prerequisite_groups pg
            JOIN prerequisite_conditions pc USING (prerequisite_group_id)
            WHERE pg.course_id = %s
            ORDER BY pg.prerequisite_group_id, pc.prerequisite_condition_id
            """,
            (course_id.upper(),),
        )
        rows = cursor.fetchall()
    groups = defaultdict(lambda: {"group_type": None, "conditions": []})
    for row in rows:
        groups[row[0]]["group_type"] = row[1]
        groups[row[0]]["conditions"].append({
            "prerequisite_course_id": row[2], "minimum_grade": row[3],
            "required_program_id": row[4], "condition_type": row[5],
            "parameters": row[6], "description": row[7],
        })
    return {"course_id": course_id.upper(), "groups": list(groups.values())}
