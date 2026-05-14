-- Roundbreak Career — full schema for fresh install.
-- After v1, additive changes go in app/migrations/NNN_*.sql.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE companies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    location   TEXT,
    type       TEXT NOT NULL CHECK (type IN ('prime','contractor','specialty','newspace','other')),
    website    TEXT,
    priority   INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 3),
    status     TEXT NOT NULL DEFAULT 'researching'
                  CHECK (status IN ('researching','watching','applied','interviewing','offered','accepted','passed','closed')),
    notes      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE company_openings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    url         TEXT,
    posted_date TEXT,
    found_date  TEXT NOT NULL DEFAULT (date('now')),
    status      TEXT NOT NULL DEFAULT 'open',
    notes       TEXT
);

CREATE TABLE contacts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    company_id          INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    role                TEXT,
    linkedin_url        TEXT,
    email               TEXT,
    phone               TEXT,
    location            TEXT,
    notes               TEXT,
    tags                TEXT,
    how_we_met          TEXT,
    warmth              INTEGER CHECK (warmth BETWEEN 1 AND 5),
    last_contact_date   TEXT,
    next_followup_date  TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE interactions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id         INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    date               TEXT NOT NULL DEFAULT (date('now')),
    channel            TEXT NOT NULL CHECK (channel IN ('email','linkedin','call','text','in-person','event','other')),
    summary            TEXT,
    follow_up_required INTEGER NOT NULL DEFAULT 0,
    follow_up_by       TEXT
);

CREATE TABLE project_stories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    problem_domain  TEXT,
    situation       TEXT,
    task            TEXT,
    action          TEXT,
    result          TEXT,
    technical       TEXT,
    keywords        TEXT,
    readiness       TEXT NOT NULL DEFAULT 'draft' CHECK (readiness IN ('draft','usable','polished')),
    times_practiced INTEGER NOT NULL DEFAULT 0,
    last_practiced  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE learning_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL CHECK (type IN ('book','chapter','article','paper','video','course','skill','reference')),
    title           TEXT NOT NULL,
    author          TEXT,
    source          TEXT,
    status          TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','reading','done','dropped')),
    priority        INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 3),
    notes_path      TEXT,
    date_started    TEXT,
    date_completed  TEXT,
    rating          INTEGER CHECK (rating BETWEEN 1 AND 5),
    tags            TEXT,
    key_takeaways   TEXT
);

CREATE TABLE actions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    description      TEXT,
    category         TEXT NOT NULL CHECK (category IN ('clearance','membership','network','learning','resume','interview','salary_research','admin','technical')),
    priority         TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('high','medium','low')),
    target_date      TEXT,
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','done','skipped')),
    date_completed   TEXT,
    completion_notes TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE salary_data (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source            TEXT NOT NULL CHECK (source IN ('h1b','levels','glassdoor','conversation','recruiter','offer','other')),
    company           TEXT,
    role              TEXT,
    level             TEXT,
    base_salary       REAL,
    bonus_target_pct  REAL,
    bonus_amount      REAL,
    equity_value      REAL,
    total_comp        REAL,
    location          TEXT,
    year              INTEGER,
    cleared           INTEGER NOT NULL DEFAULT 0,
    notes             TEXT,
    date_recorded     TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE resume_versions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    focus_area   TEXT,
    file_path    TEXT NOT NULL,
    date_created TEXT NOT NULL DEFAULT (date('now')),
    notes        TEXT,
    is_current   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE monthly_reviews (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    year                     INTEGER NOT NULL,
    month                    INTEGER NOT NULL,
    wins                     TEXT,
    misses                   TEXT,
    lessons                  TEXT,
    next_month_focus         TEXT,
    books_completed_count    INTEGER DEFAULT 0,
    actions_completed_count  INTEGER DEFAULT 0,
    contacts_added_count     INTEGER DEFAULT 0,
    stories_polished_count   INTEGER DEFAULT 0,
    date_completed           TEXT,
    UNIQUE(year, month)
);

CREATE TABLE field_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name  TEXT NOT NULL,
    record_id   INTEGER NOT NULL,
    field_name  TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT,
    changed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_contacts_company       ON contacts(company_id);
CREATE INDEX idx_contacts_followup      ON contacts(next_followup_date);
CREATE INDEX idx_contacts_last_contact  ON contacts(last_contact_date);
CREATE INDEX idx_interactions_contact   ON interactions(contact_id);
CREATE INDEX idx_openings_company       ON company_openings(company_id);
CREATE INDEX idx_actions_status         ON actions(status);
CREATE INDEX idx_actions_target_date    ON actions(target_date);
CREATE INDEX idx_learning_status        ON learning_items(status);
CREATE INDEX idx_field_history_record   ON field_history(table_name, record_id);

-- FTS5 virtual tables -------------------------------------------------------
CREATE VIRTUAL TABLE companies_fts USING fts5(
    name, notes,
    content='companies', content_rowid='id', tokenize='porter unicode61'
);
CREATE VIRTUAL TABLE contacts_fts USING fts5(
    name, role, notes, tags, how_we_met,
    content='contacts', content_rowid='id', tokenize='porter unicode61'
);
CREATE VIRTUAL TABLE stories_fts USING fts5(
    title, situation, task, action, result, technical, keywords,
    content='project_stories', content_rowid='id', tokenize='porter unicode61'
);
CREATE VIRTUAL TABLE actions_fts USING fts5(
    title, description, completion_notes,
    content='actions', content_rowid='id', tokenize='porter unicode61'
);
CREATE VIRTUAL TABLE learning_fts USING fts5(
    title, author, key_takeaways, tags,
    content='learning_items', content_rowid='id', tokenize='porter unicode61'
);

-- FTS sync triggers ---------------------------------------------------------
CREATE TRIGGER companies_ai AFTER INSERT ON companies BEGIN
    INSERT INTO companies_fts(rowid, name, notes) VALUES (new.id, new.name, new.notes);
END;
CREATE TRIGGER companies_ad AFTER DELETE ON companies BEGIN
    INSERT INTO companies_fts(companies_fts, rowid, name, notes) VALUES ('delete', old.id, old.name, old.notes);
END;
CREATE TRIGGER companies_au AFTER UPDATE ON companies BEGIN
    INSERT INTO companies_fts(companies_fts, rowid, name, notes) VALUES ('delete', old.id, old.name, old.notes);
    INSERT INTO companies_fts(rowid, name, notes) VALUES (new.id, new.name, new.notes);
END;

CREATE TRIGGER contacts_ai AFTER INSERT ON contacts BEGIN
    INSERT INTO contacts_fts(rowid, name, role, notes, tags, how_we_met)
        VALUES (new.id, new.name, new.role, new.notes, new.tags, new.how_we_met);
END;
CREATE TRIGGER contacts_ad AFTER DELETE ON contacts BEGIN
    INSERT INTO contacts_fts(contacts_fts, rowid, name, role, notes, tags, how_we_met)
        VALUES ('delete', old.id, old.name, old.role, old.notes, old.tags, old.how_we_met);
END;
CREATE TRIGGER contacts_au AFTER UPDATE ON contacts BEGIN
    INSERT INTO contacts_fts(contacts_fts, rowid, name, role, notes, tags, how_we_met)
        VALUES ('delete', old.id, old.name, old.role, old.notes, old.tags, old.how_we_met);
    INSERT INTO contacts_fts(rowid, name, role, notes, tags, how_we_met)
        VALUES (new.id, new.name, new.role, new.notes, new.tags, new.how_we_met);
END;

CREATE TRIGGER stories_ai AFTER INSERT ON project_stories BEGIN
    INSERT INTO stories_fts(rowid, title, situation, task, action, result, technical, keywords)
        VALUES (new.id, new.title, new.situation, new.task, new.action, new.result, new.technical, new.keywords);
END;
CREATE TRIGGER stories_ad AFTER DELETE ON project_stories BEGIN
    INSERT INTO stories_fts(stories_fts, rowid, title, situation, task, action, result, technical, keywords)
        VALUES ('delete', old.id, old.title, old.situation, old.task, old.action, old.result, old.technical, old.keywords);
END;
CREATE TRIGGER stories_au AFTER UPDATE ON project_stories BEGIN
    INSERT INTO stories_fts(stories_fts, rowid, title, situation, task, action, result, technical, keywords)
        VALUES ('delete', old.id, old.title, old.situation, old.task, old.action, old.result, old.technical, old.keywords);
    INSERT INTO stories_fts(rowid, title, situation, task, action, result, technical, keywords)
        VALUES (new.id, new.title, new.situation, new.task, new.action, new.result, new.technical, new.keywords);
END;

CREATE TRIGGER actions_ai AFTER INSERT ON actions BEGIN
    INSERT INTO actions_fts(rowid, title, description, completion_notes)
        VALUES (new.id, new.title, new.description, new.completion_notes);
END;
CREATE TRIGGER actions_ad AFTER DELETE ON actions BEGIN
    INSERT INTO actions_fts(actions_fts, rowid, title, description, completion_notes)
        VALUES ('delete', old.id, old.title, old.description, old.completion_notes);
END;
CREATE TRIGGER actions_au AFTER UPDATE ON actions BEGIN
    INSERT INTO actions_fts(actions_fts, rowid, title, description, completion_notes)
        VALUES ('delete', old.id, old.title, old.description, old.completion_notes);
    INSERT INTO actions_fts(rowid, title, description, completion_notes)
        VALUES (new.id, new.title, new.description, new.completion_notes);
END;

CREATE TRIGGER learning_ai AFTER INSERT ON learning_items BEGIN
    INSERT INTO learning_fts(rowid, title, author, key_takeaways, tags)
        VALUES (new.id, new.title, new.author, new.key_takeaways, new.tags);
END;
CREATE TRIGGER learning_ad AFTER DELETE ON learning_items BEGIN
    INSERT INTO learning_fts(learning_fts, rowid, title, author, key_takeaways, tags)
        VALUES ('delete', old.id, old.title, old.author, old.key_takeaways, old.tags);
END;
CREATE TRIGGER learning_au AFTER UPDATE ON learning_items BEGIN
    INSERT INTO learning_fts(learning_fts, rowid, title, author, key_takeaways, tags)
        VALUES ('delete', old.id, old.title, old.author, old.key_takeaways, old.tags);
    INSERT INTO learning_fts(rowid, title, author, key_takeaways, tags)
        VALUES (new.id, new.title, new.author, new.key_takeaways, new.tags);
END;

-- updated_at touch triggers -------------------------------------------------
CREATE TRIGGER companies_touch AFTER UPDATE ON companies BEGIN
    UPDATE companies SET updated_at = datetime('now') WHERE id = new.id AND new.updated_at = old.updated_at;
END;
CREATE TRIGGER contacts_touch AFTER UPDATE ON contacts BEGIN
    UPDATE contacts SET updated_at = datetime('now') WHERE id = new.id AND new.updated_at = old.updated_at;
END;
CREATE TRIGGER stories_touch AFTER UPDATE ON project_stories BEGIN
    UPDATE project_stories SET updated_at = datetime('now') WHERE id = new.id AND new.updated_at = old.updated_at;
END;
CREATE TRIGGER actions_touch AFTER UPDATE ON actions BEGIN
    UPDATE actions SET updated_at = datetime('now') WHERE id = new.id AND new.updated_at = old.updated_at;
END;

-- Field history triggers (md fields only) -----------------------------------
CREATE TRIGGER companies_history AFTER UPDATE OF notes ON companies
WHEN old.notes IS NOT new.notes
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('companies', old.id, 'notes', old.notes, new.notes);
END;

CREATE TRIGGER contacts_history AFTER UPDATE OF notes ON contacts
WHEN old.notes IS NOT new.notes
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('contacts', old.id, 'notes', old.notes, new.notes);
END;

CREATE TRIGGER stories_history_situation AFTER UPDATE OF situation ON project_stories
WHEN old.situation IS NOT new.situation
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('project_stories', old.id, 'situation', old.situation, new.situation);
END;
CREATE TRIGGER stories_history_task AFTER UPDATE OF task ON project_stories
WHEN old.task IS NOT new.task
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('project_stories', old.id, 'task', old.task, new.task);
END;
CREATE TRIGGER stories_history_action AFTER UPDATE OF action ON project_stories
WHEN old.action IS NOT new.action
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('project_stories', old.id, 'action', old.action, new.action);
END;
CREATE TRIGGER stories_history_result AFTER UPDATE OF result ON project_stories
WHEN old.result IS NOT new.result
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('project_stories', old.id, 'result', old.result, new.result);
END;
CREATE TRIGGER stories_history_technical AFTER UPDATE OF technical ON project_stories
WHEN old.technical IS NOT new.technical
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('project_stories', old.id, 'technical', old.technical, new.technical);
END;

CREATE TRIGGER actions_history_desc AFTER UPDATE OF description ON actions
WHEN old.description IS NOT new.description
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('actions', old.id, 'description', old.description, new.description);
END;
CREATE TRIGGER actions_history_notes AFTER UPDATE OF completion_notes ON actions
WHEN old.completion_notes IS NOT new.completion_notes
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('actions', old.id, 'completion_notes', old.completion_notes, new.completion_notes);
END;

CREATE TRIGGER learning_history AFTER UPDATE OF key_takeaways ON learning_items
WHEN old.key_takeaways IS NOT new.key_takeaways
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('learning_items', old.id, 'key_takeaways', old.key_takeaways, new.key_takeaways);
END;

CREATE TRIGGER reviews_history_wins AFTER UPDATE OF wins ON monthly_reviews
WHEN old.wins IS NOT new.wins
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('monthly_reviews', old.id, 'wins', old.wins, new.wins);
END;
CREATE TRIGGER reviews_history_misses AFTER UPDATE OF misses ON monthly_reviews
WHEN old.misses IS NOT new.misses
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('monthly_reviews', old.id, 'misses', old.misses, new.misses);
END;
CREATE TRIGGER reviews_history_lessons AFTER UPDATE OF lessons ON monthly_reviews
WHEN old.lessons IS NOT new.lessons
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('monthly_reviews', old.id, 'lessons', old.lessons, new.lessons);
END;
CREATE TRIGGER reviews_history_focus AFTER UPDATE OF next_month_focus ON monthly_reviews
WHEN old.next_month_focus IS NOT new.next_month_focus
BEGIN
    INSERT INTO field_history(table_name, record_id, field_name, old_value, new_value)
        VALUES ('monthly_reviews', old.id, 'next_month_focus', old.next_month_focus, new.next_month_focus);
END;
