"""Optional browser QA; requires Playwright and an installed Chromium, no real data."""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
with tempfile.TemporaryDirectory(prefix='school-browser-') as folder:
    env = dict(os.environ, HERMES_SCHOOL_DATA=folder, PYTHONIOENCODING='utf-8')
    seed = "from hermes_school.cli import demo; from hermes_school.config import private_write,data_dir; from hermes_school.storage.db import migrate; from werkzeug.security import generate_password_hash; migrate(); demo(); private_write(data_dir()/'password.hash',generate_password_hash('browser-fixture-only'))"
    subprocess.run([str(python), '-c', seed], check=True, env=env)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([str(python), '-m', 'hermes_school.cli', 'dashboard', '--port', str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = f'http://127.0.0.1:{port}'
        for _ in range(50):
            try:
                urllib.request.urlopen(url + '/login', timeout=1)
                break
            except OSError:
                time.sleep(.2)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(url)
            page.get_by_label('Mot de passe du dashboard').fill('browser-fixture-only')
            page.get_by_role('button', name='Se connecter').click()
            page.wait_for_url(url + '/')
            assert page.get_by_role('heading', name='Accueil', exact=True).is_visible()
            assert 'DÉMONSTRATION' in page.locator('.banner').inner_text()
            artifact = root / 'docs' / 'dashboard-preview.png'
            page.screenshot(path=str(artifact), full_page=True)
            page.get_by_role('link', name='Notes', exact=False).first.click()
            page.wait_for_url('**/page/grades')
            assert page.locator('.grade').count() == 4
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.goto(url + '/page/organization')
            page.get_by_label('Nouvelle tâche').fill('Révision navigateur')
            page.get_by_role('button', name='Ajouter', exact=True).click()
            assert page.get_by_text('Révision navigateur').is_visible()
            assert not errors, errors
            browser.close()
            print('Browser QA: login, desktop overview, grades, mobile layout, task creation passed.')
    finally:
        process.terminate()
        process.wait(timeout=10)
