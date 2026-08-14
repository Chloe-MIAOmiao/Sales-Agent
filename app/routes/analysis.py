import json

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.auth import require_role
from app.db import get_conn
from app.templating import templates
from core.llm_client import LLMClient
from core.mock_data import SAMPLE_CASES, get_sample_case
from core.pipeline import run_pipeline
from core.tasks import maybe_create_followup_task

router = APIRouter()


@router.get("/analysis", response_class=HTMLResponse)
@require_role("rep", "manager")
def analysis_page(request: Request):
    return templates.TemplateResponse(
        request,
        "analysis.html",
        {"sample_cases": SAMPLE_CASES},
    )


@router.post("/analysis", response_class=HTMLResponse)
@require_role("rep", "manager")
def run_analysis(
    request: Request,
    chat_text: str = Form(...),
    customer_name: str = Form(""),
):
    llm = LLMClient()
    try:
        result = run_pipeline(llm, chat_text)
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "analysis.html",
            {
                "sample_cases": SAMPLE_CASES,
                "error": str(e),
            },
        )

    user = request.state.session
    conn = get_conn()
    try:
        if result.status == "invalid_lead":
            spam = result.spam_check
            cur = conn.execute(
                "INSERT INTO customers (name, source_chat, lead_status, stage, owner_id, last_contact_at) VALUES (?, ?, ?, 'leads', ?, datetime('now','localtime'))",
                (customer_name or None, chat_text, "invalid", user.get("uid")),
            )
            customer_id = cur.lastrowid
            conn.execute(
                "INSERT INTO analyses (customer_id, created_by, spam_json, verdict) VALUES (?, ?, ?, ?)",
                (
                    customer_id,
                    user.get("uid"),
                    json.dumps(spam.model_dump(), ensure_ascii=False),
                    "invalid_lead",
                ),
            )
            conn.commit()
        else:
            profile = result.customer_profile
            compliance = result.compliance_report
            spam = result.spam_check
            draft = result.email_draft
            spam_risk = result.email_spam_risk

            cur = conn.execute(
                "INSERT INTO customers (name, language, source_chat, lead_status, stage, owner_id, last_contact_at) VALUES (?, ?, ?, 'valid', 'leads', ?, datetime('now','localtime'))",
                (
                    customer_name or None,
                    profile.language_preference.value,
                    chat_text,
                    user.get("uid"),
                ),
            )
            customer_id = cur.lastrowid
            cur = conn.execute(
                "INSERT INTO analyses (customer_id, created_by, profile_json, compliance_json, spam_json, verdict) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    customer_id,
                    user.get("uid"),
                    json.dumps(profile.model_dump(), ensure_ascii=False),
                    json.dumps(compliance.model_dump(), ensure_ascii=False),
                    json.dumps(spam.model_dump(), ensure_ascii=False),
                    compliance.verdict,
                ),
            )
            analysis_id = cur.lastrowid
            conn.execute(
                "INSERT INTO email_drafts (analysis_id, subject, body, language, created_by) VALUES (?, ?, ?, ?, ?)",
                (
                    analysis_id,
                    draft.subject,
                    draft.body,
                    draft.language.value,
                    user.get("uid"),
                ),
            )
            maybe_create_followup_task(
                conn, analysis_id=analysis_id, customer_id=customer_id,
                user_id=user.get("uid"),
                profile=profile, compliance=compliance,
            )
            conn.commit()
    finally:
        conn.close()

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "result": result,
            "customer_name": customer_name,
        },
    )


@router.get("/samples/{key}")
def sample(key: str):
    case = get_sample_case(key)
    if not case:
        return JSONResponse({"error": "未找到示例"}, status_code=404)
    return {"text": case["text"], "title": case["title"]}
