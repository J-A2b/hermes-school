import os
import json
from pathlib import Path


def private_mkdir(path):
    # Python 3.13+ maps mode 0700 to a protected Windows ACL for the
    # creating identity. Inherit the user's directory ACL on Windows;
    # keep strict POSIX permissions on the Debian server.
    path.mkdir(parents=True, exist_ok=True, mode=0o777 if os.name == 'nt' else 0o700)


def data_dir():
    path = Path(os.environ.get("HERMES_SCHOOL_DATA", "data")).resolve()
    private_mkdir(path)
    return path


def private_write(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    path.chmod(0o600)


def secret():
    import secrets
    path = data_dir() / "session.key"
    if not path.exists():
        private_write(path, secrets.token_hex(32))
    return path.read_text().strip()


def settings():
    path = data_dir() / "settings.json"
    defaults = {"quiet_start": "22:00", "quiet_end": "07:00", "sync_times": "07:00,12:00,18:00", "friday_time": "19:00", "retention_days": 365}
    if path.exists():
        defaults.update(json.loads(path.read_text(encoding="utf-8")))
    return defaults
