import json
from hermes_school.storage.db import connect, now, upsert


def synchronize(source, account, kinds=('grades', 'assignments', 'assessments', 'lessons', 'timetable')):
    with connect() as db:
        run = db.execute("INSERT INTO sync_runs(started_at,status) VALUES(?,'running')", (now(),)).lastrowid
    summary = {}
    homework = None
    homework_error = None
    for kind in kinds:
        try:
            if kind in ('assignments', 'assessments', 'lessons') and hasattr(source, 'homework'):
                if homework_error:
                    raise ValueError('Cahier indisponible')
                if homework is None:
                    try:
                        homework = source.homework()
                    except Exception:
                        homework_error = True
                        raise
                items = homework[kind]
            else:
                items = source.fetch(kind)
            if not isinstance(items, list):
                raise ValueError('Liste attendue')
            with connect() as db:
                # Baseline per account AND module: a partial first import never floods alerts.
                baseline = not db.execute('SELECT 1 FROM sync_modules WHERE account=? AND kind=? AND source=?', (account, kind, 'ecoledirecte')).fetchone()
                counts = {'created': 0, 'modified': 0, 'unchanged': 0}
                for item in items:
                    counts[upsert(db, account, kind, item, baseline)] += 1
                db.execute('INSERT OR REPLACE INTO sync_modules VALUES(?,?,?,?)', ('ecoledirecte', account, kind, now()))
                summary[kind] = counts
        except Exception as exc:
            # Never persist remote exception text: it can contain credentials or bodies.
            summary[kind] = {'error': type(exc).__name__}
    failed = sum('error' in s for s in summary.values())
    status = 'failed' if failed == len(summary) else 'partial' if failed else 'success'
    with connect() as db:
        db.execute('UPDATE sync_runs SET finished_at=?,status=?,summary=? WHERE id=?', (now(), status, json.dumps(summary), run))
    return {'id': run, 'status': status, 'modules': summary}
