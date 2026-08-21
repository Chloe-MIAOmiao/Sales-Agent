import pytest

from tests.conftest import insert_valid_analysis, make_web_client


@pytest.fixture
def rep_client(tmp_path, monkeypatch):
    return make_web_client(tmp_path, monkeypatch, "rep", "rep", 1)


@pytest.fixture
def seeded_draft(rep_client):
    from app import db

    conn = db.get_conn()
    analysis_id, draft_id = insert_valid_analysis(conn, created_by=1)
    conn.commit()
    conn.close()
    return draft_id


def test_draft_detail_shows_body(rep_client, seeded_draft):
    resp = rep_client.get(f"/drafts/{seeded_draft}")

    assert resp.status_code == 200
    assert "跟进邮件" in resp.text
    assert "您好,感谢咨询……" in resp.text


def test_draft_detail_denied_for_other_rep(tmp_path, monkeypatch, seeded_draft):
    client = make_web_client(tmp_path, monkeypatch, "rep2", "rep", 2)

    resp = client.get(f"/drafts/{seeded_draft}", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/drafts"


def test_manager_can_view_any_draft_detail(tmp_path, monkeypatch, seeded_draft):
    client = make_web_client(tmp_path, monkeypatch, "mgr", "manager", 3)

    resp = client.get(f"/drafts/{seeded_draft}")

    assert resp.status_code == 200
    assert "您好,感谢咨询……" in resp.text


def test_missing_draft_redirects_to_list(rep_client):
    resp = rep_client.get("/drafts/9999", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/drafts"


def test_drafts_list_links_to_detail(rep_client, seeded_draft):
    resp = rep_client.get("/drafts")

    assert resp.status_code == 200
    assert f'href="/drafts/{seeded_draft}"' in resp.text
