BEGIN;
INSERT INTO program_advisor_aliases(normalized_alias,program_id,priority) VALUES
 ('aircraft maintenance electronics','1165DIPMA',10),('category e aircraft maintenance','1165DIPMA',10),('ame e','1165DIPMA',20),
 ('maintenance category m','1230DIPMA',10),('category m aircraft maintenance','1230DIPMA',10),('ame m','1230DIPMA',20),
 ('structures aircraft maintenance','1205DIPMA',10),('category s aircraft maintenance','1205DIPMA',10),('ame s','1205DIPMA',20)
ON CONFLICT(normalized_alias) DO UPDATE SET program_id=EXCLUDED.program_id,alias_scope='program',family_key=NULL,priority=EXCLUDED.priority,active=TRUE;
INSERT INTO program_advisor_aliases(normalized_alias,alias_scope,family_key,priority) VALUES
 ('aircraft maintenance engineer programs','family','aircraft_maintenance_engineer',10),
 ('aircraft maintenance programs','family','aircraft_maintenance_engineer',20)
ON CONFLICT(normalized_alias) DO UPDATE SET alias_scope='family',program_id=NULL,family_key=EXCLUDED.family_key,priority=EXCLUDED.priority,active=TRUE;
INSERT INTO program_relationships(program_id,relationship_type,relationship_key,independent_program)
SELECT program_id,'member_of','aircraft_maintenance_engineer',TRUE FROM programs WHERE program_id IN ('1165DIPMA','1230DIPMA','1205DIPMA')
ON CONFLICT(program_id,relationship_type,relationship_key) DO UPDATE SET independent_program=TRUE,active=TRUE;
COMMIT;
