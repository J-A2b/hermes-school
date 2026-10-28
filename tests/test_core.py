import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from cryptography.fernet import Fernet, InvalidToken
from hermes_school.models.normalize import grade, number, local_date
from hermes_school.storage.db import connect, records, upsert
from hermes_school.sync.service import synchronize
from hermes_school.analytics.planning import estimate, weekend_context
from hermes_school.notifications.queue import quiet, pending
from hermes_school.documents.library import store, search, download
from hermes_school.security.backup import backup, restore


@pytest.mark.parametrize('value,maximum,result', [('15,5', '20', 15.5), ('7', '10', 14), ('ABS', '20', None), ('NN', '20', None), ('4', '0', None), ('NaN', '20', None), ('1', '4', 5)])
def test_grades(value, maximum, result):
    g = grade({'id': 1, 'valeur': value, 'noteSur': maximum}, 'notes')
    assert g['out_of_20'] == result
    assert g['raw']['valeur'] == value


def test_letter_grade():
    assert grade({'id': 1, 'valeur': '5', 'noteSur': '5', 'enLettre': True}, '')['out_of_20'] is None


def test_dates_dst():
    assert local_date('2026-01-01 09:00').endswith('+01:00')
    assert local_date('2026-07-01 09:00').endswith('+02:00')
    assert local_date('2026-10-25') == '2026-10-25'
    with pytest.raises(ValueError):
        local_date('incorrect')


def test_upsert_history_and_duplicates():
    item = {'source_id': '1', 'title': 'Contrôle', 'score': 12}
    with connect() as db:
        assert upsert(db, 'a', 'grades', item, True) == 'created'
        assert upsert(db, 'a', 'grades', item) == 'unchanged'
        assert upsert(db, 'a', 'grades', item | {'score': 13}) == 'modified'
        assert db.execute('SELECT count(*) FROM records').fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM grade_history').fetchone()[0] == 2
        old = db.execute("SELECT old_payload FROM change_events WHERE action='modified'").fetchone()[0]
        assert json.loads(old)['score'] == 12


def test_sync_partial_and_atomic():
    class Source:
        def fetch(self, kind):
            if kind == 'grades':
                return [{'source_id': '1', 'title': 'Note'}]
            if kind == 'assignments':
                return [{'source_id': '2'}, {}]
            raise TimeoutError('TOKEN SECRET DO NOT PERSIST')
    result = synchronize(Source(), 'student')
    assert result['status'] == 'partial'
    assert len(records('grades')) == 1
    assert records('assignments') == []
    with connect() as db:
        assert 'TOKEN' not in db.execute('SELECT summary FROM sync_runs').fetchone()[0]
    assert synchronize(Source(), 'student')['modules']['grades']['unchanged'] == 1


def test_assessment_notifications_baseline_dedup():
    with connect() as db:
        upsert(db, 'a', 'assessments', {'source_id': '1'}, True)
        upsert(db, 'a', 'grades', {'source_id': '1'})
        assert db.execute('SELECT count(*) FROM notifications').fetchone()[0] == 0
        upsert(db, 'a', 'assessments', {'source_id': '2'})
        upsert(db, 'a', 'assessments', {'source_id': '2'})
        assert db.execute('SELECT count(*) FROM notifications').fetchone()[0] == 1


@pytest.mark.parametrize('hour,expected', [(0, True), (5, True), (12, False), (22, True)])
def test_quiet(hour, expected):
    # Winter UTC is Paris minus one hour.
    assert quiet(datetime(2026, 1, 1, hour, tzinfo=timezone.utc)) is expected


def test_estimates():
    assert estimate('Maths')['method'] == 'valeur par défaut'
    with connect() as db:
        for n in [20, 30, 100]:
            db.execute('INSERT INTO study_sessions(subject,work_type,planned_minutes,actual_minutes,difficulty,date) VALUES(?,?,?,?,?,?)', ('Maths', 'homework', 30, n, 3, '2026-01-01'))
    assert estimate('Maths')['minutes'] == 30
    assert estimate('Maths')['samples'] == 3


def test_document_search_and_url_security():
    rid = store('Théorème de Pythagore'.encode(), 'cours.txt', 'fixture anonymisée')
    assert search('Pythagore')[0]['id'] == rid
    for url in ['http://doc1.ecoledirecte.com/a', 'https://evil.test/a', 'https://doc1.ecoledirecte.com.evil.test/a', 'https://127.0.0.1/a']:
        with pytest.raises(ValueError):
            download(url, 'a.pdf', 'test')


def test_encrypted_backup_restore(tmp_path):
    store(b'Cours prive', 'cours.txt', 'fixture')
    key = Fernet.generate_key()
    path = tmp_path / 'backup.enc'
    backup(path, key)
    assert b'Cours prive' not in path.read_bytes()
    target = tmp_path / 'restored'
    restore(path, key, target)
    import sqlite3
    with sqlite3.connect(target / 'school.sqlite') as db:
        assert db.execute('SELECT count(*) FROM documents').fetchone()[0] == 1
    assert len(list((target / 'documents').iterdir())) == 1
    with pytest.raises(ValueError):
        restore(path, key, target)
    with pytest.raises(InvalidToken):
        restore(path, Fernet.generate_key(), tmp_path / 'wrong')


def test_mcp_tools():
    from hermes_school.integrations.mcp.server import build_server, update_task
    server = build_server()
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert len(names) == 11
    assert 'school_get_weekend_context' in names
    assert 'school_update_personal_task' in names
    with pytest.raises(ValueError):
        update_task(1, 'yes')
    assert update_task(1, True)['updated'] is False


def test_sources_scoped():
    with connect() as db:
        for account in ['one', 'two']:
            upsert(db, account, 'grades', {'source_id': '1'})
    assert len(records('grades')) == 2


def test_query_injection():
    with connect() as db:
        upsert(db, 'a', 'grades', {'source_id': '1'})
    assert records('grades', "' OR 1=1 --") == []
    with pytest.raises(ValueError):
        records('grades; DROP TABLE records')
