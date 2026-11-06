SELECT c.id
FROM courses c LEFT JOIN enrollments e ON e.course_id = c.id
WHERE e.id IS NULL
ORDER BY c.id;

SELECT s.name, count(*) AS courses
FROM students s JOIN enrollments e ON e.student_id = s.id
GROUP BY s.id
HAVING count(*) > 1
ORDER BY courses DESC, s.name;
