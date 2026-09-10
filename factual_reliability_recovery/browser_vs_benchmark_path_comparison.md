# Browser versus benchmark path comparison

Both paths ultimately call the same FastAPI `/advisor` endpoint and `answer_student_question`. Both carry a ten-message history window and structured `conversation_state`.

The certified benchmark explicitly selected `gpt-5.6-sol` with medium reasoning. The real browser path omitted model settings and production defaulted to Luna. Production now defaults to `gpt-5.6-sol` with `medium` reasoning, and applies that profile on every model round.

The benchmark primarily certified governed data, deterministic state, frozen evidence, and targeted model transcripts. It did not use the exact ten-turn `/app` conversation as an end-to-end release gate. The browser displayed `data.answer` directly, so any raw tool protocol surviving model finalization was student-visible. The API now sanitizes every final answer, and the browser has a second sanitizer before text rendering.

The request transport did not diverge through SSE or a second endpoint: `/app` uses synchronous JSON POST. The material divergences were default model/profile, acceptance coverage, and the absence of a render-boundary protocol filter.
