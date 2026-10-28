from pathlib import Path
from hermes_school.config import settings


def generate(folder: Path):
    cfg = settings()
    folder.mkdir(parents=True, exist_ok=True)
    for name, calendars in [('sync', [f'*-*-* {t}:00 Europe/Paris' for t in cfg['sync_times'].split(',')]),
                            ('friday', [f'Fri *-*-* {cfg["friday_time"]}:00 Europe/Paris'])]:
        content = '[Unit]\nDescription=Hermes School ' + name + '\n[Timer]\n' + ''.join('OnCalendar=' + c + '\n' for c in calendars) + 'Persistent=true\nRandomizedDelaySec=60\n[Install]\nWantedBy=timers.target\n'
        (folder / f'hermes-school-{name}.timer').write_text(content)
    print(f'Timers générés dans {folder}. Les examiner puis les installer manuellement.')
