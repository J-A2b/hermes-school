from datetime import datetime, time
from zoneinfo import ZoneInfo
from hermes_school.config import settings
from hermes_school.storage.db import connect


def quiet(at=None):
    cfg = settings()
    current = (at or datetime.now(ZoneInfo('Europe/Paris'))).astimezone(ZoneInfo('Europe/Paris')).time().replace(tzinfo=None)
    start, end = time.fromisoformat(cfg['quiet_start']), time.fromisoformat(cfg['quiet_end'])
    return start <= current < end if start < end else current >= start or current < end if start != end else False


def pending(at=None):
    if quiet(at):
        return []
    with connect() as db:
        return [dict(r) | {'event': 'assessment_discovered', 'publication_verified': False}
                for r in db.execute("SELECT * FROM notifications WHERE status='pending' ORDER BY id LIMIT 50")]
