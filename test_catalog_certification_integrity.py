import unittest

from database import get_connection


class CatalogCertificationIntegrityTests(unittest.TestCase):
    def test_current_prerequisite_edges_and_external_pool_semantics(self):
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT count(*)
                    FROM prerequisites_import p
                    LEFT JOIN courses c ON c.course_id=p.prerequisite_course_id
                    WHERE p.prerequisite_course_id IS NOT NULL AND c.course_id IS NULL
                """)
                self.assertEqual(cursor.fetchone()[0], 0)

                cursor.execute("""
                    SELECT status,institution_key,native_course_code
                    FROM courses WHERE course_id='CIVL1011'
                """)
                self.assertEqual(cursor.fetchone(), ('Historical', 'BCIT', 'CIVL 1011'))

                cursor.execute("""
                    SELECT allows_external_courses,approval_required
                    FROM credit_requirements
                    WHERE program_id='810MBSN'
                      AND requirement_name='Complete an additional 3.0 credits of electives'
                """)
                self.assertEqual(cursor.fetchone(), (True, True))

                cursor.execute("SELECT count(*) FROM programs WHERE lower(status)='active'")
                self.assertEqual(cursor.fetchone()[0], 374)
                cursor.execute("SELECT count(*) FROM courses WHERE lower(status)='active'")
                self.assertEqual(cursor.fetchone()[0], 3976)


if __name__ == '__main__':
    unittest.main()
