-- User-confirmed correction for the canonical FSCT 8150 prerequisite text.
-- Keep the imported status/provenance fields intact; only replace the truncated value.
UPDATE courses
SET prerequisite_text_clean = '3 credits of a university/college biology course.'
WHERE course_id = 'FSCT8150'
  AND prerequisite_text_clean = '3';

-- User-confirmed correction for CREA 8210.
UPDATE courses
SET prerequisite_text_clean = 'All 60 credits from the BCI are required.'
WHERE course_id = 'CREA8210'
  AND prerequisite_text_clean = 'All 60';
