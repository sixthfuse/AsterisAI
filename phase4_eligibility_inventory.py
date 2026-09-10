"""Read-only inventory of admission eligibility rules for Advisor V2 Phase 4."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from database import get_connection


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def collect() -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM programs WHERE status = 'Active'")
            active_programs = cursor.fetchone()[0]
            cursor.execute(
                """SELECT COUNT(DISTINCT program_id), COUNT(*)
                   FROM academic_rule_sets WHERE rule_scope = 'ADMISSION'"""
            )
            governed_programs, rule_sets = cursor.fetchone()
            cursor.execute(
                """SELECT ars.program_id, p.program_name, ars.rule_set_id,
                          ars.rule_name, ars.study_mode, ars.exact_choice_count,
                          arg.rule_group_id, arg.parent_group_id, arg.operator, arg.label,
                          arc.condition_id, arc.condition_type, arc.subject_id,
                          arc.minimum_value, arc.unit, arc.accepted_values,
                          arc.parameters, arc.description
                   FROM academic_rule_sets ars
                   JOIN programs p USING (program_id)
                   LEFT JOIN academic_rule_groups arg USING (rule_set_id)
                   LEFT JOIN academic_rule_conditions arc USING (rule_group_id)
                   WHERE ars.rule_scope = 'ADMISSION'
                   ORDER BY ars.program_id, ars.rule_set_id, arg.sort_order,
                            arg.rule_group_id, arc.sort_order, arc.condition_id"""
            )
            rows = cursor.fetchall()
            cursor.execute(
                """SELECT pg.group_type, pc.condition_type, COUNT(*),
                          COUNT(DISTINCT pg.course_id)
                   FROM prerequisite_groups pg
                   JOIN prerequisite_conditions pc USING (prerequisite_group_id)
                   GROUP BY pg.group_type, pc.condition_type
                   ORDER BY COUNT(*) DESC"""
            )
            prerequisite_types = cursor.fetchall()
            cursor.execute(
                """SELECT rule_scope, COUNT(*), COUNT(DISTINCT program_id)
                   FROM academic_rule_sets GROUP BY rule_scope ORDER BY rule_scope"""
            )
            rule_scopes = cursor.fetchall()
            cursor.execute(
                """SELECT COALESCE(study_mode, '<NULL>'), COUNT(*), COUNT(DISTINCT program_id)
                   FROM academic_rule_sets WHERE rule_scope = 'ADMISSION'
                   GROUP BY study_mode ORDER BY COUNT(*) DESC"""
            )
            admission_study_modes = cursor.fetchall()
            cursor.execute(
                """SELECT COALESCE(international_eligibility::text, '<NULL>'), COUNT(*)
                   FROM program_delivery_facts GROUP BY international_eligibility
                   ORDER BY COUNT(*) DESC"""
            )
            international_delivery_states = cursor.fetchall()
            cursor.execute(
                """SELECT ars.rule_scope, arc.condition_type, COUNT(*),
                          COUNT(DISTINCT ars.program_id)
                   FROM academic_rule_sets ars
                   JOIN academic_rule_groups arg USING(rule_set_id)
                   JOIN academic_rule_conditions arc USING(rule_group_id)
                   GROUP BY ars.rule_scope, arc.condition_type
                   ORDER BY ars.rule_scope, COUNT(*) DESC, arc.condition_type"""
            )
            scoped_condition_types = cursor.fetchall()
            cursor.execute(
                """SELECT COUNT(*) FILTER (WHERE minimum_grade IS NOT NULL),
                          COUNT(DISTINCT pg.course_id) FILTER (WHERE minimum_grade IS NOT NULL)
                   FROM prerequisite_groups pg
                   JOIN prerequisite_conditions pc USING(prerequisite_group_id)"""
            )
            prerequisite_minimum_grades = cursor.fetchone()
            cursor.execute(
                """SELECT table_name FROM information_schema.tables
                   WHERE table_schema = 'public' AND
                         (table_name ILIKE '%progress%' OR table_name ILIKE '%campus%'
                          OR table_name ILIKE '%delivery%' OR table_name ILIKE '%prereq%')
                   ORDER BY table_name"""
            )
            related_tables = [row[0] for row in cursor.fetchall()]
            table_summaries = {}
            for table_name in related_tables:
                cursor.execute(
                    """SELECT column_name FROM information_schema.columns
                       WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position""",
                    (table_name,),
                )
                columns = [row[0] for row in cursor.fetchall()]
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                table_summaries[table_name] = {"row_count": cursor.fetchone()[0], "columns": columns}

    condition_counts: Counter[str] = Counter()
    condition_programs: dict[str, set[str]] = defaultdict(set)
    operator_counts: Counter[str] = Counter()
    operator_programs: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    nested_programs: set[str] = set()
    program_types: dict[str, set[str]] = defaultdict(set)
    program_names: dict[str, str] = {}
    seen_groups: set[str] = set()
    seen_conditions: set[str] = set()
    parameter_keys: Counter[str] = Counter()

    for row in rows:
        (program_id, program_name, rule_set_id, rule_name, study_mode,
         exact_choice_count, group_id, parent_group_id, operator, label,
         condition_id, condition_type, subject_id, minimum_value, unit,
         accepted_values, parameters, description) = row
        program_names[program_id] = program_name
        if group_id and group_id not in seen_groups:
            seen_groups.add(group_id)
            op = (operator or "<NULL>").upper()
            operator_counts[op] += 1
            operator_programs[op].add(program_id)
            if parent_group_id:
                nested_programs.add(program_id)
        if condition_id and condition_id not in seen_conditions:
            seen_conditions.add(condition_id)
            kind = (condition_type or "<NULL>").upper()
            condition_counts[kind] += 1
            condition_programs[kind].add(program_id)
            program_types[program_id].add(kind)
            for key in (parameters or {}):
                parameter_keys[str(key)] += 1
            if len(examples[kind]) < 4:
                examples[kind].append(json_value({
                    "program_id": program_id, "program_name": program_name,
                    "rule_set_id": rule_set_id, "rule_name": rule_name,
                    "study_mode": study_mode, "exact_choice_count": exact_choice_count,
                    "group_operator": operator, "group_label": label,
                    "condition_id": condition_id, "subject_id": subject_id,
                    "minimum_value": minimum_value, "unit": unit,
                    "accepted_values": accepted_values, "parameters": parameters,
                    "description": description,
                }))

    combinations = Counter(tuple(sorted(types)) for types in program_types.values())
    combination_examples: list[dict[str, Any]] = []
    for combo, count in combinations.most_common():
        matching = [pid for pid, types in program_types.items() if tuple(sorted(types)) == combo][:5]
        combination_examples.append({
            "condition_types": list(combo), "program_count": count,
            "examples": [{"program_id": pid, "program_name": program_names[pid]} for pid in matching],
        })

    return json_value({
        "transaction_mode": "PostgreSQL SET TRANSACTION READ ONLY",
        "active_program_count": active_programs,
        "governed_admission_program_count": governed_programs,
        "admission_rule_set_count": rule_sets,
        "admission_group_count": len(seen_groups),
        "admission_condition_count": len(seen_conditions),
        "condition_types": [
            {"condition_type": kind, "condition_count": count,
             "program_count": len(condition_programs[kind]), "examples": examples[kind]}
            for kind, count in condition_counts.most_common()
        ],
        "group_operators": [
            {"operator": op, "group_count": count, "program_count": len(operator_programs[op])}
            for op, count in operator_counts.most_common()
        ],
        "programs_with_nested_groups": len(nested_programs),
        "nested_group_examples": [
            {"program_id": pid, "program_name": program_names[pid]} for pid in sorted(nested_programs)[:20]
        ],
        "parameter_keys": dict(parameter_keys.most_common()),
        "condition_type_combinations": combination_examples,
        "course_prerequisite_inventory": [
            {"group_type": group_type, "condition_type": condition_type,
             "condition_count": count, "course_count": course_count}
            for group_type, condition_type, count, course_count in prerequisite_types
        ],
        "academic_rule_scopes": [
            {"scope": scope, "rule_set_count": count, "program_count": programs}
            for scope, count, programs in rule_scopes
        ],
        "admission_rule_study_modes": [
            {"study_mode": mode, "rule_set_count": count, "program_count": programs}
            for mode, count, programs in admission_study_modes
        ],
        "program_delivery_international_states": [
            {"international_eligibility": state, "program_count": count}
            for state, count in international_delivery_states
        ],
        "scoped_condition_types": [
            {"scope": scope, "condition_type": kind, "condition_count": count,
             "program_count": programs}
            for scope, kind, count, programs in scoped_condition_types
        ],
        "prerequisite_minimum_grade_conditions": prerequisite_minimum_grades[0],
        "courses_with_minimum_grade_prerequisites": prerequisite_minimum_grades[1],
        "related_tables": related_tables,
        "related_table_summaries": table_summaries,
    })


if __name__ == "__main__":
    result = collect()
    output = Path("outputs") / "phase4_eligibility_db_inventory.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "active_program_count", "governed_admission_program_count",
        "admission_rule_set_count", "admission_group_count",
        "admission_condition_count", "programs_with_nested_groups",
    )}, indent=2))
