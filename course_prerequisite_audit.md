# Suspicious prerequisite strings

Audit scope: all 1,152 records in the live `courses` table. Flagged values are bare numbers or non-empty prerequisite fragments of eight characters or fewer. No replacement was inferred.

| Course | Course name | Stored prerequisite | Disposition |
|---|---|---|---|
| FSCT 8150 | Forensic Biology: DNA Typing Theory | `3` | Corrected from user-confirmed wording to `3 credits of a university/college biology course.` |
| CREA 8210 | Creative Industries Internship Work Term | `All 60` | Corrected from user-confirmed wording to `All 60 credits from the BCI are required.` |

After the two user-confirmed corrections, this audit query returns no remaining records.

Query used:

```sql
SELECT course_id, display_course_code, course_name,
       prerequisite_text_raw, prerequisite_text_clean,
       prerequisite_status, source_url
FROM courses
WHERE btrim(coalesce(prerequisite_text_raw, '')) ~ '^[0-9]+(?:\.[0-9]+)?$'
   OR btrim(coalesce(prerequisite_text_clean, '')) ~ '^[0-9]+(?:\.[0-9]+)?$'
   OR (
       prerequisite_status <> 'explicit_none'
       AND length(btrim(coalesce(prerequisite_text_clean, prerequisite_text_raw, ''))) BETWEEN 1 AND 8
   )
ORDER BY course_id;
```
