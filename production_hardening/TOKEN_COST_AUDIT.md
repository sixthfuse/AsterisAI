# Phase 9 token and API-cost audit

No live OpenAI request was used. The audit replays six representative cases from the frozen Phase 3 certification transcripts and estimates tokens as `ceil(characters / 4)`. It measures only conversation history sent to the model; unchanged instructions, tool schemas, evidence payloads, reasoning tokens, and output are outside the estimate.

| Case | Frozen evidence | Legacy history | Hardened history | Saved |
|---|---:|---:|---:|---:|
| Simple fact | FLOW-04/1 | 0 | 0 | 0 |
| Admissions | FLOW-27/1 | 0 | 0 | 0 |
| International eligibility | CAT-01-B/1 | 0 | 0 | 0 |
| Prerequisite | FLOW-03/1 | 0 | 0 | 0 |
| Comparison follow-up | FLOW-22/3 | 531 | 340 | 191 (36.0%) |
| Long-session follow-up | LONG-01/22 | 444 | 308 | 136 (30.6%) |

Across the two history-bearing representative requests, replayed context falls from 975 to 648 estimated tokens, a reduction of 327 tokens or 33.5%. First-turn requests correctly show no history reduction. Durable structured `TopicState` remains authoritative; recent text is still available but assistant messages are individually bounded and total replay is capped at 2,400 characters.

Actual model usage is now returned by the advisor path and logged as input, output, and cached tokens when the API supplies those fields. Output is capped at 1,200 tokens. The client uses a 30-second timeout and one SDK retry. Phase 9 live usage: 0 requests, 0 tokens, $0.

