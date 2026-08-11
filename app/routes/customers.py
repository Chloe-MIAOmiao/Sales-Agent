from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth import require_role
from app.db import get_conn
from app.templating import templates

router = APIRouter()


def list_customers(q: str = "", stage: str | None = None, owner_id: int | None = None, is_manager: bool = False) -> list[dict]:
    conn = get_conn()
    try:
        sql = (
            "SELECT c.*, u.username AS owner FROM customers c "
            "LEFT JOIN users u ON c.owner_id=u.id WHERE 1=1"
        )
        params: list = []
        if q:
            sql += " AND c.name LIKE ?"
            params.append(f"%{q}%")
        if stage:
            sql += " AND c.stage = ?"
            params.append(stage)
        if not is_manager and owner_id is not None:
            sql += " AND (c.owner_id = ? OR c.owner_id IS NULL)"
            params.append(owner_id)
        sql += " ORDER BY c.id DESC"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@router.get("/customers", response_class=HTMLResponse)
@require_role("rep", "manager")
def customers_page(request: Request, q: str = "", stage: str = ""):
    user = request.state.session
    rows = list_customers(
        q=q, stage=stage or None,
        owner_id=user.get("uid"),
        is_manager=user.get("role") == "manager",
    )
    return templates.TemplateResponse(
        request, "customers.html",
        {"customers": rows, "q": q, "stage": stage},
    )
