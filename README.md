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

## Index: EXPLAIN before and after

In `idx_demo`, loaded 500 courses, 20,000 students and 50,000 enrollments.
Query: `SELECT * FROM enrollments WHERE student_id = 777;`.
Each timing is the minimum of three real EXPLAIN ANALYZE runs on this laptop.
All six runs and the other lookup plans are in [evidence/index.txt](evidence/index.txt).

| Measurement | Before index | After index |
|---|---|---|
| Access method | Seq Scan on enrollments | Bitmap Heap Scan on enrollments |
| Estimated cost | 0.00..1042.00 | 4.31..15.59 |
| Rows removed by filter | 49997 | 0 (no filter scan) |
| Execution time | 1.838 ms | 0.016 ms |

Before:

```text
Seq Scan on enrollments  (cost=0.00..1042.00 rows=3 width=34)
  Filter: (student_id = 777)
```

After:

```text
Bitmap Heap Scan on enrollments  (cost=4.31..15.59 rows=3 width=34)
  Recheck Cond: (student_id = 777)
  ->  Bitmap Index Scan on enrollments_student_id_idx  (cost=0.00..4.31 rows=3 width=0)
        Index Cond: (student_id = 777)
```

Table size: 3336 kB; added index size: 896 kB.

1. PRIMARY KEY and UNIQUE create indexes automatically; FOREIGN KEY does
   not create an index on its referencing column. The unique pair
   `(course_id, student_id)` serves searches by its leading `course_id` column;
   on this dataset it did not replace a dedicated student lookup index.
   Email lookup used `students_email_key`, and course lookup used
   `enrollments_course_id_student_id_key`.
2. Six course rows fit in a very small table. Sequential access costs less than
   going through an index. The student lookup otherwise scans 50,000 enrollment
   rows, so a selective index saves work. The planner chooses by estimated cost,
   not simply by whether an index exists.
3. The index speeds up listing a student's enrollments and finding their child
   rows when a student is deleted with CASCADE. It uses storage and makes writes
   maintain another index, so unnecessary indexes should be avoided.

Small main-table lookup after ANALYZE:

```text
Seq Scan on courses  (cost=0.00..1.07 rows=1 width=100)
  Filter: (id = 'api-design'::text)
```

To repeat the index experiment after the final schema includes the index:

```bash
psql -h localhost -U catalog_app -d idx_demo -v ON_ERROR_STOP=1 -f schema.sql
psql -h localhost -U catalog_app -d idx_demo -v ON_ERROR_STOP=1 -c "DROP INDEX enrollments_student_id_idx;"
psql -h localhost -U catalog_app -d idx_demo -v ON_ERROR_STOP=1 -f experiments/idx_data.sql
psql -h localhost -U catalog_app -d idx_demo
```

Then compare in psql:

```sql
EXPLAIN SELECT * FROM students WHERE email = 'student777@example.com';
EXPLAIN SELECT * FROM enrollments WHERE course_id = 'course-7';
EXPLAIN ANALYZE SELECT * FROM enrollments WHERE student_id = 777;
-- Run the previous statement three times; record the minimum Execution Time.
CREATE INDEX enrollments_student_id_idx ON enrollments(student_id);
EXPLAIN ANALYZE SELECT * FROM enrollments WHERE student_id = 777;
-- Repeat three times again. Execution times vary by machine and cache state.
```

## Transaction

Scenario: enroll Madina Ospanova in a course using two inserts. Tested with two
independent database connections, A (writer) and B (observer). Actual observations
are in [evidence/transaction.txt](evidence/transaction.txt).

- A began a transaction and inserted Madina. The second insert referenced
  `no-such-course`, failed with SQLSTATE 23503, and aborted the transaction.
  A subsequent SELECT failed with 25P02 (current transaction is aborted).
  After ROLLBACK, Madina's count was 0: the first insert was undone as well.
- In a new transaction A inserted Madina and enrolled her in `web-security`.
  B saw count 0 before COMMIT and count 1 after COMMIT. The final totals were
  4 students and 7 enrollments. Default isolation was `read committed`.
- Without a transaction, the first insert would commit independently. A failed
  second insert would leave a student without the intended enrollment.

To reproduce, start two psql sessions connected to `course_catalog`.
For the failure case, execute in A:

```sql
BEGIN;
INSERT INTO students(name,email) VALUES ('Madina Ospanova','madina@example.com');
INSERT INTO enrollments(course_id,student_id)
SELECT 'no-such-course',id FROM students WHERE email='madina@example.com';
SELECT count(*) FROM students; -- expected 25P02
ROLLBACK;
SELECT count(*) FROM students WHERE email='madina@example.com'; -- 0
```

For the successful case, begin and run both inserts in A, using `web-security`
instead of `no-such-course`. Before committing, run the last count query in B:
it returns 0. COMMIT in A, then repeat in B: it returns 1. Finally rebuild with
schema.sql and seed.sql to restore the 6/3/6 dataset. Keep transactions short:
they hold locks until committed or rolled back.
