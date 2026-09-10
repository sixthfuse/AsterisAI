BEGIN;
INSERT INTO program_advisor_aliases(normalized_alias,program_id,priority) VALUES
 ('business administration graduate certificate','A700GRCERT',10),('graduate business certificate','A700GRCERT',10),('business admin grad certificate','A700GRCERT',10)
ON CONFLICT(normalized_alias) DO UPDATE SET program_id=EXCLUDED.program_id,alias_scope='program',family_key=NULL,priority=EXCLUDED.priority,active=TRUE;
INSERT INTO program_relationships(program_id,relationship_type,relationship_key,independent_program) VALUES ('A700GRCERT','member_of','graduate_business',TRUE)
ON CONFLICT(program_id,relationship_type,relationship_key) DO UPDATE SET independent_program=TRUE,active=TRUE;
COMMIT;
