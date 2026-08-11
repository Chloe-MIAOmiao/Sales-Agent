from app.routes.customers import list_customers


def test_list_customers_filters_by_owner(tmp_path):
    from app import db
    orig = db.DB_PATH
    db.DB_PATH = tmp_path / "c.db"
    db.init_db()
    conn = db.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('rep','x','rep')")
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('mgr','x','manager')")
    conn.execute("INSERT INTO customers (name, stage, owner_id) VALUES ('A','leads',1)")
    conn.execute("INSERT INTO customers (name, stage, owner_id) VALUES ('B','active',2)")
    conn.commit()
    conn.close()
    try:
        rows = list_customers("A", None, owner_id=1, is_manager=False)
        assert [r["name"] for r in rows] == ["A"]
        rows_all = list_customers("", "active", owner_id=None, is_manager=True)
        assert [r["name"] for r in rows_all] == ["B"]
    finally:
        db.DB_PATH = orig
