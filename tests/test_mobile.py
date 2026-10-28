import pytest
from hermes_school.dashboard.app import create_app


def test_mobile_exact_host_and_secure_cookie(monkeypatch):
    monkeypatch.setenv('HERMES_SCHOOL_TRUSTED_HOSTS', 'school.example.ts.net')
    monkeypatch.setenv('HERMES_SCHOOL_HTTPS', '1')
    app = create_app({'TESTING': True})
    client = app.test_client()
    response = client.get('/login', base_url='https://school.example.ts.net')
    assert response.status_code == 200
    cookie = response.headers['Set-Cookie']
    assert '; Secure;' in cookie
    assert '; HttpOnly;' in cookie
    assert '; SameSite=Strict' in cookie
    assert client.get('/login', base_url='https://other.example.ts.net').status_code == 400
    assert client.get('/login', base_url='https://school.example.ts.net.evil.test').status_code == 400


def test_desktop_http_remains_available(monkeypatch):
    monkeypatch.delenv('HERMES_SCHOOL_TRUSTED_HOSTS', raising=False)
    monkeypatch.setenv('HERMES_SCHOOL_HTTPS', '0')
    response = create_app({'TESTING': True}).test_client().get('/login')
    assert response.status_code == 200
    assert '; Secure;' not in response.headers['Set-Cookie']


@pytest.mark.parametrize('host', ['.example.ts.net', '*.ts.net', 'https://example.ts.net', 'example.ts.net/path'])
def test_reject_broad_or_invalid_host_configuration(monkeypatch, host):
    monkeypatch.setenv('HERMES_SCHOOL_TRUSTED_HOSTS', host)
    with pytest.raises(ValueError):
        create_app({'TESTING': True})
