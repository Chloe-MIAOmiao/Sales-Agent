from app.auth import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    h = hash_password("s3cret")
    assert h != "s3cret"
    assert verify_password("s3cret", h)
    assert not verify_password("wrong", h)


def test_hash_uses_pbkdf2_sha256_high_iterations():
    h = hash_password("s3cret")
    assert h.startswith("pbkdf2:sha256:600000$")


def test_login_page_with_invalid_session_cookie():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.get("/login", cookies={"session": "garbage-token"})
    assert resp.status_code == 200
