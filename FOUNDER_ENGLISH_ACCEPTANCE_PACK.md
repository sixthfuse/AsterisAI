# Founder English Acceptance Pack

## Purpose

This is the final release gate for the English factual-orchestration phase. Use the real `/app` browser for 30–60 minutes. Ask the questions naturally, add your own wording, and do not coach Asteris toward the expected answer.

Automated checks are supporting evidence only. The phase passes only when the founder accepts the browser behaviour.

## How to score

Mark each item **PASS**, **FAIL**, or **UNCERTAIN**. A failure includes a wrong fact, wrong entity, stale-topic answer, invented certainty, missing decisive condition, raw internal protocol, or an answer that does not address the question. Record the exact answer for every failure or uncertainty.

Any confident wrong answer is a release blocker. A clarification is acceptable when the target really is ambiguous. Asteris may take several seconds; accuracy is the priority.

## Single-turn checks

1. How many campuses does BCIT have?
2. What are the names of the BCIT campuses?
3. What is BCIT's main phone number?
4. What is the address of the Downtown Campus?
5. How many active programs does BCIT have?
6. How many active courses are in the catalog?
7. Do you offer any technology programs?
8. What engineering programs does BCIT offer?
9. Are there any biotechnology or biochemistry programs?
10. Show me nursing programs.
11. Tell me about the Technology Management Bachelor of Technology.
12. What are the admission requirements for Technology Management?
13. Does Technology Management require work experience?
14. What English grade is required for Technology Management?
15. Does a BCIT diploma meet the post-secondary pathway for Technology Management?
16. Is there a pre-entry assessment for Technology Management?
17. Can a Red Seal count toward admission requirements at BCIT?
18. Which programs have published Red Seal admission evidence?
19. Tell me about the Civil Engineering diploma.
20. Tell me about the Civil Engineering bachelor degree.
21. What is the difference between the Civil Engineering diploma and bachelor degree?
22. What are the prerequisites for Hydraulics?
23. Tell me about Applied Hydraulics.
24. How many credits is Applied Hydraulics?
25. Which nursing programs accept international students?
26. Is the regular full-time Bachelor of Science in Nursing available to international students?
27. What does conditional or restricted international availability mean?
28. Which engineering programs are available to international students?
29. What can you verify about international availability, and what is unpublished?
30. Who are you?
31. What can you help me with?
32. How many languages can you speak?
33. What is the weather tomorrow?
34. Who won the World Cup?
35. Tell me about a program that does not exist at BCIT.

## Conversation A — valid campus follow-up, then hard topic switch

36. How many campuses does BCIT have?
37. What are their names?
38. Give me their phone numbers.
39. How many languages can you speak?
40. Now tell me about Technology Management.

Expected behaviour: turns 37–38 reuse campus context; turn 39 immediately drops it; turn 40 resolves Technology Management exactly.

## Conversation B — program continuity, then new course

41. Tell me about the Technology Management program.
42. What are its admission requirements?
43. Does it require work experience?
44. Tell me about Applied Hydraulics instead.
45. What are its prerequisites?

Expected behaviour: turns 42–43 retain Technology Management; turn 44 switches to the course; turn 45 retains that course.

## Conversation C — applicant facts must not become search filters

46. Tell me about Technology Management.
47. I have English 12 with 68 percent and a BCIT diploma, but no work experience. Can I apply?
48. Which parts do I meet and which part do I not meet?
49. Does my diploma change the work-experience requirement?
50. What else is required before entry?

Expected behaviour: English and diploma are assessed as met, the one-year relevant technical work requirement as unmet, and the pre-entry assessment remains explicit. Applicant facts never replace the target program.

## Conversation D — family set and member selection

51. What nursing programs does BCIT offer?
52. Which of these are available to international students?
53. Tell me more about the Pediatric Nursing option.
54. What are its entrance requirements?
55. Go back to all nursing programs. Which ones are unavailable to international students?

Expected behaviour: the set remains a set until turn 53 selects a member; turn 55 returns to the family and uses certified international states.

## Conversation E — correction and ambiguity

56. Tell me about Civil Engineering.
57. I mean the diploma, not the bachelor's degree.
58. What courses are in that program?
59. Actually, switch to the bachelor's degree.
60. What is required to progress into it?

Expected behaviour: Asteris asks for or uses the credential distinction correctly and never blends the two program records.

## Conversation F — course prerequisite semantics

61. Tell me about Applied Hydraulics.
62. What do I need before I can take it?
63. Are those requirements AND or OR?
64. If I completed only one alternative, is that enough?
65. Switch to another course: tell me about COMM 1100.

Expected behaviour: prerequisite groups preserve their stored AND/OR meaning; turn 65 switches courses cleanly.

## Conversation G — unrelated interruption

66. What engineering programs are available?
67. Which are available to international students?
68. What is BCIT's phone number?
69. What can you do?
70. Return to engineering programs.

Expected behaviour: each explicit switch wins immediately. Turn 69 must never answer with engineering, international, campus, or phone evidence.

## Conversation H — genuine unknowns

71. Tell me about Technology Management.
72. Can you guarantee I will be admitted?
73. Are seats available right now?
74. Exactly when will BCIT approve my application?
75. What facts can you verify, and which of those questions require BCIT confirmation?

Expected behaviour: Asteris gives stored facts but does not invent admission outcomes, live seats, or decision timing.

## Founder decision

- Date:
- Duration:
- Questions added beyond this pack:
- PASS count:
- FAIL count:
- UNCERTAIN count:
- Release decision: **ACCEPT / REJECT**
- Notes and copied failed answers:

