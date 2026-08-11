from app import db


def test_migration_creates_tasks_and_customer_columns(tmp_path):
    orig = db.DB_PATH
    db.DB_PATH = tmp_path / "test.db"
    try:
        db.init_db()
        conn = db.get_conn()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "tasks" in tables
        cols = [r[1] for r in conn.execute("PRAGMA table_info(customers)")]
        assert "stage" in cols and "owner_id" in cols and "last_contact_at" in cols
        conn.close()
    finally:
        db.DB_PATH = orig
