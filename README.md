# Sales Agent — EduTech Course Sales Compliance & Multilingual Follow-up Agent System

A locally running Web application for sales teams. Sales representatives upload/paste chat logs, and the system automatically performs customer profiling, training-industry compliance risk auditing, and compliant email draft generation (language-adaptive + spam filtering). Supervisors can view history and reports.

Design doc: `docs/superpowers/specs/2026-08-10-sales-agent-design.md`

## Features

- **Customer Profiling**: career background, core pain points, budget sensitivity (around ¥2,999), purchase intent, and language/cultural preferences
- **Compliance Risk Audit**: checks against training-industry red lines (guaranteed employment / guaranteed minimum salary / guaranteed learning / refusal of refunds / fake scarcity)
- **Compliant Email Generation**: generates Chinese, English, or bilingual emails based on the customer's language preference, and auto-corrects non-compliant promises in the chat
- **Spam Filtering**: invalid lead identification + anti-spam risk check on generated emails
- **History & Reports**: supervisors can view each seller's analysis count and violation rate
- **One-click Demo**: 3 built-in sample conversations on the analysis page

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure keys: copy .env.example to .env and fill in DEEPSEEK_API_KEY
# 3. Start
python run.py
```

Visit `http://127.0.0.1:8000`.

Default accounts (auto-created on first startup):

| Role       | Username | Password |
|-----------|----------|----------|
| Sales rep  | rep      | 123456   |
| Supervisor | manager  | 123456   |

> Only generates email drafts; it does not actually send emails.

## Run Tests

```bash
pytest
```

## Directory Structure

- `core/` — Agent core logic (Web-independent, testable in isolation)
  - `llm_client.py` — DeepSeek wrapper (reads key from environment variables, structured-output validation with retries)
  - `schemas.py` — Pydantic data structures
  - `pipeline.py` — pipeline orchestration
  - `analyzers/` — `profiler.py`, `compliance.py`, `spam.py`, `email_writer.py`
  - `mock_data.py` — 3 demo scenarios
- `app/` — Web layer (FastAPI routes, Jinja2 templates, auth, db)
- `tests/` — unit tests (mocked LLM)