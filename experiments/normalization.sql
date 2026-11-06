\ir norm_demo.sql
SELECT id, student_name, course_id, course_title FROM registrations ORDER BY id;

BEGIN;
UPDATE registrations SET course_title = 'Modern Frontend: React 19 & Next.js 16'
WHERE student_name = 'Daniyar Bekov' AND course_id = 'modern-frontend';
SELECT DISTINCT course_id, course_title FROM registrations WHERE course_id = 'modern-frontend';
ROLLBACK;

BEGIN;
DELETE FROM registrations WHERE course_id = 'backend-fastapi';
SELECT * FROM registrations WHERE course_id = 'backend-fastapi';
ROLLBACK;

BEGIN;
INSERT INTO registrations (course_id, course_title, credits)
VALUES ('web-security', 'Web Security Essentials', 4);
SELECT student_name, course_id FROM registrations WHERE course_id = 'web-security';
ROLLBACK;

\ir ../schema.sql
INSERT INTO students (name, email)
SELECT student_name, student_email FROM registrations
GROUP BY student_name, student_email ORDER BY min(id);
INSERT INTO courses (id, title, description, credits)
SELECT DISTINCT course_id, course_title, '', credits FROM registrations;
INSERT INTO enrollments (course_id, student_id)
SELECT r.course_id, s.id FROM registrations r
JOIN students s ON s.email = r.student_email ORDER BY r.id;
SELECT s.name, c.title FROM enrollments e
JOIN students s ON s.id = e.student_id
JOIN courses c ON c.id = e.course_id ORDER BY e.id;
SELECT (SELECT count(*) FROM courses) AS courses,
       (SELECT count(*) FROM students) AS students,
       (SELECT count(*) FROM enrollments) AS enrollments;
