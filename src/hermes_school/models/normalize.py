import base64
import math
from html.parser import HTMLParser
from datetime import datetime
from zoneinfo import ZoneInfo


def number(value):
    try:
        result = float(str(value).replace(',', '.').strip())
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def local_date(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if len(value) == 10:
        return dt.date().isoformat()
    return (dt.replace(tzinfo=ZoneInfo('Europe/Paris')) if dt.tzinfo is None else dt).isoformat()


def decode(value):
    try:
        return base64.b64decode(value, validate=True).decode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return value


def plain_text(value):
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts, self.skip = [], 0
        def handle_starttag(self, tag, attrs):
            if tag in ('script', 'style'):
                self.skip += 1
            if tag in ('p', 'div', 'br', 'li'):
                self.parts.append('\n')
        def handle_endtag(self, tag):
            if tag in ('script', 'style') and self.skip:
                self.skip -= 1
        def handle_data(self, data):
            if not self.skip:
                self.parts.append(data)
    parser = Text()
    parser.feed(decode(value))
    return ''.join(parser.parts).strip()


def grade(raw, endpoint):
    if not isinstance(raw, dict) or 'id' not in raw or 'valeur' not in raw:
        raise ValueError('Structure de note invalide')
    score, maximum = number(raw['valeur']), number(raw.get('noteSur'))
    return {'source_id': str(raw['id']), 'subject': raw.get('libelleMatiere', ''),
            'title': raw.get('devoir', ''), 'date': local_date(raw.get('date')),
            'score': score, 'maximum': maximum,
            'out_of_20': score * 20 / maximum if score is not None and maximum and maximum > 0 and not raw.get('enLettre') else None,
            'coefficient': number(raw.get('coef')), 'period': raw.get('codePeriode'),
            'class_average': number(raw.get('moyenneClasse')), 'raw': raw, 'endpoint': endpoint}
