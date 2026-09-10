"""Generalized clinical-placement and practice-hour requirement support."""

from database import get_connection


def get_nursing_requirements(program_id):
    """Return structured nursing requirements without treating them as courses."""
    program_id = program_id.upper()
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT requirement_code, requirement_name, requirement_type,
                   applies_to, executable, verification_method, description,
                   source_url, parameters
            FROM clinical_placement_requirements
            WHERE program_id = %s ORDER BY sort_order, requirement_code
            """,
            (program_id,),
        )
        clinical = [dict(zip((
            "requirement_code", "requirement_name", "requirement_type",
            "applies_to", "executable", "verification_method", "description",
            "source_url", "parameters",
        ), row)) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT requirement_code, requirement_name, required_hours,
                   tracking_scope, executable, verification_method, description,
                   source_url, parameters
            FROM practice_hour_requirements
            WHERE program_id = %s ORDER BY sort_order, requirement_code
            """,
            (program_id,),
        )
        practice = [dict(zip((
            "requirement_code", "requirement_name", "required_hours",
            "tracking_scope", "executable", "verification_method", "description",
            "source_url", "parameters",
        ), row)) for row in cursor.fetchall()]
    return {"program_id": program_id, "clinical_placement": clinical, "practice_hours": practice}


def assess_nursing_requirements(program_id, evidence=None, practice_hours=None):
    """Classify requirements as met, missing, or requiring human confirmation.

    Only requirements explicitly marked executable are automatically evaluated.
    Unknown evidence is never interpreted as failure for a human-verified rule.
    """
    evidence = {str(key).upper(): value for key, value in (evidence or {}).items()}
    practice_hours = {str(key).upper(): value for key, value in (practice_hours or {}).items()}
    requirements = get_nursing_requirements(program_id)
    result = {"met": [], "missing": [], "human_confirmation": []}
    for requirement in requirements["clinical_placement"]:
        code = requirement["requirement_code"].upper()
        item = {**requirement, "category": "CLINICAL_PLACEMENT"}
        if not requirement["executable"] or requirement["verification_method"] == "HUMAN_CONFIRMATION":
            item["provided_evidence"] = evidence.get(code)
            result["human_confirmation"].append(item)
        elif evidence.get(code) is True:
            result["met"].append(item)
        else:
            result["missing"].append(item)
    for requirement in requirements["practice_hours"]:
        code = requirement["requirement_code"].upper()
        completed = practice_hours.get(code)
        item = {**requirement, "category": "PRACTICE_HOURS", "completed_hours": completed}
        if not requirement["executable"] or requirement["required_hours"] is None:
            result["human_confirmation"].append(item)
        elif completed is not None and float(completed) >= float(requirement["required_hours"]):
            result["met"].append(item)
        else:
            result["missing"].append(item)
    result.update({
        "program_id": program_id.upper(),
        "eligible": not result["missing"] and not result["human_confirmation"],
        "academic_prerequisites_evaluated_separately": True,
    })
    return result


def assess_nursing_applicant(program_id, academic_evidence=None, clinical_evidence=None, practice_hours=None):
    """Combine cleanly executable admission facts with non-course nursing gates."""
    from academic_rules import get_program_rules

    supplied = {str(key).upper(): value for key, value in (academic_evidence or {}).items()}
    result = {"met": [], "missing": [], "human_confirmation": []}
    rules = get_program_rules(program_id, "ADMISSION")["rule_sets"]
    for rule_set in rules:
        for group in rule_set["groups"]:
            for condition in group["conditions"]:
                item = {**condition, "category": "ACADEMIC_ADMISSION"}
                parameters = condition.get("parameters") or {}
                subject = str(condition.get("subject_id") or "").upper()
                value = supplied.get(subject)
                if not parameters.get("executable", False):
                    item["provided_evidence"] = value
                    result["human_confirmation"].append(item)
                elif condition["condition_type"] == "GRADE":
                    (result["met"] if value is not None and float(value) >= float(condition["minimum_value"]) else result["missing"]).append(item)
                elif condition["condition_type"] == "CREDENTIAL":
                    (result["met"] if value is True else result["missing"]).append(item)
                elif condition["condition_type"] == "WORK_EXPERIENCE":
                    (result["met"] if value is not None and float(value) >= float(condition["minimum_value"]) else result["missing"]).append(item)
                else:
                    result["human_confirmation"].append(item)
    nursing = assess_nursing_requirements(program_id, clinical_evidence, practice_hours)
    for bucket in ("met", "missing", "human_confirmation"):
        result[bucket].extend(nursing[bucket])
    result.update({
        "program_id": program_id.upper(),
        "eligible": not result["missing"] and not result["human_confirmation"],
        "academic_and_non_course_separated": True,
    })
    return result
