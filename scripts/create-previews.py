"""Generate publication images from explicit synthetic demo data only.

Requires Playwright + Chromium in the interpreter running this script.
Use --python to select the application's virtualenv interpreter.
"""
import argparse
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', default=str(root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')))
    args = parser.parse_args()
    output = root / 'docs/images'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='school-public-demo-') as folder:
        env = dict(os.environ, HERMES_SCHOOL_DATA=folder, PYTHONPATH=str(root / 'src'), PYTHONIOENCODING='utf-8', HERMES_SCHOOL_HTTPS='0', HERMES_SCHOOL_TRUSTED_HOSTS='')
        seed = "from hermes_school.cli import demo; from hermes_school.config import private_write,data_dir; from hermes_school.storage.db import migrate; from werkzeug.security import generate_password_hash; migrate(); demo(); private_write(data_dir()/'password.hash',generate_password_hash('synthetic-preview-only'))"
        subprocess.run([args.python, '-c', seed], check=True, env=env, cwd=root)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen([args.python, '-m', 'hermes_school.cli', 'dashboard', '--port', str(port)], env=env, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            url = f'http://127.0.0.1:{port}'
            for _ in range(60):
                try:
                    urllib.request.urlopen(url + '/login', timeout=1)
                    break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError('Demo server failed to start')
                    time.sleep(.2)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={'width': 1440, 'height': 1050}, device_scale_factor=1)
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(url + '/login')
                page.get_by_label('Mot de passe du dashboard').fill('synthetic-preview-only')
                page.get_by_role('button', name='Se connecter').click()
                page.wait_for_url(url + '/')
                assert 'DÉMONSTRATION' in page.locator('.banner').inner_text()
                page.screenshot(path=str(output / 'dashboard-desktop.png'))
                page.goto(url + '/page/grades')
                page.get_by_role('button', name='Changer le thème').click()
                page.screenshot(path=str(output / 'grades-dark.png'))
                page.get_by_role('button', name='Changer le thème').click()
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto(url + '/')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path=str(output / 'dashboard-mobile.png'))
                assert not errors, errors
                browser.close()
            print('Three synthetic screenshots generated; desktop/mobile rendering verified.')
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    main()
