"""Run all five Lab 6 bonuses in separate lab6_bonus* databases."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import threading
import time

import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--host',default='127.0.0.1')
parser.add_argument('--port',type=int,default=55436)
parser.add_argument('--user',default='catalog_app')
parser.add_argument('--admin-user',default='postgres')
parser.add_argument('--psql',default=shutil.which('psql') or r'C:\Program Files\PostgreSQL\18\bin\psql.exe')
args=parser.parse_args()
evidence=ROOT/'evidence/bonus'
evidence.mkdir(exist_ok=True)

def conn(database,admin=False):
    return psycopg.connect(host=args.host,port=args.port,dbname=database,
        user=args.admin_user if admin else args.user,autocommit=True)

def create(database):
    assert database.startswith('lab6_bonus')
    with conn('postgres',True) as c:
        if not c.execute('SELECT 1 FROM pg_database WHERE datname=%s',(database,)).fetchone():
            c.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(database),sql.Identifier(args.user)))

def file(database,path,text=None):
    assert database.startswith('lab6_bonus')
    cmd=[args.psql,'-X','-h',args.host,'-p',str(args.port),'-U',args.user,'-d',database,'-v','ON_ERROR_STOP=1']
    cmd+=['-f',str(ROOT/path)] if text is None else ['-c',text]
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PGCLIENTENCODING':'UTF8'})
    if r.returncode: raise RuntimeError(r.stdout+r.stderr)
    return r.stdout+r.stderr

def save(name,text):
    (evidence/name).write_text(text.strip()+'\n',encoding='utf-8')
    print(text,flush=True)

create('lab6_bonus_norm')
save('1-normalization.txt',file('lab6_bonus_norm','experiments/normalization.sql'))
with conn('lab6_bonus_norm') as c:
    assert c.execute('SELECT (SELECT count(*) FROM courses),(SELECT count(*) FROM students),(SELECT count(*) FROM enrollments)').fetchone()==(3,3,6)

create('lab6_bonus')
file('lab6_bonus','schema.sql');file('lab6_bonus','seed.sql')
log=[]
with conn('lab6_bonus') as a,conn('lab6_bonus') as b,conn('lab6_bonus') as observer:
    read="SELECT likes FROM courses WHERE id='api-design'"
    inc="UPDATE courses SET likes=likes+1 WHERE id='api-design' RETURNING likes"
    av=a.execute(read).fetchone()[0];bv=b.execute(read).fetchone()[0]
    assert av==bv==11
    a.execute("UPDATE courses SET likes=%s WHERE id='api-design'",(av+1,))
    b.execute("UPDATE courses SET likes=%s WHERE id='api-design'",(bv+1,))
    assert a.execute(read).fetchone()[0]==12
    log+=['A reads 11; B reads 11. A writes 12; B writes 12. Final likes: 12 (one update lost).']
    a.execute("UPDATE courses SET likes=11 WHERE id='api-design'")
    assert a.execute(inc).fetchone()[0]==12
    assert b.execute(inc).fetchone()[0]==13
    log+=['Atomic SQL increments: A returns 12; B returns 13. Both likes preserved.']
    a.execute("UPDATE courses SET likes=11 WHERE id='api-design'")
    a.execute('BEGIN')
    assert a.execute(inc).fetchone()[0]==12
    b.execute("SET statement_timeout='10s'")
    result=[];errors=[]
    def update_b():
        try: result.append(b.execute(inc).fetchone()[0])
        except Exception as exc: errors.append(exc)
    worker=threading.Thread(target=update_b)
    worker.start()
    blocked=False
    try:
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            blocked=observer.execute('SELECT %s=ANY(pg_blocking_pids(%s))',(a.info.backend_pid,b.info.backend_pid)).fetchone()[0]
            if blocked:break
            time.sleep(.02)
        assert blocked,'B was not observed waiting for A'
        log+=['pg_blocking_pids confirmed: session B waits for the lock held by session A.']
    finally:
        a.execute('COMMIT');worker.join(timeout=10)
    assert not errors and result==[13],(errors,result)
    log+=['A COMMIT released the lock. B resumed and returned 13, using the current value.']
    a.execute("UPDATE courses SET likes=11 WHERE id='api-design'")
    log+=['Restored likes to 11.']
save('2-lost-update-lock.txt','\n'.join(log))

out=file('lab6_bonus','experiments/sql_injection.sql')
assert all(s in out for s in ('(6 rows)','(0 rows)','(1 row)'))
save('3-sql-injection.txt',out)
save('4-extra-queries.txt',file('lab6_bonus','experiments/bonus_queries.sql'))
with conn('lab6_bonus') as c:
    assert c.execute('SELECT c.id FROM courses c LEFT JOIN enrollments e ON e.course_id=c.id WHERE e.id IS NULL ORDER BY c.id').fetchall()==[('api-design',),('databases-postgresql',),('web-security',)]
    assert c.execute('SELECT s.name,count(*) AS courses FROM students s JOIN enrollments e ON e.student_id=s.id GROUP BY s.id HAVING count(*)>1 ORDER BY courses DESC,s.name').fetchall()==[('Daniyar Bekov',3),('Aigerim Sadykova',2)]
    before=[c.execute(f'SELECT * FROM {t} ORDER BY id').fetchall() for t in ('courses','students','enrollments')]
    file('lab6_bonus','queries.sql');file('lab6_bonus','queries.sql')
    after=[c.execute(f'SELECT * FROM {t} ORDER BY id').fetchall() for t in ('courses','students','enrollments')]
    assert before==after

create('lab6_bonus_email')
old=(ROOT/'schema.sql').read_text(encoding='utf-8').replace(" CONSTRAINT students_email_format CHECK (position('@' IN email) > 1)",'')
file('lab6_bonus_email','schema.sql',text=old);file('lab6_bonus_email','seed.sql')
out=file('lab6_bonus_email','experiments/email_rule.sql')
assert '23514' in out and 'students_email_format' in out
save('5-alter-email.txt',out)
with conn('lab6_bonus_email') as c:
    assert c.execute("SELECT count(*) FROM students WHERE email='no-at-sign'").fetchone()[0]==0
    assert c.execute('SELECT count(*) FROM students').fetchone()[0]==3

save('summary.txt','All five Lab 6 bonus tasks passed.\nNormalization: 3 courses / 3 students / 6 enrollments.\nLost update: 12; atomic update and observed row lock: 13.\nInjection: 6 rows; parameter payload: 0; valid parameter: 1.\nExtra queries match expected results.\nEmail rule: SQLSTATE 23514 / students_email_format.\nqueries.sql ran twice without changing stored rows.\nWorking course_catalog database was never modified.')
