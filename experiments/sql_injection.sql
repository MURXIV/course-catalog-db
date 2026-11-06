SELECT id, title FROM courses WHERE id = 'x' OR '1'='1';
PREPARE by_id(text) AS SELECT id, title FROM courses WHERE id = $1;
EXECUTE by_id('x'' OR ''1''=''1');
EXECUTE by_id('api-design');
DEALLOCATE by_id;
