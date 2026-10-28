import hmac
import json
import os
import re
import secrets
import time
from datetime import timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, abort, redirect, render_template, request, session, send_file, url_for
from werkzeug.security import check_password_hash
from hermes_school.config import data_dir, secret, settings, private_write
from hermes_school.storage.db import migrate, connect, records, KINDS
from hermes_school.documents.library import search
from hermes_school.analytics.planning import weekend_context
from hermes_school.analytics.grades import subject_averages

PAGES = {'overview': 'Accueil', 'grades': 'Notes', 'assignments': 'Devoirs', 'timetable': 'Emploi du temps',
         'lessons': 'Cours et documents', 'messages': 'Messagerie', 'changes': 'Historique', 'organization': 'Organisation', 'settings': 'Paramètres'}


def create_app(test_config=None):
    migrate()
    app = Flask(__name__)
    trusted_hosts = ['localhost', '127.0.0.1', '[::1]']
    for host in os.environ.get('HERMES_SCHOOL_TRUSTED_HOSTS', '').split(','):
        host = host.strip().lower()
        if not host:
            continue
        # Exact DNS names only: reject Flask's leading-dot suffix trust and URLs.
        if len(host) > 253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host):
            raise ValueError('Nom d’hôte autorisé invalide')
        trusted_hosts.append(host)
    app.config.update(SECRET_KEY=secret(), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                      SESSION_COOKIE_SECURE=os.environ.get('HERMES_SCHOOL_HTTPS') == '1',
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=8), MAX_CONTENT_LENGTH=64 * 1024,
                      TRUSTED_HOSTS=trusted_hosts)
    if test_config:
        app.config.update(test_config)
    attempts = {}

    @app.before_request
    def guard():
        if request.routing_exception:
            raise request.routing_exception
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        if request.method == 'POST' and not hmac.compare_digest(session['csrf'], request.form.get('csrf', '')):
            abort(403)
        if request.endpoint not in ('login', 'static') and not session.get('authenticated'):
            return redirect(url_for('login'))

    @app.after_request
    def headers(response):
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            ip = request.remote_addr
            recent = [t for t in attempts.get(ip, []) if time.monotonic() - t < 300]
            if len(recent) >= 5:
                abort(429)
            path = data_dir() / 'password.hash'
            if path.exists() and check_password_hash(path.read_text().strip(), request.form.get('password', '')):
                session.clear()
                session.update(authenticated=True, csrf=secrets.token_urlsafe(32))
                session.permanent = True
                attempts.pop(ip, None)
                return redirect('/')
            attempts[ip] = recent + [time.monotonic()]
            error = 'Connexion refusée. Vérifiez le mot de passe du dashboard.'
        return render_template('login.html', error=error)

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect('/login')

    @app.get('/')
    @app.get('/page/<page>')
    def page_view(page='overview'):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        if page not in PAGES:
            abort(404)
        with connect() as db:
            status = db.execute('SELECT * FROM sync_runs ORDER BY id DESC LIMIT 1').fetchone()
            changes = [dict(r) for r in db.execute('SELECT c.*,r.title,r.kind FROM change_events c JOIN records r ON r.id=c.record_id ORDER BY c.id DESC LIMIT 100')]
            tasks = [dict(r) for r in db.execute('SELECT * FROM tasks ORDER BY done,priority,id')]
            counts = dict(db.execute('SELECT kind,count(*) FROM records GROUP BY kind'))
            study_sessions = [dict(r) for r in db.execute('SELECT * FROM study_sessions ORDER BY id DESC LIMIT 30')]
        items = records(page if page in KINDS else None, request.args.get('q', ''), request.args.get('subject', ''))
        period = request.args.get('period', '')
        periods = sorted({r['data'].get('period') for r in items if r['data'].get('period')})
        if period:
            items = [r for r in items if r['data'].get('period') == period]
        if page in ('assignments', 'timetable'):
            items.sort(key=lambda r: r['date'] or '9999')
        day = request.args.get('day', '')
        if day:
            items = [r for r in items if (r['date'] or '')[:10] == day]
        subjects = sorted({r['subject'] for r in records(limit=500) if r['subject']})
        # A general average is deliberately unavailable unless supplied and verified by source.
        return render_template('dashboard.html', pages=PAGES, page=page, title=PAGES[page], items=items,
                               subjects=subjects, changes=changes, tasks=tasks, counts=counts, status=status,
                               documents=search(request.args.get('q', '')), settings=settings(),
                               demo=(data_dir() / 'DEMO').exists(), context=weekend_context(), periods=periods, study_sessions=study_sessions,
                               today=datetime.now(ZoneInfo('Europe/Paris')).date().isoformat(),
                               tomorrow=(datetime.now(ZoneInfo('Europe/Paris')).date()+timedelta(days=1)).isoformat(),
                               averages=subject_averages(items))

    @app.post('/assignments/<int:rid>/plan')
    def assignment_plan(rid):
        from datetime import datetime
        try:
            minutes = int(request.form.get('minutes', '30'))
            priority = int(request.form.get('priority', '2'))
            scheduled = request.form.get('scheduled_at') or None
            if scheduled:
                datetime.fromisoformat(scheduled)
            if not 1 <= minutes <= 1440 or not 1 <= priority <= 3:
                raise ValueError()
        except ValueError:
            abort(400)
        with connect() as db:
            record = db.execute("SELECT * FROM records WHERE id=? AND kind='assignments'", (rid,)).fetchone()
            if not record:
                abort(404)
            db.execute('INSERT INTO tasks(record_id,title,estimated_minutes,priority,due_date,scheduled_at) VALUES(?,?,?,?,?,?) ON CONFLICT(record_id) WHERE record_id IS NOT NULL DO UPDATE SET estimated_minutes=excluded.estimated_minutes,priority=excluded.priority,scheduled_at=excluded.scheduled_at',
                       (rid, record['title'], minutes, priority, record['date'], scheduled))
        return redirect('/page/assignments')

    @app.post('/availability')
    def availability():
        from hermes_school.models.normalize import local_date
        from datetime import datetime
        try:
            start = local_date(request.form['start'])
            end = local_date(request.form['end'])
            if datetime.fromisoformat(end) <= datetime.fromisoformat(start):
                raise ValueError()
        except (ValueError, KeyError):
            abort(400)
        with connect() as db:
            db.execute('INSERT INTO availability(starts_at,ends_at,label) VALUES(?,?,?)', (start, end, request.form.get('label', 'Travail scolaire')[:200]))
        return redirect('/page/organization')

    @app.post('/availability/<int:slot_id>/delete')
    def availability_delete(slot_id):
        with connect() as db:
            db.execute('DELETE FROM availability WHERE id=?', (slot_id,))
        return redirect('/page/organization')

    @app.post('/study')
    def study():
        from hermes_school.storage.db import now
        try:
            actual, planned, difficulty = [int(request.form[k]) for k in ('actual', 'planned', 'difficulty')]
            if not 1 <= actual <= 1440 or not 1 <= planned <= 1440 or not 1 <= difficulty <= 5:
                raise ValueError()
            subject = request.form['subject'].strip()
            if not 1 <= len(subject) <= 100:
                raise ValueError()
        except (ValueError, KeyError):
            abort(400)
        with connect() as db:
            db.execute('INSERT INTO study_sessions(subject,work_type,planned_minutes,actual_minutes,difficulty,date) VALUES(?,?,?,?,?,?)', (subject, request.form.get('work_type', 'homework')[:50], planned, actual, difficulty, now()))
        return redirect('/page/organization')

    @app.post('/tasks')
    def task():
        title = request.form.get('title', '').strip()
        if not 1 <= len(title) <= 300:
            abort(400)
        try:
            minutes, priority = int(request.form.get('minutes', 30)), int(request.form.get('priority', 2))
            if not 1 <= minutes <= 1440 or not 1 <= priority <= 3:
                raise ValueError()
        except ValueError:
            abort(400)
        with connect() as db:
            db.execute('INSERT INTO tasks(title,estimated_minutes,priority) VALUES(?,?,?)', (title, minutes, priority))
        return redirect('/page/organization')

    @app.post('/tasks/<int:task_id>/toggle')
    def toggle(task_id):
        with connect() as db:
            db.execute('UPDATE tasks SET done=1-done WHERE id=?', (task_id,))
        return redirect('/page/organization')

    @app.post('/assignments/<int:rid>/done')
    def assignment_done(rid):
        with connect() as db:
            row = db.execute("SELECT title FROM records WHERE id=? AND kind='assignments'", (rid,)).fetchone()
            if not row:
                abort(404)
            db.execute('INSERT OR IGNORE INTO tasks(record_id,title,done) VALUES(?,?,1)', (rid, row['title']))
            if not db.execute('SELECT changes()').fetchone()[0]:
                db.execute('UPDATE tasks SET done=1-done WHERE record_id=?', (rid,))
        return redirect('/page/assignments')

    @app.post('/settings')
    def save_settings():
        import re
        cfg = settings()
        for key in ('quiet_start', 'quiet_end', 'friday_time'):
            value = request.form.get(key, '')
            if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value):
                abort(400)
            cfg[key] = value
        times = request.form.get('sync_times', '')
        if not times or any(not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', t) for t in times.split(',')) or len(times.split(',')) > 6:
            abort(400)
        cfg['sync_times'] = times
        private_write(data_dir() / 'settings.json', json.dumps(cfg))
        return redirect('/page/settings')

    @app.get('/documents/<int:doc_id>')
    def document(doc_id):
        with connect() as db:
            row = db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
        if not row:
            abort(404)
        digest = row['sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            abort(404)
        path = data_dir() / 'documents' / digest
        if not path.is_file() or path.is_symlink():
            abort(404)
        return send_file(path, as_attachment=True, download_name=row['name'], mimetype='application/octet-stream')

    return app
