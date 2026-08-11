import datetime

from core.schemas import ComplianceReport, CustomerProfile


def maybe_create_followup_task(
    conn,
    analysis_id: int,
    customer_id: int,
    user_id: int,
    profile: CustomerProfile | None,
    compliance: ComplianceReport | None,
) -> int | None:
    """WARNING 或成交意向 High 时自动创建跟进任务,返回 task_id 或 None。"""
    if profile is None or compliance is None:
        return None
    high_intent = profile.deal_intent == "High"
    warning = compliance.verdict == "WARNING"
    if not (high_intent or warning):
        return None
    due = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    title = "跟进客户并处理合规风险" if warning else "跟进高意向客户"
    cur = conn.execute(
        "INSERT INTO tasks (assigned_to, customer_id, title, due_date, status) VALUES (?,?,?,?,'pending')",
        (user_id, customer_id, title, due),
    )
    conn.commit()
    return cur.lastrowid
