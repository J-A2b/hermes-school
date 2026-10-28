import argparse
import getpass
import json
import os
import platform
import shutil
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from hermes_school.config import data_dir, private_write
from hermes_school.storage.db import connect, migrate, now, upsert


def output(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def authenticate(interactive=False):
    from hermes_school.connectors.ecoledirecte.client import Client
    from hermes_school.security.backup import Fernet
    path = data_dir() / 'credentials.enc'
    key_path = data_dir() / 'credentials.key'
    saved = {}
    if path.exists():
        saved = json.loads(Fernet(key_path.read_bytes()).decrypt(path.read_bytes()))
    username = input('Identifiant ÉcoleDirecte : ') if interactive else saved.get('username')
    password = getpass.getpass('Mot de passe ÉcoleDirecte : ') if interactive else saved.get('password')
    if not username or not password:
        raise ValueError('Exécutez hermes-school login dans un terminal privé')
    client = Client()
    def answer(question, choices):
        print(question)
        for i, choice in enumerate(choices):
            print(f'{i + 1}. {choice}')
        return int(input('Votre choix : ')) - 1
    accounts, fa = client.login(username, password, saved.get('fa'), answer if interactive else None)
    students = []
    for account in accounts:
        if account.get('typeCompte') == 'E':
            students.append(account)
        students.extend(account.get('profile', {}).get('eleves', []))
    if not students:
        raise ValueError('Aucun élève accessible')
    selected = saved.get('student')
    if interactive:
        for i, student in enumerate(students):
            print(f"{i + 1}. {student.get('prenom', '')} {student.get('nom', '')} ({student['id']})")
        selected = str(students[int(input('Numéro de l’élève : ')) - 1]['id'])
    if selected not in [str(s['id']) for s in students]:
        raise ValueError('Élève inaccessible : refaire login')
    client.student = selected
    if interactive:
        if not key_path.exists():
            private_write(key_path, Fernet.generate_key().decode())
        payload = {'username': username, 'password': password, 'fa': fa, 'student': selected}
        path.write_bytes(Fernet(key_path.read_bytes()).encrypt(json.dumps(payload).encode()))
        path.chmod(0o600)
    return client


def demo():
    if (data_dir() / 'credentials.enc').exists():
        raise ValueError('La démonstration exige un répertoire séparé sans identifiants')
    with connect() as db:
        if db.execute("SELECT 1 FROM records WHERE source!='demo'").fetchone():
            raise ValueError('La démonstration exige une base dédiée')
        today = datetime.now(ZoneInfo('Europe/Paris')).date()
        for i, (subject, title, score) in enumerate([('Mathématiques', 'Fonctions et dérivées', 16), ('Français', 'Analyse de texte', 14.5), ('Anglais', 'Expression écrite', 18), ('Physique-Chimie', 'Énergie et mouvement', 15)]):
            item = {'source_id': str(i), 'subject': subject, 'title': title, 'date': (today - timedelta(days=i * 3)).isoformat(), 'score': score, 'maximum': 20, 'out_of_20': score, 'coefficient': 1, 'period': 'T1', 'class_average': 12.5, 'raw': {'valeur': str(score)}, 'endpoint': 'demo'}
            upsert(db, 'demo', 'grades', item, True, 'demo')
            item = {'source_id': str(i), 'subject': subject, 'title': 'Réviser : ' + title, 'date': (today + timedelta(days=i + 1)).isoformat(), 'description': 'Relire le cours et préparer les exercices 1 à 4. Donnée de démonstration.', 'endpoint': 'demo'}
            upsert(db, 'demo', 'assignments', item, True, 'demo')
            if i < 2:
                upsert(db, 'demo', 'assessments', item, True, 'demo')
            start = datetime.fromisoformat((today + timedelta(days=i//2)).isoformat() + ('T09:00:00' if i%2==0 else 'T11:00:00')).replace(tzinfo=ZoneInfo('Europe/Paris')).isoformat()
            upsert(db, 'demo', 'timetable', {'source_id': str(i), 'subject': subject, 'title': subject, 'date': start,
                   'end': start.replace('09:00', '10:00').replace('11:00', '12:00'), 'raw': {'prof': 'Professeur exemple', 'salle': 'B12', 'isAnnule': i==3}, 'endpoint': 'demo'}, True, 'demo')
    private_write(data_dir() / 'DEMO', 'Données fictives')


def main():
    parser = argparse.ArgumentParser(description='Hermes School — collecteur scolaire privé')
    parser.add_argument('command', choices=['doctor', 'init', 'login', 'sync', 'status', 'dashboard', 'backup', 'restore', 'keygen', 'demo', 'mcp', 'friday', 'timers', 'study', 'document'])
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--output')
    parser.add_argument('--input')
    parser.add_argument('--key-file')
    parser.add_argument('--subject', default='')
    parser.add_argument('--minutes', type=int, default=30)
    parser.add_argument('--planned', type=int, default=30)
    parser.add_argument('--difficulty', type=int, default=3)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        migrate()
        if args.command == 'doctor':
            output({'platform': platform.platform(), 'python': sys.version.split()[0], 'sqlite': sqlite3.sqlite_version,
                    'data_dir': str(data_dir()), 'disk_free_bytes': shutil.disk_usage(data_dir()).free,
                    'systemd': bool(shutil.which('systemctl')), 'hermes': bool(shutil.which('hermes')),
                    'server_audited': False, 'debian_audit': 'bash scripts/audit-debian.sh'})
        elif args.command == 'init':
            from werkzeug.security import generate_password_hash
            password = getpass.getpass('Nouveau mot de passe dashboard (12 caractères minimum) : ')
            if len(password) < 12:
                raise ValueError('Mot de passe trop court')
            if password != getpass.getpass('Confirmer : '):
                raise ValueError('Confirmation différente')
            private_write(data_dir() / 'password.hash', generate_password_hash(password))
            print('Dashboard initialisé.')
        elif args.command == 'login':
            if (data_dir() / 'DEMO').exists():
                raise ValueError('Utilisez un répertoire de données réel distinct de la démonstration')
            authenticate(True)
            print('Connexion validée, secrets chiffrés localement. Protégez aussi credentials.key.')
        elif args.command == 'sync':
            from hermes_school.sync.service import synchronize
            client = authenticate()
            result = synchronize(client, client.student)
            from hermes_school.sync.attachments import synchronize_documents
            result['documents'] = synchronize_documents(client)
            if result['documents']['failed']:
                result['status'] = 'partial'
            with connect() as db:
                db.execute('UPDATE sync_runs SET status=?,summary=? WHERE id=?', (result['status'], json.dumps(result), result['id']))
            output(result)
            if result['status'] != 'success':
                return 1
        elif args.command == 'status':
            from hermes_school.integrations.mcp.server import status
            output(status())
        elif args.command == 'dashboard':
            from waitress import serve
            from hermes_school.dashboard.app import create_app
            print(f'Dashboard : http://127.0.0.1:{args.port}', flush=True)
            serve(create_app(), host='127.0.0.1', port=args.port, threads=4)
        elif args.command == 'demo':
            demo()
            print('Démonstration chargée explicitement.')
        elif args.command == 'mcp':
            from hermes_school.integrations.mcp.server import run
            run()
        elif args.command == 'friday':
            from hermes_school.analytics.planning import weekend_context
            ctx = weekend_context()
            with connect() as db:
                db.execute('INSERT INTO weekly_plans(created_at,context) VALUES(?,?)', (now(), json.dumps(ctx)))
            if args.output:
                private_write(Path(args.output), json.dumps(ctx, ensure_ascii=False, indent=2))
            else:
                output(ctx)
        elif args.command == 'keygen':
            from cryptography.fernet import Fernet
            if not args.output or Path(args.output).exists():
                raise ValueError('Indiquez un nouveau fichier avec --output')
            private_write(Path(args.output), Fernet.generate_key().decode())
        elif args.command in ('backup', 'restore'):
            from hermes_school.security.backup import backup, restore
            if not args.key_file or not args.output:
                raise ValueError('--key-file et --output requis')
            key = Path(args.key_file).read_bytes().strip()
            if args.command == 'backup':
                backup(args.output, key)
            else:
                if not args.input:
                    raise ValueError('--input requis')
                restore(args.input, key, args.output)
            print('Opération terminée.')
        elif args.command == 'timers':
            from hermes_school.jobs.timers import generate
            generate(Path(args.output or 'generated-systemd'))
        elif args.command == 'study':
            if not args.subject or not 1 <= args.minutes <= 1440 or not 1 <= args.planned <= 1440 or not 1 <= args.difficulty <= 5:
                raise ValueError('Matière, durées 1..1440, difficulté 1..5 requises')
            with connect() as db:
                db.execute('INSERT INTO study_sessions(subject,work_type,planned_minutes,actual_minutes,difficulty,date) VALUES(?,?,?,?,?,?)', (args.subject, 'homework', args.planned, args.minutes, args.difficulty, now()))
        elif args.command == 'document':
            from hermes_school.documents.library import store
            if not args.input:
                raise ValueError('--input requis')
            path = Path(args.input)
            output({'document_id': store(path.read_bytes(), path.name, 'import local autorisé')})
        return 0
    except Exception as exc:
        # Do not print exception details from HTTP, credentials, documents or crypto.
        print(f'Opération interrompue ({type(exc).__name__}). Consultez docs/OPERATIONS.md ; aucun secret affiché.', file=sys.stderr)
        if isinstance(exc, ValueError):
            print('Vérifiez les paramètres et la configuration locale.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
