import sqlite3

from app.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('rep', 'manager'))
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                language TEXT,
                source_chat TEXT,
                lead_status TEXT DEFAULT 'valid'
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER REFERENCES customers(id),
                created_by INTEGER REFERENCES users(id),
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                profile_json TEXT,
                compliance_json TEXT,
                spam_json TEXT,
                verdict TEXT
            );

            CREATE TABLE IF NOT EXISTS email_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER REFERENCES analyses(id),
                subject TEXT,
                body TEXT,
                language TEXT,
                status TEXT DEFAULT 'draft',
                created_by INTEGER REFERENCES users(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
