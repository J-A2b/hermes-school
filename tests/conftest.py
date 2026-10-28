import pytest
from hermes_school.storage.db import migrate


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_SCHOOL_DATA', str(tmp_path / 'data'))
    migrate()
