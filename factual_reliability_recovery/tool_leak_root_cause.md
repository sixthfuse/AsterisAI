# Tool-leak root cause

The browser does not render tool objects or an SSE stream. It rendered the `/advisor` response field `answer` as text. Raw `functions.search_programs` and JSON fragments originated when model/tool protocol text survived into the raw model answer and the deterministic finalizer returned it unchanged. API serialization faithfully transported that string, and the browser had no boundary filter.

The repair removes function headers, tool JSON argument lines, and protocol markers in the server finalizer and again at the browser render boundary. API and browser regression tests use the observed leak strings. The exact ten-turn endpoint replay and the live Sol response contain no function names or JSON arguments.
