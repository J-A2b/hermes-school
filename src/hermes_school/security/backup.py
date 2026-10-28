import io
import json
import sqlite3
import tempfile
import zipfile
import os
from contextlib import closing
from pathlib import Path
from cryptography.fernet import Fernet
from hermes_school.config import data_dir, private_mkdir
from hermes_school.storage.db import connect


def backup(destination, key):
    """Consistent SQLite snapshot + immutable document blobs. Secrets excluded."""
    stream = io.BytesIO()
    with tempfile.TemporaryDirectory() as temp:
        snapshot = Path(temp) / 'school.sqlite'
        with connect() as db, closing(sqlite3.connect(snapshot)) as target:
            db.backup(target)
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, 'school.sqlite')
            for path in (data_dir() / 'documents').glob('*'):
                if path.is_file() and len(path.name) == 64:
                    archive.write(path, 'documents/' + path.name)
    target = Path(destination)
    # Atomic replacement keeps the previous generation intact if writing fails.
    fd, temporary = tempfile.mkstemp(prefix='.school-backup-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(Fernet(key).encrypt(stream.getvalue()))
            output.flush()
            os.fsync(output.fileno())
        Path(temporary).chmod(0o600)
        os.replace(temporary, target)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def restore(archive_path, key, destination):
    """Restore into a NEW directory only, never overwrite a live database."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError('La destination doit être nouvelle')
    blob = Fernet(key).decrypt(Path(archive_path).read_bytes())
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        for entry in archive.infolist():
            parts = Path(entry.filename).parts
            valid = entry.filename == 'school.sqlite' or (len(parts) == 2 and parts[0] == 'documents' and len(parts[1]) == 64 and all(c in '0123456789abcdef' for c in parts[1]))
            if not valid or entry.file_size > 100_000_000:
                raise ValueError('Archive invalide')
        private_mkdir(destination)
        archive.extractall(destination)
    for path in destination.rglob('*'):
        path.chmod(0o700 if path.is_dir() else 0o600)
    with closing(sqlite3.connect(destination / 'school.sqlite')) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Intégrité SQLite incorrecte')
