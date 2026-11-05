# course-catalog-db

PostgreSQL schema for Course Catalog, Lab 6 of Advanced Web Technologies.
Author: Timur Murat. The frontend and FastAPI projects are unchanged.

## How to run

Requires PostgreSQL 16+ and the psql client. Once, as the postgres superuser:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
CREATE DATABASE idx_demo OWNER catalog_app;
CREATE DATABASE norm_demo OWNER catalog_app;
```

From this repository, run the following commands. Enter the teaching password
`change-me` when prompted. On Windows, first set `$env:PGCLIENTENCODING = "UTF8"`.
Port 5432 is the default; add `-p YOUR_PORT` to each command if needed.

```bash
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f schema.sql
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f queries.sql
```

`schema.sql` intentionally drops the three teaching tables: rebuilding erases
their contents and resets identity sequences. Run `seed.sql` once per rebuild.
Afterwards there are 6 courses, 3 students and 6 enrollments. Queries 3 and 4
roll back their writes. Identity sequences are not rolled back, so the example
enrollment ID can increase between runs while stored data stays the same.
The password above is a lab example; real credentials do not belong in Git.

## Constraint violation log

Executed against PostgreSQL 18, as `catalog_app`.
Complete statements and actual error messages: [evidence/constraints.txt](evidence/constraints.txt).
HTTP values below describe the intended API mapping; this lab changes SQL only.

| Experiment | SQLSTATE | Constraint or NOT NULL column | API response |
|---|---|---|---|
| NULL title | `23502` | `title` | 422 |
| Zero credits | `23514` | `courses_credits_check` | 422 |
| Negative likes | `23514` | `courses_likes_check` | 422 |
| Short name | `23514` | `students_name_check` | 422 |
| Duplicate email | `23505` | `students_email_key` | 409 |
| Duplicate course ID | `23505` | `courses_pkey` | 409 |
| Duplicate enrollment | `23505` | `enrollments_course_id_student_id_key` | 409 |
| Missing course | `23503` | `enrollments_course_id_fkey` | 404 |
| Missing student | `23503` | `enrollments_student_id_fkey` | 404 |
| Delete enrolled course | `23001` | `enrollments_course_id_fkey` | 409 |
| Delete student 1 | No error | `enrollments_student_id_fkey` with CASCADE | 204 |

For the cascade experiment, deleting student 1 removed both of that student's
enrollments; the course rows stayed. ROLLBACK restored the student and both
enrollments. A foreign-key failure on an INSERT means a referenced resource
does not exist (404); a restricted DELETE conflicts with existing enrollments
(409). NOT NULL and CHECK failures map to invalid input (422); duplicates map
to conflict (409). These are deliberate route-level choices, not HTTP responses
automatically produced by PostgreSQL.

Pydantic checks incoming API data and gives early feedback, but scripts, another
application or direct SQL can bypass the API. Database constraints protect every
write regardless of its source, including concurrent requests.
