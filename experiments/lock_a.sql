BEGIN;
UPDATE courses SET likes = likes + 1 WHERE id = 'api-design' RETURNING likes;
