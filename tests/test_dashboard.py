from hermes_school.config import data_dir, private_write
from hermes_school.dashboard.app import create_app, PAGES
from hermes_school.documents.library import store
from hermes_school.cli import demo
from werkzeug.security import generate_password_hash


def client():
    private_write(data_dir() / 'password.hash', generate_password_hash('a secure password'))
    return create_app({'TESTING': True}).test_client()


def login(c):
    c.get('/login')
    with c.session_transaction() as s:
        token = s['csrf']
    return c.post('/login', data={'csrf': token, 'password': 'a secure password'})


def test_auth_csrf_and_download():
    c = client()
    doc = store(b'prive', 'a.txt', 'test')
    assert c.get('/').status_code == 302
    assert c.get(f'/documents/{doc}').status_code == 302
    assert c.post('/login', data={'password': 'a secure password'}).status_code == 403
    assert login(c).status_code == 302
    assert c.get('/').status_code == 200
    assert c.get(f'/documents/{doc}').data == b'prive'
    assert c.get('/documents/9999').status_code == 404
    assert c.get('/documents/../../credentials.key').status_code == 404
    assert c.post('/tasks', data={'title': 'Bad csrf'}).status_code == 403
    assert c.get('/').headers['Cache-Control'] == 'no-store'


def test_every_page_demo():
    demo()
    c = client()
    login(c)
    for page in PAGES:
        response = c.get('/page/' + page)
        assert response.status_code == 200, page
        assert 'DÉMONSTRATION' in response.text


def test_personal_tasks():
    c = client()
    login(c)
    with c.session_transaction() as s:
        token = s['csrf']
    assert c.post('/tasks', data={'csrf': token, 'title': '<script>alert(1)</script>', 'minutes': 30, 'priority': 2}).status_code == 302
    response = c.get('/page/organization')
    assert '<script>alert(1)</script>' not in response.text
    assert '&lt;script&gt;' in response.text
    assert c.post('/tasks', data={'csrf': token, 'title': 'x', 'minutes': -1}).status_code == 400


def test_host_and_brute_force():
    c = client()
    assert c.get('/login', headers={'Host': 'evil.example'}).status_code == 400
    c.get('/login')
    with c.session_transaction() as s:
        token = s['csrf']
    for i in range(5):
        assert c.post('/login', data={'csrf': token, 'password': 'wrong'}).status_code == 200
    assert c.post('/login', data={'csrf': token, 'password': 'wrong'}).status_code == 429
