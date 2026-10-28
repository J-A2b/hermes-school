import io
import zipfile
import pytest
from docx import Document
from pypdf import PdfWriter
from hermes_school.documents.library import store, search
from hermes_school.storage.db import connect
from hermes_school.security.backup import restore
from cryptography.fernet import Fernet


def test_extract_docx_and_pdf_without_ocr():
    document = Document()
    document.add_paragraph('Exercices de géométrie')
    stream = io.BytesIO()
    document.save(stream)
    store(stream.getvalue(), 'cours.docx', 'fixture synthétique')
    assert search('géométrie')
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    stream = io.BytesIO()
    writer.write(stream)
    store(stream.getvalue(), 'page-blanche.pdf', 'fixture synthétique sans texte')
    with connect() as db:
        assert db.execute("SELECT extracted_text FROM documents WHERE name='page-blanche.pdf'").fetchone()[0] == ''


def test_restore_rejects_path_traversal(tmp_path):
    key = Fernet.generate_key()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as z:
        z.writestr('../outside.txt', b'not allowed')
    archive = tmp_path / 'malicious.enc'
    archive.write_bytes(Fernet(key).encrypt(stream.getvalue()))
    with pytest.raises(ValueError):
        restore(archive, key, tmp_path / 'restored')
    assert not (tmp_path / 'outside.txt').exists()
