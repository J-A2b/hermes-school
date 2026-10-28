CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS records(
 id INTEGER PRIMARY KEY, source TEXT NOT NULL, account TEXT NOT NULL, kind TEXT NOT NULL,
 source_id TEXT NOT NULL, subject TEXT NOT NULL DEFAULT '', title TEXT NOT NULL DEFAULT '',
 date TEXT, payload TEXT NOT NULL, fingerprint TEXT NOT NULL, first_seen TEXT NOT NULL,
 last_synced TEXT NOT NULL, UNIQUE(source,account,kind,source_id));
CREATE INDEX IF NOT EXISTS records_kind_date ON records(kind,date);
CREATE INDEX IF NOT EXISTS records_subject ON records(subject);
CREATE TABLE IF NOT EXISTS change_events(id INTEGER PRIMARY KEY, record_id INTEGER NOT NULL REFERENCES records(id),
 action TEXT NOT NULL, old_payload TEXT, new_payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sync_runs(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, summary TEXT);
CREATE TABLE IF NOT EXISTS source_references(id INTEGER PRIMARY KEY, record_id INTEGER NOT NULL UNIQUE REFERENCES records(id), endpoint TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, record_id INTEGER REFERENCES records(id), title TEXT NOT NULL,
 done INTEGER NOT NULL DEFAULT 0, estimated_minutes INTEGER NOT NULL DEFAULT 30, priority INTEGER NOT NULL DEFAULT 2);
CREATE UNIQUE INDEX IF NOT EXISTS tasks_record ON tasks(record_id) WHERE record_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS study_sessions(id INTEGER PRIMARY KEY, subject TEXT NOT NULL, work_type TEXT NOT NULL,
 planned_minutes INTEGER NOT NULL, actual_minutes INTEGER NOT NULL, difficulty INTEGER NOT NULL, date TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS weekly_plans(id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, context TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, record_id INTEGER REFERENCES records(id), name TEXT NOT NULL,
 sha256 TEXT UNIQUE NOT NULL, media_type TEXT NOT NULL, extracted_text TEXT NOT NULL DEFAULT '', provenance TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, change_id INTEGER NOT NULL UNIQUE REFERENCES change_events(id),
 status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, sent_at TEXT, error TEXT);
CREATE VIEW IF NOT EXISTS subjects AS SELECT DISTINCT subject FROM records WHERE subject != '';
CREATE VIEW IF NOT EXISTS grades AS SELECT * FROM records WHERE kind='grades';
CREATE VIEW IF NOT EXISTS grade_history AS SELECT c.* FROM change_events c JOIN records r ON r.id=c.record_id WHERE r.kind='grades';
CREATE VIEW IF NOT EXISTS assignments AS SELECT * FROM records WHERE kind='assignments';
CREATE VIEW IF NOT EXISTS assessments AS SELECT * FROM records WHERE kind='assessments';
CREATE VIEW IF NOT EXISTS lessons AS SELECT * FROM records WHERE kind='lessons';
CREATE VIEW IF NOT EXISTS messages AS SELECT * FROM records WHERE kind='messages';
CREATE VIEW IF NOT EXISTS timetable_events AS SELECT * FROM records WHERE kind='timetable';
INSERT OR IGNORE INTO migrations VALUES(1);
