# Бонусы Lab 6

Открой папку course-catalog-db. В адресной строке Проводника введи powershell.

```powershell
powershell -ExecutionPolicy Bypass -File .\run_bonus.ps1
```

Скрипт запускает все 5 бонусов и сохраняет результаты в evidence/bonus.
Он работает только с отдельными учебными базами lab6_bonus*.

| Бонус | Код для показа | Результат и что сказать |
|---|---|---|
| 1 Нормализация | experiments/norm_demo.sql и normalization.sql | «В общей таблице изменение одной строки даёт два названия курса; удаление записи теряет курс; курс без студента требует NULL. После разделения — 3 курса, 3 студента, 6 записей». |
| 2 Потерянное обновление | run_bonus.py, блок с двумя соединениями; experiments/lock_a.sql и lock_b.sql | «Обе сессии читают 11 и пишут 12 — один лайк теряется. likes = likes + 1 даёт 13. Пока A не сделает COMMIT, B ждёт блокировку». |
| 3 SQL-инъекция | experiments/sql_injection.sql | «Подстановка OR возвращает 6 курсов. PREPARE передаёт строку как значение: атака даёт 0 строк, нормальный ID — 1». |
| 4 Дополнительные запросы | конец queries.sql или experiments/bonus_queries.sql | «LEFT JOIN находит три курса без записей. HAVING оставляет студентов с несколькими курсами: Daniyar — 3, Aigerim — 2». |
| 5 Проверка email | experiments/email_rule.sql и schema.sql | «ALTER TABLE добавляет правило к существующей таблице. Email без @ отклоняется: 23514, students_email_format». |

Результаты по отдельности: evidence/bonus/1-normalization.txt … 5-alter-email.txt.
Намеренная ошибка в бонусе 5 — ожидаемый результат, а не поломка.

## Показ блокировки в двух окнах

Подключи оба окна к lab6_bonus:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 127.0.0.1 -p 55436 -U catalog_app -d lab6_bonus
```

В окне A:

```sql
UPDATE courses SET likes = 11 WHERE id = 'api-design';
BEGIN;
UPDATE courses SET likes = likes + 1 WHERE id = 'api-design' RETURNING likes;
```

В окне B:

```sql
UPDATE courses SET likes = likes + 1 WHERE id = 'api-design' RETURNING likes;
```

B ждёт. В A выполни `COMMIT;`. B покажет 13. Заверши сбросом:

```sql
UPDATE courses SET likes = 11 WHERE id = 'api-design';
```
