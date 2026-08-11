from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import require_role
from app.db import get_conn
from app.templating import templates

router = APIRouter()


def _tasks_for(request: Request):
    user = request.state.session
    conn = get_conn()
    try:
        if user.get("role") == "manager":
            rows = conn.execute(
                "SELECT t.*, u.username AS owner, c.name AS customer FROM tasks t "
                "LEFT JOIN users u ON t.assigned_to=u.id LEFT JOIN customers c ON t.customer_id=c.id "
                "ORDER BY t.status, t.due_date"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT t.*, u.username AS owner, c.name AS customer FROM tasks t "
                "LEFT JOIN users u ON t.assigned_to=u.id LEFT JOIN customers c ON t.customer_id=c.id "
                "WHERE t.assigned_to=? ORDER BY t.status, t.due_date",
                (user.get("uid"),),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/tasks", response_class=HTMLResponse)
@require_role("rep", "manager")
def tasks_page(request: Request):
    return templates.TemplateResponse(request, "tasks.html", {"tasks": _tasks_for(request)})


@router.post("/tasks/{task_id}/toggle")
@require_role("rep", "manager")
def toggle_task(request: Request, task_id: int):
    user = request.state.session
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row and (user.get("role") == "manager" or row["assigned_to"] == user.get("uid")):
            new_status = "done" if row["status"] != "done" else "pending"
            conn.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
            conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/tasks", status_code=303)
