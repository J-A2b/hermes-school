import os
import stat
import pytest
from hermes_school.config import private_mkdir


@pytest.mark.skipif(os.name != 'nt', reason='Windows ACL regression')
def test_windows_data_folder_keeps_inherited_acl(tmp_path):
    import subprocess
    folder = tmp_path / 'school'
    private_mkdir(folder)
    # 0700 on Python 3.13+ disables ACL inheritance, locking out another
    # identity (e.g. the user after Codex creates the directory).
    script = '(Get-Acl -LiteralPath $env:HERMES_TEST_ACL_PATH).AreAccessRulesProtected'
    result = subprocess.run(['powershell', '-NoProfile', '-Command', script], env=dict(os.environ, HERMES_TEST_ACL_PATH=str(folder)), capture_output=True, text=True, check=True)
    assert result.stdout.strip() == 'False'


@pytest.mark.skipif(os.name == 'nt', reason='POSIX mode')
def test_posix_data_folder_is_private(tmp_path):
    folder = tmp_path / 'school'
    private_mkdir(folder)
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
