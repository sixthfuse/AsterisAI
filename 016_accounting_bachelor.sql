BEGIN;
INSERT INTO program_advisor_aliases(normalized_alias,program_id,priority) VALUES
 ('bachelor of accounting','8630BACC',5),('accounting degree','8630BACC',5),
 ('bcit accounting bachelor','8630BACC',5),('bacc','8630BACC',5)
ON CONFLICT(normalized_alias) DO UPDATE SET program_id=EXCLUDED.program_id,alias_scope='program',family_key=NULL,priority=EXCLUDED.priority,active=TRUE;
INSERT INTO program_relationships(program_id,relationship_type,relationship_key,independent_program) VALUES
 ('8630BACC','member_of','bachelor_degree',TRUE),('8630BACC','member_of','business_accounting',TRUE)
ON CONFLICT(program_id,relationship_type,relationship_key) DO UPDATE SET independent_program=TRUE,active=TRUE;
COMMIT;
