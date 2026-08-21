import json

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.auth import require_role
from app.db import get_conn
from app.templating import templates
from core.llm_client import LLMClient
from core.mock_data import SAMPLE_CASES, get_sample_case
from core.pipeline import run_pipeline
from core.schemas import (
    ComplianceReport,
    CustomerProfile,
    EmailDraft,
    EmailSpamRisk,
    PipelineResult,
    SpamCheck,
)
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
        lang = getattr(request.state, "lang", "zh-CN")
        result = run_pipeline(llm, chat_text, lang=lang)
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
    analysis_id = None
    try:
        if result.status == "invalid_lead":
            spam = result.spam_check
            cur = conn.execute(
                "INSERT INTO customers (name, source_chat, lead_status, stage, owner_id, last_contact_at) VALUES (?, ?, ?, 'leads', ?, datetime('now','localtime'))",
                (customer_name or None, chat_text, "invalid", user.get("uid")),
            )
            customer_id = cur.lastrowid
            cur = conn.execute(
                "INSERT INTO analyses (customer_id, created_by, spam_json, verdict) VALUES (?, ?, ?, ?)",
                (
                    customer_id,
                    user.get("uid"),
                    json.dumps(spam.model_dump(), ensure_ascii=False),
                    "invalid_lead",
                ),
            )
            analysis_id = cur.lastrowid
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
                "INSERT INTO analyses (customer_id, created_by, profile_json, compliance_json, spam_json, email_spam_risk_json, verdict) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    customer_id,
                    user.get("uid"),
                    json.dumps(profile.model_dump(), ensure_ascii=False),
                    json.dumps(compliance.model_dump(), ensure_ascii=False),
                    json.dumps(spam.model_dump(), ensure_ascii=False),
                    json.dumps(spam_risk.model_dump(), ensure_ascii=False)
                    if spam_risk
                    else None,
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

    return RedirectResponse(f"/analysis/result/{analysis_id}", status_code=303)


def _load_model(model_cls, raw):
    if not raw:
        return None
    return model_cls.model_validate(json.loads(raw))


@router.get("/analysis/result/{analysis_id}", response_class=HTMLResponse)
@require_role("rep", "manager")
def analysis_result(request: Request, analysis_id: int):
    user = request.state.session
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT a.*, c.name AS customer_name
            FROM analyses a
            LEFT JOIN customers c ON a.customer_id = c.id
            WHERE a.id = ?
            """,
            (analysis_id,),
        ).fetchone()
        if not row or (
            user.get("role") != "manager" and row["created_by"] != user.get("uid")
        ):
            return RedirectResponse("/analysis", status_code=303)

        status = "invalid_lead" if row["verdict"] == "invalid_lead" else "completed"
        result = PipelineResult(
            status=status,
            customer_profile=_load_model(CustomerProfile, row["profile_json"]),
            spam_check=_load_model(SpamCheck, row["spam_json"]),
            compliance_report=_load_model(ComplianceReport, row["compliance_json"]),
            email_spam_risk=_load_model(EmailSpamRisk, row["email_spam_risk_json"]),
        )
        if status == "completed":
            draft_row = conn.execute(
                "SELECT * FROM email_drafts WHERE analysis_id = ? ORDER BY id LIMIT 1",
                (analysis_id,),
            ).fetchone()
            if draft_row:
                result.email_draft = EmailDraft(
                    language=draft_row["language"],
                    subject=draft_row["subject"],
                    body=draft_row["body"],
                )
        customer_name = row["customer_name"]
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
