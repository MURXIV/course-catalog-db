ALTER TABLE students ADD CONSTRAINT students_email_format CHECK (position('@' IN email) > 1);
\set VERBOSITY verbose
\set ON_ERROR_STOP off
INSERT INTO students(name,email) VALUES ('Test User','no-at-sign');
\set ON_ERROR_STOP on
\d students
