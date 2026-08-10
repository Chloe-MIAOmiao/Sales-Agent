from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import create_session_token, hash_password, verify_password
from app.db import get_conn
from app.templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if not row or not verify_password(password, row["password_hash"]):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "用户名或密码错误"},
            status_code=401,
        )
    token = create_session_token(row["id"], row["username"], row["role"])
    response = RedirectResponse(
        "/reports" if row["role"] == "manager" else "/analysis",
        status_code=303,
    )
    response.set_cookie("session", token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session")
    return response


def ensure_seed_users():
    """初始化默认账号:rep/123456(销售)、manager/123456(主管)。"""
    conn = get_conn()
    try:
        for name, role in (("rep", "rep"), ("manager", "manager")):
            exists = conn.execute(
                "SELECT 1 FROM users WHERE username = ?", (name,)
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (name, hash_password("123456"), role),
                )
        conn.commit()
    finally:
        conn.close()
