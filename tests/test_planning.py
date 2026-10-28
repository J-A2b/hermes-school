import json
from datetime import datetime
from zoneinfo import ZoneInfo
from hermes_school.storage.db import connect, upsert
from hermes_school.sync.service import synchronize
from hermes_school.sync.attachments import synchronize_documents
from hermes_school.analytics.planning import weekend_context
from hermes_school.documents.library import search
from test_dashboard import client, login


def test_empty_initial_import_then_assessment():
    class Source:
        items = []
        def fetch(self, kind):
            return self.items
    source = Source()
    synchronize(source, 'a', kinds=('assessments',))
    source.items = [{'source_id': 'announced-later'}]
    synchronize(source, 'a', kinds=('assessments',))
    with connect() as db:
        assert db.execute('SELECT count(*) FROM notifications').fetchone()[0] == 1


def test_attachment_import_cached():
    class Client:
        student = 'a'
        calls = 0
        def attachment(self, file_id):
            assert file_id == '42'
            self.calls += 1
            return b'Cours de geometrie'
    with connect() as db:
        upsert(db, 'a', 'assignments', {'source_id': '7', 'endpoint': 'Eleves/a/cahierdetexte/2026-10-28.awp',
                                       'detail': {'aFaire': {'documents': [{'id': 42, 'libelle': 'geometrie.txt'}]}}})
    source = Client()
    assert synchronize_documents(source)['created'] == 1
    assert synchronize_documents(source)['cached'] == 1
    assert source.calls == 1
    assert search('geometrie')[0]['name'] == 'geometrie.txt'


def test_planning_forms_and_completed_work():
    today = datetime.now(ZoneInfo('Europe/Paris')).date().isoformat()
    with connect() as db:
        upsert(db, 'a', 'assignments', {'source_id': '1', 'title': 'Exercices', 'date': today, 'subject': 'Maths'})
        rid = db.execute('SELECT id FROM records').fetchone()[0]
    c = client()
    login(c)
    with c.session_transaction() as s:
        token = s['csrf']
    assert c.post(f'/assignments/{rid}/plan', data={'csrf': token, 'minutes': 45, 'priority': 1}).status_code == 302
    assert weekend_context()['items'][0]['estimate']['minutes'] == 45
    assert c.post('/availability', data={'csrf': token, 'start': today+'T09:00', 'end': today+'T11:00'}).status_code == 302
    assert weekend_context()['availability_known']
    assert c.post('/study', data={'csrf': token, 'subject': 'Maths', 'planned': 30, 'actual': 25, 'difficulty': 2}).status_code == 302
    assert c.post('/availability', data={'csrf': token, 'start': today+'T11:00', 'end': today+'T09:00'}).status_code == 400
    c.post(f'/assignments/{rid}/done', data={'csrf': token})
    assert weekend_context()['items'] == []
