import json
import pytest
import requests
from hermes_school.connectors.ecoledirecte.client import Client, APIError


class Reply:
    status_code = 200
    def __init__(self, value):
        self.value = value
    def json(self):
        return self.value


class Session:
    def __init__(self, replies):
        self.headers = {}
        self.cookies = {'GTK': 'fixture-cookie'}
        self.replies = iter(replies)
        self.calls = []
    def get(self, *args, **kwargs):
        return Reply({})
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Reply(next(self.replies))


def test_login_human_qcm():
    s = Session([{'code': 250, 'token': 'challenge'}, {'code': 200, 'data': {'question': 'UXVlc3Rpb24=', 'propositions': ['T3Vp', 'Tm9u']}},
                 {'code': 200, 'data': {'cn': 'cn', 'cv': 'cv'}}, {'code': 200, 'token': 'session', 'data': {'accounts': [{'id': 1}]}}])
    c = Client(session=s)
    accounts, fa = c.login('fixture', 'not-real', answer=lambda q, choices: 0)
    assert accounts[0]['id'] == 1
    assert fa == [{'cn': 'cn', 'cv': 'cv'}]
    assert s.headers['X-Gtk'] == 'fixture-cookie'
    assert s.headers['X-Token'] == 'session'
    assert json.loads(s.calls[2][1]['data']['data'])['choix'] == 'T3Vp'


def test_human_required_unattended():
    c = Client(session=Session([{'code': 250, 'token': 'challenge'}]))
    with pytest.raises(APIError) as err:
        c.login('fixture', 'not-real')
    assert err.value.code == 250


def test_grade_schema_and_token_rotation():
    c = Client(student='1', session=Session([{'code': 200, 'token': 'renewed', 'data': {'notes': [{'id': 1, 'valeur': '8', 'noteSur': '10'}]}}]))
    assert c.fetch('grades')[0]['out_of_20'] == 16
    assert c.http.headers['X-Token'] == 'renewed'
    c = Client(student='1', session=Session([{'code': 200, 'data': {}}]))
    with pytest.raises(APIError):
        c.fetch('grades')


def test_homework_details():
    s = Session([{'code': 200, 'data': {'2026-10-29': [{'idDevoir': 7, 'matiere': 'Maths', 'interrogation': True}]}},
                 {'code': 200, 'data': {'matieres': [{'id': 7, 'matiere': 'Maths', 'aFaire': {'contenu': 'RXhlcmNpY2Vz'}, 'contenuDeSeance': {'contenu': 'Q291cnM='}}]}}])
    result = Client(student='1', session=s).homework()
    assert result['assignments'][0]['description'] == 'Exercices'
    assert len(result['assessments']) == 1
    assert result['lessons'][0]['description'] == 'Cours'


def test_no_remote_message_write():
    with pytest.raises(NotImplementedError):
        Client(student='1').fetch('messages')


def test_publication_flags():
    data = {'notes': [{'id': 1, 'valeur': '12', 'noteSur': '20', 'codePeriode': 'T1'}],
            'parametrage': {'affichageNote': False}}
    assert Client(student='1', session=Session([{'code': 200, 'data': data}])).fetch('grades') == []
    data['parametrage'] = {'noteUniquementPeriodeCloture': True}
    assert Client(student='1', session=Session([{'code': 200, 'data': data}])).fetch('grades') == []
    data['periodes'] = [{'codePeriode': 'T1', 'cloture': True}]
    assert len(Client(student='1', session=Session([{'code': 200, 'data': data}])).fetch('grades')) == 1
