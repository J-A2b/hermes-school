import hashlib
import io
import re
from pathlib import Path
from urllib.parse import urlsplit
import requests
from hermes_school.config import data_dir, private_mkdir
from hermes_school.storage.db import connect

MAX_SIZE = 20 * 1024 * 1024


def store(blob, name, provenance, record_id=None):
    if len(blob) > MAX_SIZE:
        raise ValueError('Document trop volumineux')
    suffix = Path(name).suffix.lower()
    if suffix not in ('.pdf', '.docx', '.txt'):
        raise ValueError('Format non autorisé')
    text = ''
    if suffix == '.pdf':
        if not blob.startswith(b'%PDF-'):
            raise ValueError('PDF invalide')
        from pypdf import PdfReader
        text = '\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(blob)).pages)
    elif suffix == '.docx':
        import zipfile
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_SIZE * 3:
                raise ValueError('DOCX décompressé trop volumineux')
        from docx import Document
        text = '\n'.join(p.text for p in Document(io.BytesIO(blob)).paragraphs)
    else:
        text = blob.decode('utf-8')
    digest = hashlib.sha256(blob).hexdigest()
    folder = data_dir() / 'documents'
    private_mkdir(folder)
    path = folder / digest
    path.write_bytes(blob)
    path.chmod(0o600)
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO documents(record_id,name,sha256,media_type,extracted_text,provenance) VALUES(?,?,?,?,?,?)',
                   (record_id, Path(name).name, digest, {'.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.txt': 'text/plain'}[suffix], text[:2_000_000], provenance))
        rid = db.execute('SELECT id FROM documents WHERE sha256=?', (digest,)).fetchone()[0]
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='document_search'").fetchone():
            db.execute('DELETE FROM document_search WHERE document_id=?', (rid,))
            db.execute('INSERT INTO document_search VALUES(?,?)', (rid, text[:2_000_000]))
    return rid


def download(url, name, provenance, record_id=None):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not re.fullmatch(r'doc[0-9]+\.ecoledirecte\.com', parsed.hostname or '') or parsed.port not in (None, 443) or parsed.username:
        raise ValueError('Domaine de document non autorisé')
    with requests.get(url, stream=True, timeout=(10, 30), allow_redirects=False) as response:
        if response.status_code != 200:
            raise ValueError('Téléchargement refusé')
        blob = bytearray()
        for chunk in response.iter_content(65536):
            blob.extend(chunk)
            if len(blob) > MAX_SIZE:
                raise ValueError('Document trop volumineux')
    return store(bytes(blob), name, provenance, record_id)


def search(query: str='') -> list[dict]:
    with connect() as db:
        # LIKE fallback also works on SQLite builds without FTS5.
        return [dict(r) for r in db.execute('SELECT id,name,sha256,media_type,provenance,substr(extracted_text,1,300) AS excerpt FROM documents WHERE name LIKE ? OR extracted_text LIKE ? LIMIT 100', ('%' + query[:200] + '%',) * 2)]
