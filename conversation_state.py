"""Bounded, versioned session memory carried independently of the text window.

The state stores references, user-reported facts with provenance, and concise
verified conclusions.  Catalog records remain authoritative; this state never
stores raw chat messages or turns uncertain answers into facts.
"""
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class SubjectSnapshot(BaseModel):
    scope: Literal['program', 'program_family', 'course', 'campus', 'campus_directory', 'global']
    program_id: str | None = Field(default=None, max_length=40)
    course_id: str | None = Field(default=None, max_length=40)
    scope_query: str | None = Field(default=None, max_length=500)
    campus_name: str | None = Field(default=None, max_length=200)
    catalog_kind: Literal['programs', 'courses'] | None = None
    comparison_program_ids: list[str] = Field(default_factory=list, max_length=20)

    def identity(self):
        return (self.scope, self.program_id, self.course_id, self.scope_query,
                self.campus_name, self.catalog_kind, tuple(self.comparison_program_ids))


class CompletedCourseFact(BaseModel):
    course_id: str = Field(max_length=40)
    grade: float | None = Field(default=None, ge=0, le=100)
    source: Literal['user_reported'] = 'user_reported'


class StudentFact(BaseModel):
    key: Literal[
        'applicant_status', 'credential_background', 'work_experience',
        'delivery_preference', 'study_mode_preference', 'gpa'
    ]
    value: str = Field(max_length=300)
    source: Literal['user_reported'] = 'user_reported'


class AdvisorConclusion(BaseModel):
    key: str = Field(max_length=120)
    summary: str = Field(max_length=500)
    program_id: str | None = Field(default=None, max_length=40)
    certainty: Literal['verified'] = 'verified'
    source: Literal['asteris_derived'] = 'asteris_derived'
    dependency_keys: list[str] = Field(default_factory=list, max_length=20)
    valid: bool = True


class TopicState(BaseModel):
    version: Literal[1, 2] = 2
    scope: Literal['none', 'program', 'program_family', 'course', 'campus', 'campus_directory', 'global', 'ambiguous']
    program_id: str | None = Field(default=None, max_length=40)
    course_id: str | None = Field(default=None, max_length=40)
    scope_query: str | None = Field(default=None, max_length=500)
    result_query: str | None = Field(default=None, max_length=500)
    unique_result_program_id: str | None = Field(default=None, max_length=40)
    campus_name: str | None = Field(default=None, max_length=200)
    catalog_kind: Literal['programs', 'courses'] | None = None
    candidates: list[str] = Field(default_factory=list, max_length=100)
    prior_program_ids: list[str] = Field(default_factory=list, max_length=10)
    reported_completed_course_ids: list[str] = Field(default_factory=list, max_length=200)
    reported_completed_courses: list[CompletedCourseFact] = Field(default_factory=list, max_length=200)
    comparison_program_ids: list[str] = Field(default_factory=list, max_length=20)
    subject_history: list[SubjectSnapshot] = Field(default_factory=list, max_length=20)
    student_facts: list[StudentFact] = Field(default_factory=list, max_length=20)
    conclusions: list[AdvisorConclusion] = Field(default_factory=list, max_length=50)
    answered_facets: list[str] = Field(default_factory=list, max_length=100)
    stopped: bool = False
    turn_index: int = Field(default=0, ge=0)
    level: int | None = Field(default=None, ge=1, le=100)
    requirement_type: Literal['final_project_options', 'liberal_studies', 'electives'] | None = None
    academic_scope: Literal['admission', 'international', 'graduation', 'progression'] | None = None

    @model_validator(mode='after')
    def validate_subject(self):
        required = {'program': self.program_id, 'course': self.course_id,
                    'program_family': self.scope_query, 'campus': self.campus_name,
                    'global': self.catalog_kind, 'ambiguous': self.candidates}
        if self.scope in required and not required[self.scope]:
            raise ValueError('The active subject requires an entity reference')
        for field, scope in [('program_id', 'program'), ('course_id', 'course'),
                             ('scope_query', 'program_family'), ('campus_name', 'campus'),
                             ('catalog_kind', 'global')]:
            if self.scope != scope:
                setattr(self, field, None)
        if self.scope not in {'program_family', 'global'}:
            self.result_query = self.unique_result_program_id = None
        if self.scope != 'program_family':
            self.comparison_program_ids = []
        if self.scope != 'ambiguous':
            self.candidates = []
        if self.scope != 'program':
            self.level = self.requirement_type = self.academic_scope = None
        return self

    def identity(self):
        return (self.scope, self.program_id, self.course_id, self.scope_query,
                self.campus_name, self.catalog_kind, tuple(self.candidates),
                tuple(self.comparison_program_ids))

    def snapshot(self):
        if self.scope in {'none', 'ambiguous'}:
            return None
        return SubjectSnapshot(
            scope=self.scope, program_id=self.program_id, course_id=self.course_id,
            scope_query=self.scope_query, campus_name=self.campus_name,
            catalog_kind=self.catalog_kind,
            comparison_program_ids=list(self.comparison_program_ids),
        )

    @classmethod
    def from_value(cls, value):
        if value is None:
            return None
        return cls.model_validate(value).model_copy(deep=True)
