"""HTTP adapter. No remote write except interactive authentication."""
import json
import os
import time
from datetime import date, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo
from datetime import datetime
import requests
from hermes_school.models.normalize import grade, local_date, decode, plain_text


class Source(Protocol):
    def fetch(self, kind: str) -> list[dict]: ...


class APIError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(f'ÉcoleDirecte : code {code}. Intervention ou reconnexion nécessaire.')


class Client:
    base = 'https://api.ecoledirecte.com/v3/'

    def __init__(self, token='', student='', version=None, session=None):
        if student and not str(student).isdigit():
            raise ValueError('Identifiant élève invalide')
        self.student = str(student)
        self.version = version or os.environ.get('ED_API_VERSION', '4.101.4')
        self.http = session or requests.Session()
        self.http.headers.update({'User-Agent': 'HermesSchool/0.1 (local personal client)', 'X-Token': token})

    def request(self, path, body=None, verb='get', accepted=(200,)):
        for attempt in range(3):
            try:
                response = self.http.post(self.base + path, params={'verbe': verb, 'v': self.version},
                                          data={'data': json.dumps(body or {})}, timeout=(10, 30), allow_redirects=False)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                if response.status_code != 200:
                    raise APIError(response.status_code)
                result = response.json()
                if not isinstance(result, dict) or not isinstance(result.get('code'), int):
                    raise APIError('schema')
                if result.get('token'):
                    self.http.headers['X-Token'] = result['token']
                if result['code'] not in accepted:
                    raise APIError(result['code'])
                return result
            except (requests.Timeout, requests.ConnectionError):
                if attempt == 2:
                    raise APIError('network') from None
                time.sleep(2 ** attempt)
            except (requests.RequestException, ValueError):
                raise APIError('response') from None

    def login(self, username, password, fa=None, answer=None):
        r = self.http.get(self.base + 'login.awp', params={'gtk': 1, 'v': self.version}, timeout=20, allow_redirects=False)
        if r.status_code != 200:
            raise APIError(r.status_code)
        gtk = self.http.cookies.get('GTK')
        if gtk:
            self.http.headers['X-Gtk'] = gtk
        body = {'identifiant': username, 'motdepasse': password, 'isReLogin': False, 'uuid': ''}
        if fa:
            body['fa'] = fa
        result = self.request('login.awp', body, 'post', accepted=(200, 250))
        if result['code'] == 250:
            if answer is None:
                raise APIError(250)
            challenge = self.request('connexion/doubleauth.awp')['data']
            choice = answer(decode(challenge['question']), [decode(p) for p in challenge['propositions']])
            if not isinstance(choice, int) or not 0 <= choice < len(challenge['propositions']):
                raise ValueError('Choix invalide')
            factors = self.request('connexion/doubleauth.awp', {'choix': challenge['propositions'][choice]}, 'post')['data']
            body['fa'] = [{'cn': factors['cn'], 'cv': factors['cv']}]
            result = self.request('login.awp', body, 'post')
            fa = body['fa']
        accounts = result.get('data', {}).get('accounts')
        if not isinstance(accounts, list):
            raise APIError('accounts-schema')
        return accounts, fa

    def fetch(self, kind):
        sid = self.student
        if not sid:
            raise ValueError('Élève non sélectionné')
        if kind == 'grades':
            path = f'eleves/{sid}/notes.awp'
            data = self.request(path, {'anneeScolaire': ''})['data']
            if not isinstance(data, dict) or not isinstance(data.get('notes'), list):
                raise APIError('grades-schema')
            # Honor publication flags; do not derive hidden bulletin values.
            cfg = data.get('parametrage', {})
            if cfg.get('affichageNote') is False:
                return []
            closed = {p.get('codePeriode') for p in data.get('periodes', []) if p.get('cloture') is True}
            notes = [n for n in data['notes'] if n.get('visible', True) is not False and
                     (not cfg.get('noteUniquementPeriodeCloture') or n.get('codePeriode') in closed)]
            if cfg.get('affichageMoyenneDevoir') is False:
                notes = [{k: v for k, v in n.items() if k not in ('moyenneClasse', 'minClasse', 'maxClasse')} for n in notes]
            return [grade(n, path) for n in notes]
        if kind == 'timetable':
            path = f'E/{sid}/emploidutemps.awp'
            today = datetime.now(ZoneInfo('Europe/Paris')).date()
            data = self.request(path, {'dateDebut': today.isoformat(), 'dateFin': (today + timedelta(days=21)).isoformat(), 'avecTrous': False})['data']
            if not isinstance(data, list):
                raise APIError('timetable-schema')
            return [{'source_id': str(r['id']), 'title': r.get('text', ''), 'subject': r.get('matiere', ''),
                     'date': local_date(r['start_date']), 'end': local_date(r['end_date']), 'raw': r, 'endpoint': path} for r in data]
        if kind in ('assignments', 'assessments', 'lessons'):
            return self.homework()[kind]
        raise NotImplementedError('Collecte distante non validée pour ce module')

    def attachment(self, file_id):
        """Download only a CDT attachment identifier returned by an authorized lesson."""
        from hermes_school.documents.library import MAX_SIZE
        if not str(file_id).isdigit():
            raise ValueError('Identifiant de pièce jointe invalide')
        response = self.http.post(self.base + 'telechargement.awp',
            params={'verbe': 'get', 'v': self.version, 'leTypeDeFichier': 'FICHIER_CDT', 'fichierId': str(file_id)},
            data={'data': json.dumps({'forceDownload': 0})}, timeout=(10, 30), stream=True, allow_redirects=False)
        try:
            if response.status_code != 200:
                raise APIError(response.status_code)
            blob = bytearray()
            for chunk in response.iter_content(65536):
                blob.extend(chunk)
                if len(blob) > MAX_SIZE:
                    raise ValueError('Document trop volumineux')
            return bytes(blob)
        finally:
            response.close()

    def homework(self):
        path = f'Eleves/{self.student}/cahierdetexte.awp'
        days = self.request(path)['data']
        if not isinstance(days, dict):
            raise APIError('homework-schema')
        result = {'assignments': [], 'assessments': [], 'lessons': []}
        for due, entries in days.items():
            local_date(due)
            if not isinstance(entries, list):
                raise APIError('homework-schema')
            detail_path = f'Eleves/{self.student}/cahierdetexte/{due}.awp'
            detail = self.request(detail_path)['data']
            if not isinstance(detail, dict) or not isinstance(detail.get('matieres'), list):
                raise APIError('homework-detail-schema')
            by_id = {str(m.get('id')): m for m in detail['matieres']}
            for entry in entries:
                eid = str(entry['idDevoir'])
                mat = by_id.get(eid, {})
                work = mat.get('aFaire', {}) or {}
                item = {'source_id': eid, 'title': entry.get('matiere', '') + ' — travail à faire',
                        'subject': entry.get('matiere', ''), 'date': due,
                        'description': plain_text(work.get('contenu', '')), 'raw': entry,
                        'detail': mat, 'endpoint': detail_path}
                result['assignments'].append(item)
                if entry.get('interrogation') is True:
                    result['assessments'].append(item)
            for mat in detail['matieres']:
                if mat.get('contenuDeSeance'):
                    result['lessons'].append({'source_id': f"{due}:{mat['id']}", 'date': due, 'title': mat.get('matiere', ''),
                                              'subject': mat.get('matiere', ''), 'description': plain_text(mat['contenuDeSeance'].get('contenu', '')),
                                              'raw': mat, 'endpoint': detail_path})
        return result
