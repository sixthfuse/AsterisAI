# Conversational subject contract

`conversation_state.TopicState` is the versioned API subject. The browser sends
the state returned by the last successful answer, independently of its ten-message
transcript window. Start a new conversation clears both. State contains references
and academic subtopics, never policy facts or answer language.

`resolve_academic_context` owns subject transitions. Explicit current user subjects
override the previous state. Otherwise the state persists. Scope is one of:
program, program_family, course, campus, campus_directory, global, ambiguous, none.
Changing subjects clears incompatible entity and academic-subtopic fields.
Program families use catalog aliases and retain their set scope. A verified
single-result search stores `unique_result_program_id`; singular referential
follow-ups resolve that record while plural/other-result questions retain the set.
`result_query` retains a credential filter independently of the family/global scope.
Zero/multiple results clear the reference, and explicit new topics replace it.
Applicant credentials and completed-course claims remain student facts.
An explicit application target in the same message overrides applicant background.
Course prerequisites within an active program requirement retrieve the named
course while retaining the program subject. Standalone course lookups select the
course as the subject.

For callers without structured state, chronological transcript replay uses the
same transition rules. Assistant prose can identify a course only for an
unresolved course search. With structured state, transcript prose cannot override
the active subject. A verified single-course tool result may resolve an unresolved
course lookup. A program search with exactly one verified result retains its
reference without changing the underlying set scope. Detail intent uses the
referenced program and forces the full program-details tool, rather than replaying
the list. Compound OR searches union independently resolved alternatives and
deduplicate by program ID. Standalone stop/frustration utterances bypass academic
resolution and retrieval, return a short acknowledgement, and preserve state.

Routes and entity tool arguments use the resolved subject. Family/global
eligibility queries retrieve every member's governed evidence. Response language
continues to come from the current question. Ambiguous explicit program references
clear stale selection and request clarification.

The `/advisor` request accepts optional `conversation_state`; every advisor answer
returns it. Old clients remain supported through transcript replay, but cannot
recover a subject after they omit both its state and its transcript anchor.
The version-1 API state has two backward-compatible optional fields:
`result_query` and `unique_result_program_id`. No database schema or data migration
is required.

Validation:

```text
.venv\Scripts\python.exe -B -m unittest test_ai_advisor test_advisor_quality_all_programs test_campus_information test_conversation_state test_conversation_results -q
.venv\Scripts\python.exe -B -m unittest discover -p "test*.py" -q
node --test test_conversation_ui.js
```

The full Python suite includes HTTP engine tests and expects the canonical app
running on localhost port 8000. Transition tests cover both Biochemistry/Nursing
orders, neutral follow-ups, catalog program names, scope switches, API roundtrips,
long conversations, ambiguity, and current-message language. Browser tests cover
history truncation, successful state roundtrips, errors, and conversation reset.

Validated on 2026-09-07: all 393 Python regression tests passed, including 132 new
topic-state tests; all four browser-state tests passed. Focused suites ran before
full discovery. The former test expecting global scope to revive an older program
was updated to require an explicit program switch under this contract.


Validated after generalized result-state fixes on 2026-09-07:
- Focused advisor/state/quality/campus run: 264 tests passed.
- Final targeted result-state run: 14 tests passed (including the subsequently
  added explicit global credential-scope regression).
- Full Python discovery: 407 tests passed in 179.127 seconds.
- Browser-state suite: 5 tests passed.
- Live HTTP verification on localhost:8000 passed the nine-turn Nursing,
  family-master, global-master, three detail requests, stop, compound search,
  and standalone biochemistry flow. All three detail requests used
  get_program_details for M600MSC; stop used no tools; both final searches
  included 9940BSC. The live model returned full overview, curriculum, admissions,
  and progression details rather than the search summary.

Changed implementation: ai_advisor.py and conversation_state.py.
Regression coverage: test_conversation_results.py and test_conversation_ui.js.
No database schema or migration changes. Browser transport already preserves the
complete returned state independently of the ten-message history window.
