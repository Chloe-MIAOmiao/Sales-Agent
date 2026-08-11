from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth import require_role
from app.db import get_conn
from app.templating import templates

router = APIRouter()
@router.get("/reports", response_class=HTMLResponse)
@require_role("manager")
def reports_page(request: Request):
    conn = get_conn()
    try:
        total_analyses = conn.execute(
            "SELECT COUNT(*) AS c FROM analyses"
        ).fetchone()["c"]
        invalid_leads = conn.execute(
            "SELECT COUNT(*) AS c FROM analyses WHERE verdict = 'invalid_lead'"
        ).fetchone()["c"]
        warnings = conn.execute(
            "SELECT COUNT(*) AS c FROM analyses WHERE verdict = 'WARNING'"
        ).fetchone()["c"]
        by_user = conn.execute(
            """
            SELECT u.username, COUNT(a.id) AS analyses,
                   SUM(CASE WHEN a.verdict = 'WARNING' THEN 1 ELSE 0 END) AS warnings,
                   SUM(CASE WHEN a.verdict = 'invalid_lead' THEN 1 ELSE 0 END) AS invalid
            FROM users u
            LEFT JOIN analyses a ON a.created_by = u.id
            GROUP BY u.id ORDER BY analyses DESC
            """
        ).fetchall()
        intent_rows = conn.execute(
            """
            SELECT json_extract(profile_json, '$.deal_intent') AS intent, COUNT(*) AS n
            FROM analyses WHERE profile_json IS NOT NULL GROUP BY intent
            """
        ).fetchall()
        trend_rows = conn.execute(
            """
            SELECT substr(created_at, 1, 10) AS day,
                   COUNT(*) AS n,
                   SUM(CASE WHEN verdict='WARNING' THEN 1 ELSE 0 END) AS warns
            FROM analyses GROUP BY day ORDER BY day
            """
        ).fetchall()
    finally:
        conn.close()
    return templates.TemplateResponse(
        request,
        "reports.html",
        {
            "total_analyses": total_analyses,
            "invalid_leads": invalid_leads,
            "warnings": warnings,
            "by_user": [dict(r) for r in by_user],
            "intent_data": [{"intent": r["intent"], "n": r["n"]} for r in intent_rows],
            "trend_data": [{"day": r["day"], "n": r["n"], "warns": r["warns"]} for r in trend_rows],
        },
    )

