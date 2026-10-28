import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from hermes_school.config import data_dir

KINDS = ('grades', 'assignments', 'assessments', 'lessons', 'messages', 'timetable', 'school_life')


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    path = data_dir() / 'school.sqlite'
    db = sqlite3.connect(path, timeout=20)
    path.chmod(0o600)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def migrate():
    with connect() as db:
        db.executescript(Path(__file__).with_name('001.sql').read_text())
        for migration in sorted(Path(__file__).parent.glob('*.sql')):
            version = int(migration.stem)
            if not db.execute('SELECT 1 FROM migrations WHERE version=?', (version,)).fetchone():
                db.executescript('BEGIN;\n' + migration.read_text() + '\nCOMMIT;')
        try:
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS document_search USING fts5(document_id UNINDEXED, text)')
        except sqlite3.OperationalError:
            pass


def upsert(db, account, kind, item, baseline=False, source='ecoledirecte'):
    if kind not in KINDS or not str(item.get('source_id', '')).strip():
        raise ValueError('Identifiant ou type invalide')
    payload = json.dumps(item, sort_keys=True, ensure_ascii=False, allow_nan=False)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    old = db.execute('SELECT * FROM records WHERE source=? AND account=? AND kind=? AND source_id=?',
                     (source, account, kind, str(item['source_id']))).fetchone()
    stamp = now()
    if old and old['fingerprint'] == digest:
        db.execute('UPDATE records SET last_synced=? WHERE id=?', (stamp, old['id']))
        return 'unchanged'
    if old:
        rid = old['id']
        db.execute('UPDATE records SET subject=?,title=?,date=?,payload=?,fingerprint=?,last_synced=? WHERE id=?',
                   (item.get('subject', ''), item.get('title', ''), item.get('date'), payload, digest, stamp, rid))
    else:
        rid = db.execute('INSERT INTO records(source,account,kind,source_id,subject,title,date,payload,fingerprint,first_seen,last_synced) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                         (source, account, kind, str(item['source_id']), item.get('subject', ''), item.get('title', ''), item.get('date'), payload, digest, stamp, stamp)).lastrowid
    db.execute('INSERT OR REPLACE INTO source_references(record_id,endpoint) VALUES(?,?)', (rid, item.get('endpoint', '')))
    change = db.execute('INSERT INTO change_events(record_id,action,old_payload,new_payload,created_at) VALUES(?,?,?,?,?)',
                        (rid, 'modified' if old else 'imported' if baseline else 'created', old['payload'] if old else None, payload, stamp)).lastrowid
    # An announced future assessment is distinct from a newly discovered grade.
    if not baseline and not old and kind == 'assessments':
        db.execute('INSERT INTO notifications(change_id,created_at) VALUES(?,?)', (change, stamp))
    return 'modified' if old else 'created'


def records(kind=None, query='', subject='', limit=200):
    if kind is not None and kind not in KINDS:
        raise ValueError('Type invalide')
    sql, args = 'SELECT * FROM records WHERE 1=1', []
    for field, value in [('kind', kind), ('subject', subject)]:
        if value:
            sql += f' AND {field}=?'
            args.append(value)
    if query:
        sql += ' AND (title LIKE ? OR payload LIKE ?)'
        args.extend(['%' + query[:200] + '%'] * 2)
    sql += ' ORDER BY date DESC, id DESC LIMIT ?'
    args.append(max(1, min(int(limit), 500)))
    with connect() as db:
        return [dict(r) | {'data': json.loads(r['payload'])} for r in db.execute(sql, args)]
