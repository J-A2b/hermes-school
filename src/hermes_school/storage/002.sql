CREATE TABLE IF NOT EXISTS sync_modules(source TEXT NOT NULL, account TEXT NOT NULL, kind TEXT NOT NULL,
 completed_at TEXT NOT NULL, PRIMARY KEY(source,account,kind));
CREATE TABLE IF NOT EXISTS document_links(source_id TEXT NOT NULL, account TEXT NOT NULL,
 document_id INTEGER NOT NULL REFERENCES documents(id), record_id INTEGER REFERENCES records(id), PRIMARY KEY(source_id,account));
CREATE TABLE IF NOT EXISTS availability(id INTEGER PRIMARY KEY, starts_at TEXT NOT NULL, ends_at TEXT NOT NULL, label TEXT NOT NULL);
ALTER TABLE tasks ADD COLUMN due_date TEXT;
ALTER TABLE tasks ADD COLUMN scheduled_at TEXT;
INSERT OR IGNORE INTO migrations VALUES(2);
