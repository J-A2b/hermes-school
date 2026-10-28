import json
from pathlib import Path
from hermes_school.storage.db import connect, records
from hermes_school.documents.library import store


def synchronize_documents(client):
    summary = {'created': 0, 'cached': 0, 'unsupported': 0, 'failed': 0}
    for record in records(limit=500):
        if record['account'] != client.student or record['source'] != 'ecoledirecte' or record['kind'] not in ('assignments', 'lessons'):
            continue
        raw = record['data'].get('detail') or record['data'].get('raw', {})
        containers = [raw.get('aFaire') or {}, raw.get('contenuDeSeance') or {}]
        for container in containers:
            for doc in container.get('documents', []):
                file_id, name = str(doc.get('id', '')), doc.get('libelle', '')
                if not file_id.isdigit() or Path(name).suffix.lower() not in ('.pdf', '.docx', '.txt'):
                    summary['unsupported'] += 1
                    continue
                with connect() as db:
                    existing = db.execute('SELECT 1 FROM document_links WHERE source_id=? AND account=?', (file_id, client.student)).fetchone()
                if existing:
                    summary['cached'] += 1
                    continue
                try:
                    provenance = json.dumps({'system': 'ecoledirecte', 'endpoint': record['data']['endpoint'], 'attachment_id': file_id, 'account': client.student})
                    doc_id = store(client.attachment(file_id), name, provenance, record['id'])
                    with connect() as db:
                        db.execute('INSERT OR IGNORE INTO document_links VALUES(?,?,?,?)', (file_id, client.student, doc_id, record['id']))
                    summary['created'] += 1
                except Exception:
                    summary['failed'] += 1
    return summary
