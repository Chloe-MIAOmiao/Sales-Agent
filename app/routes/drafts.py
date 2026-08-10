from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import require_role
from app.db import get_conn
from app.templating import templates

router = APIRouter()
def _drafts_for_user(request: Request):
    user = request.state.session
    conn = get_conn()
    try:
        if user.get("role") == "manager":
            rows = conn.execute(
                """
                SELECT d.*, u.username AS owner, a.id AS analysis_id
                FROM email_drafts d
                JOIN users u ON d.created_by = u.id
                LEFT JOIN analyses a ON d.analysis_id = a.id
                ORDER BY d.id DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT d.*, u.username AS owner, a.id AS analysis_id
                FROM email_drafts d
                JOIN users u ON d.created_by = u.id
                LEFT JOIN analyses a ON d.analysis_id = a.id
                WHERE d.created_by = ?
                ORDER BY d.id DESC
                """,
                (user.get("uid"),),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/drafts", response_class=HTMLResponse)
@require_role("rep", "manager")
def drafts_page(request: Request):
    return templates.TemplateResponse(
        request,
        "drafts.html",
        {"drafts": _drafts_for_user(request)},
    )


@router.post("/drafts/{draft_id}/review")
@require_role("rep", "manager")
def review_draft(request: Request, draft_id: int, status: str = "approved"):
    if status not in ("approved", "rejected"):
        status = "approved"
    user = request.state.session
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM email_drafts WHERE id = ?", (draft_id,)
        ).fetchone()
        if not row:
            return RedirectResponse("/drafts", status_code=303)
        if user.get("role") != "manager" and row["created_by"] != user.get("uid"):
            return RedirectResponse("/drafts", status_code=303)
        conn.execute(
            "UPDATE email_drafts SET status = ? WHERE id = ?", (status, draft_id)
        )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/drafts", status_code=303)

