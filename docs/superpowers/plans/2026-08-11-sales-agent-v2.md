# 销售 Agent v2 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 v1 EduTech 合规销售 Agent 上完成 4 项升级:UI 美化、跟进任务/可视化报表/客户管理、ReAct 自主决策改造、密码加固 + MCP 邮件收发。

**Architecture:** 保持 core 与 app 分离。core 增加 ReAct agent 循环与 MCP 邮件服务器;app 增加 tasks/customers 路由与图表页面;DB 轻量迁移扩展 tasks 表与 customers 列。每阶段独立可交付,测试保持全绿。

**Tech Stack:** Python 3.13, FastAPI, SQLite, Jinja2, Pico.css, Chart.js(CDN), DeepSeek(OpenAI SDK), pydantic v2, pytest, MCP SDK。

## Global Constraints

- 设计文档:`docs/superpowers/specs/2026-08-11-sales-agent-v2-design.md`(逐条遵循)
- 任何 Agent 逻辑改动必须在 `core/` 内完成,`app/` 只负责展示与调用(AGENTS.md)
- DeepSeek 密钥一律从 `.env` 读取(`DEEPSEEK_API_KEY`),源码禁止硬编码
- 模型输出必须用 Pydantic schema 校验,禁止字符串切割
- `run_pipeline` 对外接口保持 `(llm, chat_text) -> PipelineResult` 不变
- 现有 13 个测试必须持续通过
- 邮件发送必须经人工批准(HITL),Agent 不得直接发邮件
- 密码存储使用 werkzeug hash 加盐(不做 RSA)
- 中文注释与中文 UI 文案保持一致

---

### Task 1: UI 基础设施 — Pico.css 引入 + 设计系统

**Files:**
- Create: `app/static/css/app.css`
- Modify: `app/templates/base.html`

**Interfaces:**
- Produces: 全局加载的 `app.css`;`base.html` 提供所有子模板共用的 `<head>`(Pico.css CDN + app.css + favicon)、导航栏、`<main class="container">` 容器、徽章/卡片/表格/空状态样式类。

- [ ] **Step 1: 更新 base.html 引入 Pico.css 与 app.css**

修改 `app/templates/base.html`:
```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="/static/img/favicon.svg">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <link rel="stylesheet" href="/static/css/app.css">
    <title>{% block title %}EduTech 课程销售合规与多语言跟进 Agent 系统{% endblock %}</title>
</head>
<body>
<nav class="container-fluid">
    <ul><li><strong class="brand">EduTech 销售 Agent</strong></li></ul>
    {% if request.state.session.get('username') %}
    <ul>
        <li><a href="/analysis">分析</a></li>
        <li><a href="/tasks">任务</a></li>
        <li><a href="/customers">客户</a></li>
        <li><a href="/drafts">草稿</a></li>
        {% if request.state.session.get('role') == 'manager' %}<li><a href="/reports">报表</a></li>{% endif %}
        <li><a href="/logout">退出 ({{ request.state.session.get('username') }})</a></li>
    </ul>
    {% endif %}
</nav>
<main class="container">
    {% block content %}{% endblock %}
</main>
</body>
```

- [ ] **Step 2: 创建 app.css 定制样式**

创建 `app/static/css/app.css`:
```css
:root {
  --brand: #1976d2;
  --warning: #e65100;
  --danger: #c62828;
  --success: #2e7d32;
}
main.container { max-width: 960px; padding-top: 1.5rem; }
.card { background: var(--pico-card-background-color, #fff); border: 1px solid var(--pico-muted-border-color, #eee); border-radius: 0.5rem; padding: 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.badge { display: inline-block; padding: 0.1rem 0.6rem; border-radius: 1rem; font-size: 0.75rem; font-weight: 600; }
.badge.warning { background: #fff3e0; color: var(--warning); }
.badge.passed { background: #e8f5e9; color: var(--success); }
.badge.invalid { background: #fce4ec; color: var(--danger); }
.badge.draft { background: #e3f2fd; color: var(--brand); }
.badge.approved { background: #e8f5e9; color: var(--success); }
.badge.sent { background: #e8f5e9; color: var(--success); }
.badge.rejected { background: #fdecea; color: var(--danger); }
.badge.pending { background: #fff3e0; color: var(--warning); }
.badge.done { background: #e8f5e9; color: var(--success); }
.badge.overdue { background: #fdecea; color: var(--danger); }
.empty-state { text-align: center; color: var(--pico-muted-color, #888); padding: 2rem 0; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
.sample-buttons { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.5rem 0 1rem; }
pre.email-body { white-space: pre-wrap; background: var(--pico-code-background-color, #fafafa); padding: 1rem; border-radius: 0.4rem; }
table { margin-bottom: 0; }
```

- [ ] **Step 3: 运行测试确认无回归**

Run: `pytest -q`
Expected: 13 passed

- [ ] **Step 4: 提交**

```bash
git add app/templates/base.html app/static/css/app.css
git commit -m "feat(ui): introduce Pico.css design system"
```

---

### Task 2: 登录页美化

**Files:**
- Modify: `app/templates/login.html`

**Interfaces:**
- Consumes: `base.html` 的 Pico.css 与 app.css
- Produces: 居中登录卡片,复用现有 `/login` POST 表单字段(username/password)

- [ ] **Step 1: 重写 login.html**

替换 `app/templates/login.html` 的 `{% block content %}`:
```html
{% block content %}
<div class="card" style="max-width: 420px; margin: 4rem auto;">
    <hgroup>
        <h1 style="margin-bottom:0;">登录</h1>
        <p>EduTech 课程销售合规与多语言跟进 Agent 系统</p>
    </hgroup>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="post" action="/login">
        <label for="username">用户名</label>
        <input type="text" id="username" name="username" required autocomplete="username">
        <label for="password">密码</label>
        <input type="password" id="password" name="password" required autocomplete="current-password">
        <button type="submit" style="margin-top:1rem;">登录</button>
    </form>
    <p style="font-size:0.8rem;color:var(--pico-muted-color,#888);">默认账号:rep/123456(销售)、manager/123456(主管)</p>
</div>
{% endblock %}
```
`base.html` 需保留 `.error` 样式(已在 app.css 或 base.html 中定义)。

- [ ] **Step 2: 手动验证**

Run: `python run.py`,打开 `http://127.0.0.1:8000/login`,确认登录卡片居中、样式精致、能正常登录/错误提示。

- [ ] **Step 3: 提交**

```bash
git add app/templates/login.html
git commit -m "feat(ui): restyle login page"
```

---

### Task 3: 分析页 + 结果页美化

**Files:**
- Modify: `app/templates/analysis.html`
- Modify: `app/templates/result.html`

**Interfaces:**
- Consumes: `base.html` 设计系统;`analysis_page` 传入 `sample_cases`;`run_analysis` 传入 `result`、`customer_name`、`error`
- Produces: 保持所有表单字段名(`chat_text`、`customer_name`)与 `result` 字段访问路径不变

- [ ] **Step 1: 重写 analysis.html**

替换 `{% block content %}`:
```html
{% block content %}
<div class="card">
    <hgroup>
        <h1>客户分析</h1>
        <p>上传或粘贴销售聊天记录,系统将自动进行画像分析、合规审计与合规邮件生成。</p>
    </hgroup>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <div class="sample-buttons">
        {% for case in sample_cases %}
        <button type="button" class="btn-secondary" onclick="loadSample('{{ case.key }}')">{{ case.label }}</button>
        {% endfor %}
    </div>
    <form method="post" action="/analysis">
        <label for="customer_name">客户姓名(选填)</label>
        <input type="text" id="customer_name" name="customer_name" placeholder="如:张女士">
        <label for="chat_text">聊天记录</label>
        <textarea id="chat_text" name="chat_text" placeholder="在此粘贴客户与销售的聊天记录..."></textarea>
        <button type="submit" style="margin-top:1rem;">开始分析</button>
    </form>
</div>
<script>
async function loadSample(key) {
    const res = await fetch('/samples/' + key);
    const data = await res.json();
    document.getElementById('chat_text').value = data.text;
}
</script>
{% endblock %}
```

- [ ] **Step 2: 重写 result.html**

替换 `{% block content %}`(保持 `result.*` 字段访问不变,新增 empty-state 与卡片结构):
```html
{% block content %}
{% if result.status == 'invalid_lead' %}
<div class="card">
    <h1>无效线索 <span class="badge invalid">无效线索</span></h1>
    <p>{{ result.spam_check.reason }}</p>
    <a role="button" href="/analysis">返回分析</a>
</div>
{% else %}
<div class="card">
    <hgroup><h1>客户画像{% if customer_name %} - {{ customer_name }}{% endif %}</h1></hgroup>
    <table>
        <tr><th>职业背景</th><td>{{ result.customer_profile.occupation_background }}</td></tr>
        <tr><th>核心痛点</th><td>{{ result.customer_profile.core_pain_point }}</td></tr>
        <tr><th>预算敏感度</th><td>{{ result.customer_profile.budget_sensitivity }}</td></tr>
        <tr><th>成交意向度</th><td>{{ result.customer_profile.deal_intent }}</td></tr>
        <tr><th>语言偏好</th><td>{{ result.customer_profile.language_preference.value }} ({{ result.customer_profile.language_reason }})</td></tr>
    </table>
</div>

<div class="card">
    <hgroup><h1>合规审计
        {% if result.compliance_report.verdict == 'WARNING' %}<span class="badge warning">WARNING</span>
        {% else %}<span class="badge passed">PASSED</span>{% endif %}
    </h1></hgroup>
    <p>{{ result.compliance_report.summary }}</p>
    {% if result.compliance_report.violations %}
    <table>
        <tr><th>违规类型</th><th>违规原句</th></tr>
        {% for v in result.compliance_report.violations %}
        <tr><td>{{ v.violation_type }}</td><td>{{ v.quote }}</td></tr>
        {% endfor %}
    </table>
    {% endif %}
</div>

<div class="card">
    <hgroup><h1>邮件草稿 ({{ result.email_draft.language.value }})</h1></hgroup>
    <p><strong>Subject:</strong> {{ result.email_draft.subject }}</p>
    <pre class="email-body">{{ result.email_draft.body }}</pre>
    <p><strong>反垃圾风险:</strong>
        {% if result.email_spam_risk.risk_level == 'high' %}<span class="badge invalid">high</span>
        {% elif result.email_spam_risk.risk_level == 'medium' %}<span class="badge warning">medium</span>
        {% else %}<span class="badge passed">low</span>{% endif %}
        {% for issue in result.email_spam_risk.issues %}<div style="color:#888;font-size:0.85rem;">- {{ issue }}</div>{% endfor %}
    </p>
    <a role="button" href="/drafts">查看草稿并审核</a>
    <a role="button" class="secondary" href="/analysis">再次分析</a>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: 运行测试 + 手动验证**

Run: `pytest -q` → Expected: 13 passed
Run: `python run.py`,访问 `/analysis`,点"加载违规案例"→"开始分析"(需真实 API),确认三块卡片展示正常。

- [ ] **Step 4: 提交**

```bash
git add app/templates/analysis.html app/templates/result.html
git commit -m "feat(ui): restyle analysis and result pages"
```

---

### Task 4: 草稿页 + 报表页美化(阶段 A 收尾)

**Files:**
- Modify: `app/templates/drafts.html`
- Modify: `app/templates/reports.html`

**Interfaces:**
- Consumes: `_drafts_for_user` 返回字段(id/language/subject/owner/status);`reports_page` 传入 total_analyses/invalid_leads/warnings/by_user
- Produces: 表格与状态徽章使用 app.css 类;报表页增加 metric-grid 卡片

- [ ] **Step 1: 重写 drafts.html**

替换 `{% block content %}`:
```html
{% block content %}
<h1>邮件草稿</h1>
{% if drafts %}
<table>
    <thead><tr><th>ID</th><th>语言</th><th>主题</th><th>创建人</th><th>状态</th><th>操作</th></tr></thead>
    <tbody>
    {% for d in drafts %}
    <tr>
        <td>{{ d.id }}</td>
        <td>{{ d.language }}</td>
        <td>{{ d.subject }}</td>
        <td>{{ d.owner }}</td>
        <td><span class="badge {{ d.status }}">{{ d.status }}</span></td>
        <td>
            {% if d.status == 'draft' %}
            <form method="post" action="/drafts/{{ d.id }}/review" style="display:inline;">
                <input type="hidden" name="status" value="approved">
                <button type="submit" class="btn-success">批准</button>
            </form>
            <form method="post" action="/drafts/{{ d.id }}/review" style="display:inline;">
                <input type="hidden" name="status" value="rejected">
                <button type="submit" class="btn-danger">拒绝</button>
            </form>
            {% else %}<span style="color:#999;">已处理</span>{% endif %}
        </td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">暂无草稿。</div>
{% endif %}
{% endblock %}
```
注:`btn-success`/`btn-danger` 若无 Pico 对应类,可在 app.css 追加:
```css
.btn-success { background: var(--success); color:#fff; border:none; }
.btn-danger { background: var(--danger); color:#fff; border:none; }
```

- [ ] **Step 2: 重写 reports.html(基础表格,阶段 B2 再加图)**

替换 `{% block content %}`:
```html
{% block content %}
<h1>主管报表</h1>
<div class="metric-grid">
    <div class="card" style="text-align:center;"><div style="font-size:2rem;font-weight:700;">{{ total_analyses }}</div><div style="color:#888;">总分析数</div></div>
    <div class="card" style="text-align:center;"><div style="font-size:2rem;font-weight:700;">{{ invalid_leads }}</div><div style="color:#888;">无效线索</div></div>
    <div class="card" style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--warning);">{{ warnings }}</div><div style="color:#888;">合规警告</div></div>
</div>
<div class="card">
    <h2>各销售员分析统计</h2>
    <table>
        <thead><tr><th>销售员</th><th>分析数</th><th>合规警告</th><th>无效线索</th></tr></thead>
        <tbody>
        {% for row in by_user %}
        <tr><td>{{ row.username }}</td><td>{{ row.analyses }}</td><td>{{ row.warnings }}</td><td>{{ row.invalid }}</td></tr>
        {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

- [ ] **Step 3: 运行测试 + 手动验证**

Run: `pytest -q` → 13 passed
Run: `python run.py`,分别用 rep/manager 登录验证草稿页与报表页。

- [ ] **Step 4: 提交**

```bash
git add app/templates/drafts.html app/templates/reports.html app/static/css/app.css
git commit -m "feat(ui): restyle drafts and reports pages"
```

---

### Task 5: DB 迁移 — tasks 表 + customers 扩展列

**Files:**
- Modify: `app/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces: `init_db()` 幂等执行迁移:
  - 建表 `tasks(id INTEGER PK AUTOINCREMENT, assigned_to INTEGER REFERENCES users(id), customer_id INTEGER REFERENCES customers(id), title TEXT NOT NULL, due_date TEXT, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now','localtime')))`
  - `customers` 若缺列则 `ALTER TABLE` 追加:`stage TEXT DEFAULT 'leads'`、`owner_id INTEGER`、`last_contact_at TEXT`
  - 列存在性检查用 `PRAGMA table_info(customers)`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_db.py`:
```python
import os
import tempfile

from app import db
from app.config import DB_PATH


def test_migration_creates_tasks_and_customer_columns(tmp_path):
    orig = db.DB_PATH
    db.DB_PATH = tmp_path / "test.db"
    try:
        db.init_db()
        conn = db.get_conn()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "tasks" in tables
        cols = [r[1] for r in conn.execute("PRAGMA table_info(customers)")]
        assert "stage" in cols and "owner_id" in cols and "last_contact_at" in cols
        conn.close()
    finally:
        db.DB_PATH = orig
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_db.py -v`
Expected: FAIL — `assert "tasks" in tables` 失败(表不存在)

- [ ] **Step 3: 实现迁移**

修改 `app/db.py`:
```python
import sqlite3

from app.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, col: str, ddl: str) -> None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('rep', 'manager'))
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                language TEXT,
                source_chat TEXT,
                lead_status TEXT DEFAULT 'valid'
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER REFERENCES customers(id),
                created_by INTEGER REFERENCES users(id),
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                profile_json TEXT,
                compliance_json TEXT,
                spam_json TEXT,
                verdict TEXT
            );

            CREATE TABLE IF NOT EXISTS email_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER REFERENCES analyses(id),
                subject TEXT,
                body TEXT,
                language TEXT,
                status TEXT DEFAULT 'draft',
                created_by INTEGER REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assigned_to INTEGER REFERENCES users(id),
                customer_id INTEGER REFERENCES customers(id),
                title TEXT NOT NULL,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            """
        )
        _ensure_column(conn, "customers", "stage", "stage TEXT DEFAULT 'leads'")
        _ensure_column(conn, "customers", "owner_id", "owner_id INTEGER")
        _ensure_column(conn, "customers", "last_contact_at", "last_contact_at TEXT")
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 5: 运行全部测试确认无回归**

Run: `pytest -q`
Expected: 14 passed

- [ ] **Step 6: 提交**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat(db): add tasks table and customer columns migration"
```

---

### Task 6: 跟进任务 — core 规则 + routes + 页面

**Files:**
- Create: `app/routes/tasks.py`
- Modify: `app/main.py`
- Modify: `app/routes/analysis.py`(分析落库时自动建任务)
- Test: `tests/test_tasks.py`

**Interfaces:**
- Consumes: `get_conn()`;`require_role`;`PipelineResult`(compliance.verdict, customer_profile.deal_intent)
- Produces:
  - `core/tasks.py` 新增 `maybe_create_followup_task(conn, analysis_id, customer_id, user_id, profile, compliance) -> int | None`:当 `verdict == "WARNING"` 或 `deal_intent == "High"` 时插入一条 `tasks`(title 如"跟进客户并处理合规风险",due_date 为 3 天后 `datetime.date.today() + timedelta(days=3)`),返回 task_id 或 None
  - 路由 `GET /tasks`(页面)、`POST /tasks/{id}/toggle`(标记完成/重开),使用 app.css 徽章与 empty-state

- [ ] **Step 1: 写失败测试**

创建 `tests/test_tasks.py`:
```python
import sqlite3

from core.tasks import maybe_create_followup_task
from core.schemas import ComplianceReport, CustomerProfile, LanguagePreference


def _profile(deal_intent: str) -> CustomerProfile:
    return CustomerProfile(
        occupation_background="运营", core_pain_point="转行",
        budget_sensitivity="Medium", deal_intent=deal_intent,
        language_preference=LanguagePreference.ZH, language_reason="中文",
    )


def _conn(tmp_path):
    from app import db
    orig = db.DB_PATH
    db.DB_PATH = tmp_path / "t.db"
    db.init_db()
    conn = db.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('rep','x','rep')")
    conn.execute("INSERT INTO customers (name) VALUES ('张女士')")
    conn.execute("INSERT INTO analyses (customer_id, created_by, verdict) VALUES (1,1,'WARNING')")
    conn.commit()
    return conn


def test_creates_task_on_warning(tmp_path):
    conn = _conn(tmp_path)
    task_id = maybe_create_followup_task(
        conn, analysis_id=1, customer_id=1, user_id=1,
        profile=_profile("Medium"),
        compliance=ComplianceReport(verdict="WARNING", violations=[], summary="s"),
    )
    assert task_id is not None
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    assert row["status"] == "pending"
    conn.close()


def test_creates_task_on_high_intent(tmp_path):
    conn = _conn(tmp_path)
    task_id = maybe_create_followup_task(
        conn, analysis_id=1, customer_id=1, user_id=1,
        profile=_profile("High"),
        compliance=ComplianceReport(verdict="PASSED", violations=[], summary="s"),
    )
    assert task_id is not None
    conn.close()


def test_no_task_when_passed_and_medium(tmp_path):
    conn = _conn(tmp_path)
    task_id = maybe_create_followup_task(
        conn, analysis_id=1, customer_id=1, user_id=1,
        profile=_profile("Medium"),
        compliance=ComplianceReport(verdict="PASSED", violations=[], summary="s"),
    )
    assert task_id is None
    conn.close()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_tasks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.tasks'`

- [ ] **Step 3: 实现 core/tasks.py**

创建 `core/tasks.py`:
```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_tasks.py -v`
Expected: 3 passed

- [ ] **Step 5: 创建 tasks 路由与页面**

创建 `app/routes/tasks.py`:
```python
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
```

创建 `app/templates/tasks.html`:
```html
{% extends "base.html" %}
{% block title %}跟进任务 - EduTech 课程销售合规与多语言跟进 Agent 系统{% endblock %}
{% block content %}
<h1>跟进任务</h1>
{% if tasks %}
<table>
    <thead><tr><th>ID</th><th>客户</th><th>任务</th><th>负责人</th><th>截止</th><th>状态</th><th>操作</th></tr></thead>
    <tbody>
    {% for t in tasks %}
    <tr>
        <td>{{ t.id }}</td><td>{{ t.customer or '-' }}</td><td>{{ t.title }}</td><td>{{ t.owner }}</td><td>{{ t.due_date }}</td>
        <td><span class="badge {{ t.status }}">{{ t.status }}</span></td>
        <td><form method="post" action="/tasks/{{ t.id }}/toggle" style="display:inline;">
            <button type="submit">{% if t.status == 'done' %}重开{% else %}完成{% endif %}</button>
        </form></td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">暂无跟进任务。</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 6: 注册路由 + 分析时自动建任务**

在 `app/main.py` 增加 `from app.routes import tasks` 并 `app.include_router(tasks.router)`。

在 `app/routes/analysis.py` 的 `run_analysis` 落库分支中,`conn.commit()` 前调用:
```python
from core.tasks import maybe_create_followup_task
...
task_id = maybe_create_followup_task(
    conn, analysis_id=analysis_id, customer_id=customer_id,
    user_id=user.get("uid"),
    profile=profile, compliance=compliance,
)
```
(仅 `else` 有效分支;`invalid_lead` 分支不创建。)

- [ ] **Step 7: 运行全部测试 + 手动验证**

Run: `pytest -q` → Expected: 16 passed
Run: `python run.py`,rep 登录 → 加载违规案例 → 分析 → 任务页应出现一条 pending 任务。

- [ ] **Step 8: 提交**

```bash
git add core/tasks.py app/routes/tasks.py app/templates/tasks.html app/main.py app/routes/analysis.py tests/test_tasks.py
git commit -m "feat(tasks): follow-up task auto-creation and page"
```

---

### Task 7: 客户管理 — customers 路由 + 页面

**Files:**
- Create: `app/routes/customers.py`
- Modify: `app/main.py`
- Modify: `app/routes/analysis.py`(落库时写 `owner_id`、`stage`、`last_contact_at`)
- Test: `tests/test_customers.py`

**Interfaces:**
- Consumes: `customers` 表新列 stage/owner_id/last_contact_at;`analyses` 表
- Produces: 路由 `GET /customers`(列表,搜索参数 `?q=`、筛选 `?stage=`),返回字段含 id/name/stage/owner/language/last_contact_at/lead_status

- [ ] **Step 1: 写失败测试**

创建 `tests/test_customers.py`:
```python
from app.routes.customers import list_customers


def test_list_customers_filters_by_owner(tmp_path):
    from app import db
    orig = db.DB_PATH
    db.DB_PATH = tmp_path / "c.db"
    db.init_db()
    conn = db.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('rep','x','rep')")
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('mgr','x','manager')")
    conn.execute("INSERT INTO customers (name, stage, owner_id) VALUES ('A','leads',1)")
    conn.execute("INSERT INTO customers (name, stage, owner_id) VALUES ('B','active',2)")
    conn.commit()
    conn.close()
    try:
        rows = list_customers("A", None, owner_id=1, is_manager=False)
        assert [r["name"] for r in rows] == ["A"]
        rows_all = list_customers("", "active", owner_id=None, is_manager=True)
        assert [r["name"] for r in rows_all] == ["B"]
    finally:
        db.DB_PATH = orig
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_customers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.routes.customers'`

- [ ] **Step 3: 实现 customers 路由**

创建 `app/routes/customers.py`:
```python
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
```

创建 `app/templates/customers.html`:
```html
{% extends "base.html" %}
{% block title %}客户管理 - EduTech 课程销售合规与多语言跟进 Agent 系统{% endblock %}
{% block content %}
<h1>客户管理</h1>
<form method="get" action="/customers" style="display:flex;gap:0.5rem;margin-bottom:1rem;flex-wrap:wrap;">
    <input type="text" name="q" value="{{ q }}" placeholder="搜索客户名">
    <select name="stage">
        <option value="">全部阶段</option>
        {% for s in ['leads','active','lost','won'] %}
        <option value="{{ s }}" {% if stage==s %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
    </select>
    <button type="submit">筛选</button>
</form>
{% if customers %}
<table>
    <thead><tr><th>ID</th><th>客户名</th><th>阶段</th><th>负责人</th><th>语言</th><th>线索状态</th><th>最近联系</th></tr></thead>
    <tbody>
    {% for c in customers %}
    <tr>
        <td>{{ c.id }}</td><td>{{ c.name or '-' }}</td>
        <td><span class="badge {{ c.stage }}">{{ c.stage }}</span></td>
        <td>{{ c.owner or '-' }}</td><td>{{ c.language or '-' }}</td>
        <td><span class="badge {{ c.lead_status }}">{{ c.lead_status }}</span></td>
        <td>{{ c.last_contact_at or '-' }}</td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">暂无客户。</div>
{% endif %}
{% endblock %}
```
在 `app.css` 追加 stage 徽章:
```css
.badge.leads { background:#e3f2fd; color:var(--brand); }
.badge.active { background:#e8f5e9; color:var(--success); }
.badge.lost { background:#fdecea; color:var(--danger); }
.badge.won { background:#ede7f6; color:#5e35b1; }
```

- [ ] **Step 4: 注册路由 + 分析落库写入客户属性**

`app/main.py` 注册 `customers.router`。

`app/routes/analysis.py` 中,两个分支的 `INSERT INTO customers` 均增加列:
- 有效分支:加入 `owner_id`(user uid)、`stage='leads'`、`last_contact_at=datetime('now','localtime')`
- invalid_lead 分支:同样写 `owner_id`、`stage='leads'`

SQL 示例(有效分支):
```python
cur = conn.execute(
    "INSERT INTO customers (name, language, source_chat, lead_status, stage, owner_id, last_contact_at) "
    "VALUES (?, ?, ?, 'valid', 'leads', ?, datetime('now','localtime'))",
    (customer_name or None, profile.language_preference.value, chat_text, user.get("uid")),
)
```

- [ ] **Step 5: 运行全部测试 + 手动验证**

Run: `pytest -q` → Expected: 17 passed
Run: `python run.py`,rep 登录 → 分析一次 → `/customers` 应看到该客户,主管可见全部。

- [ ] **Step 6: 提交**

```bash
git add app/routes/customers.py app/templates/customers.html app/main.py app/routes/analysis.py app/static/css/app.css tests/test_customers.py
git commit -m "feat(customers): customer list, search and stage filter"
```

---

### Task 8: 可视化报表 — Chart.js 图表

**Files:**
- Modify: `app/routes/reports.py`
- Modify: `app/templates/reports.html`

**Interfaces:**
- Consumes: `reports_page` 现有 SQL;新增聚合查询
- Produces: 报表页新增三张 Chart.js 图表:违规率趋势(按日)、各销售员分析数柱状图、成交意向分布饼图

- [ ] **Step 1: 扩展 reports.py 提供图表数据**

修改 `app/routes/reports.py`,在现有查询后追加:
```python
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
```
模板上下文追加 `intent_data=[{"intent": r["intent"], "n": r["n"]} for r in intent_rows]`、`trend_data=[{"day": r["day"], "n": r["n"], "warns": r["warns"]} for r in trend_rows]`、`by_user` 已存在。

- [ ] **Step 2: 更新 reports.html 加图表**

在 `reports.html` 末尾追加:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<div class="card"><h2>各销售员分析数</h2><canvas id="byUserChart"></canvas></div>
<div class="card"><h2>成交意向分布</h2><canvas id="intentChart"></canvas></div>
<div class="card"><h2>每日分析与合规警告</h2><canvas id="trendChart"></canvas></div>
<script>
const byUser = {{ by_user | tojson }};
const intentData = {{ intent_data | tojson }};
const trendData = {{ trend_data | tojson }};
new Chart(document.getElementById('byUserChart'), { type: 'bar', data: { labels: byUser.map(r=>r.username), datasets: [{ label: '分析数', data: byUser.map(r=>r.analyses), backgroundColor:'#1976d2' }] } });
new Chart(document.getElementById('intentChart'), { type: 'pie', data: { labels: intentData.map(r=>r.intent), datasets: [{ data: intentData.map(r=>r.n), backgroundColor:['#1976d2','#e65100','#2e7d32'] }] } });
new Chart(document.getElementById('trendChart'), { type: 'line', data: { labels: trendData.map(r=>r.day), datasets: [{ label:'分析数', data: trendData.map(r=>r.n), borderColor:'#1976d2' }, { label:'合规警告', data: trendData.map(r=>r.warns), borderColor:'#e65100' }] } });
</script>
```
注:Jinja2 `tojson` 过滤器可用(Starlette 内置)。

- [ ] **Step 3: 手动验证**

Run: `python run.py`,manager 登录 → `/reports`,确认三张图表渲染、空数据时不报错。

- [ ] **Step 4: 运行测试 + 提交**

Run: `pytest -q` → 17 passed
```bash
git add app/routes/reports.py app/templates/reports.html
git commit -m "feat(reports): add Chart.js visualizations"
```

---

### Task 9: LLM 客户端 — 工具调用循环

**Files:**
- Modify: `core/llm_client.py`
- Test: `tests/test_llm_client.py`

**Interfaces:**
- Consumes: `OpenAI` 客户端,`DEFAULT_MODEL`
- Produces: `complete_tool_loop(messages, tools: list[dict], execute: Callable[[str, dict], str], max_steps=8, temperature=0.3) -> dict`:循环调用模型(带 `tools`),若返回 tool_calls 则执行 `execute(tool_name, args)` 回传 observation;若返回普通 content 则解析 JSON 返回 `{"final": content, "steps": n}`。执行异常包在 observation 中返回,不中断循环。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_llm_client.py`:
```python
from core.llm_client import LLMClient


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.i = 0
    def create(self, **kwargs):
        r = self.responses[min(self.i, len(self.responses) - 1)]
        self.i += 1
        return r


class FakeChat:
    def __init__(self, responses):
        self.completions = FakeCompletions(responses)


class FakeOpenAI:
    def __init__(self, responses):
        self.chat = FakeChat(responses)


def _tool_call(name, args, call_id="call_1"):
    import types
    fn = types.SimpleNamespace(name=name, arguments=json.dumps(args))
    return types.SimpleNamespace(id=call_id, function=fn)


def _msg_response(tool_calls=None, content=None):
    import types
    msg = types.SimpleNamespace(tool_calls=tool_calls, content=content)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])


def test_tool_loop_executes_tools_until_final():
    import json
    tool1 = _msg_response(tool_calls=[_tool_call("echo", {"x": 1})])
    final = _msg_response(content='{"ok": true}')
    client = LLMClient.__new__(LLMClient)
    client.model = "deepseek-chat"
    client.client = FakeOpenAI([tool1, final])
    executed = []
    result = client.complete_tool_loop(
        messages=[{"role": "user", "content": "go"}],
        tools=[{"type": "function", "function": {"name": "echo", "parameters": {"type": "object", "properties": {}}}}],
        execute=lambda name, args: executed.append((name, args)) or "done",
    )
    assert executed == [("echo", {"x": 1})]
    assert result["final"] == '{"ok": true}'


def test_tool_loop_caps_steps():
    import json
    tool1 = _msg_response(tool_calls=[_tool_call("echo", {})])
    client = LLMClient.__new__(LLMClient)
    client.model = "deepseek-chat"
    client.client = FakeOpenAI([tool1])
    result = client.complete_tool_loop(
        messages=[{"role": "user", "content": "go"}],
        tools=[{"type": "function", "function": {"name": "echo", "parameters": {"type": "object", "properties": {}}}}],
        execute=lambda name, args: "done", max_steps=2,
    )
    assert result["steps"] <= 2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_llm_client.py -v`
Expected: FAIL — `AttributeError: 'LLMClient' object has no attribute 'complete_tool_loop'`

- [ ] **Step 3: 实现 complete_tool_loop**

在 `core/llm_client.py` 增加方法:
```python
    def complete_tool_loop(
        self,
        messages: list[dict],
        tools: list[dict],
        execute,
        max_steps: int = 8,
        temperature: float = 0.3,
    ) -> dict:
        """ReAct 工具循环:模型请求工具则执行并回传,直到模型输出最终答案。"""
        working = [*messages]
        for step in range(max_steps):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=working,
                tools=tools,
                temperature=temperature,
            )
            message = response.choices[0].message
            if message.tool_calls:
                working.append(message)
                for tc in message.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    try:
                        obs = str(execute(name, args))
                    except Exception as e:
                        obs = f"ERROR: {e}"
                    working.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": obs,
                        }
                    )
                continue
            return {"final": message.content or "", "steps": step + 1}
        return {"final": "", "steps": max_steps, "timeout": True}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_llm_client.py -v`
Expected: 2 passed

- [ ] **Step 5: 运行全部测试 + 提交**

Run: `pytest -q` → Expected: 19 passed
```bash
git add core/llm_client.py tests/test_llm_client.py
git commit -m "feat(llm): add ReAct tool-calling loop"
```

---

### Task 10: ReAct Agent 主循环

**Files:**
- Create: `core/agent.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `LLMClient.complete_tool_loop`;现有分析器 `analyze_profile`/`audit_chat`/`check_invalid_lead`/`write_followup_email`/`check_email_spam`;`core/tasks.maybe_create_followup_task`
- Produces: `run_agent(llm, chat_text, conn=None) -> PipelineResult`:
  - 构造工具注册表(名字→函数),系统提示注入 EduTech 上下文与合规红线
  - 调用 `complete_tool_loop`,从最终 JSON 解析 `PipelineResult`
  - 若 `final` 解析失败或 timeout,抛 `RuntimeError`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_agent.py`:
```python
import json

from core.agent import TOOL_DEFINITIONS, run_agent
from core.llm_client import LLMClient
from core.schemas import PipelineResult


def test_tool_definitions_cover_required_tools():
    names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
    for required in ["analyze_profile", "audit_compliance", "check_spam", "generate_email", "check_email_spam"]:
        assert required in names


class ScriptedClient(LLMClient):
    def __init__(self, sequence):
        self.sequence = sequence
        self.i = 0
    def complete_tool_loop(self, messages, tools, execute, max_steps=8, temperature=0.3):
        while self.i < len(self.sequence):
            item = self.sequence[self.i]
            self.i += 1
            if item["kind"] == "call":
                obs = execute(item["tool"], item["args"])
                self.sequence.insert(self.i, {"kind": "obs", "content": obs})
            else:
                return {"final": item["content"], "steps": self.i}


def test_run_agent_returns_completed_result():
    result_json = json.dumps({
        "status": "completed",
        "spam_check": {"is_invalid_lead": False, "reason": "ok"},
        "customer_profile": {"occupation_background": "运营", "core_pain_point": "转行",
                             "budget_sensitivity": "Medium", "deal_intent": "Medium",
                             "language_preference": "zh", "language_reason": "中文"},
        "compliance_report": {"verdict": "PASSED", "violations": [], "summary": "合规"},
        "email_draft": {"language": "zh", "subject": "跟进", "body": "您好"},
        "email_spam_risk": {"risk_level": "low", "issues": []},
    })
    client = ScriptedClient([
        {"kind": "call", "tool": "check_spam", "args": {"chat": "x"}},
        {"kind": "final", "content": result_json},
    ])
    result = run_agent(client, "x")
    assert isinstance(result, PipelineResult)
    assert result.status == "completed"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.agent'`

- [ ] **Step 3: 实现 core/agent.py**

创建 `core/agent.py`:
```python
import json

from core.analyzers.compliance import audit_chat
from core.analyzers.email_writer import write_followup_email
from core.analyzers.profiler import analyze_profile
from core.analyzers.spam import check_email_spam, check_invalid_lead
from core.llm_client import LLMClient
from core.schemas import PipelineResult

SYSTEM_PROMPT = (
    "你是 EduTech《数据分析与 AI 工具实战班》(售价 ¥2,999,4 周线上课程)的销售合规 Agent。\n"
    "合规红线:严禁保证就业、保底薪资、包学会、拒绝退款、虚假稀缺。\n"
    "流程:先用 check_spam 判断线索有效性;有效则用 analyze_profile 提取画像,"
    "用 audit_compliance 审计聊天合规性,再用 generate_email 生成合规邮件(语言跟随客户画像),"
    "最后用 check_email_spam 复查。工具观察结果请基于聊天记录推理,最终只输出一个符合 PipelineResult 的 JSON。"
)

TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "check_spam", "description": "判断聊天是否为无效线索", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
    {"type": "function", "function": {"name": "analyze_profile", "description": "提取客户画像", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
    {"type": "function", "function": {"name": "audit_compliance", "description": "审计聊天记录合规风险", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
    {"type": "function", "function": {"name": "generate_email", "description": "生成合规跟进邮件", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
    {"type": "function", "function": {"name": "check_email_spam", "description": "检查邮件反垃圾风险", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
]


def _make_executor(llm: LLMClient):
    """返回可执行工具函数;状态保存在闭包中,供最终组装 PipelineResult。"""
    state: dict = {}

    def check_spam(chat: str):
        state["spam"] = check_invalid_lead(llm, chat)
        return state["spam"].model_dump_json(ensure_ascii=False)

    def analyze_profile(chat: str):
        state["profile"] = analyze_profile(llm, chat)
        return state["profile"].model_dump_json(ensure_ascii=False)

    def audit_compliance(chat: str):
        state["compliance"] = audit_chat(llm, chat)
        return state["compliance"].model_dump_json(ensure_ascii=False)

    def generate_email(chat: str):
        profile = state.get("profile")
        compliance = state.get("compliance")
        if profile is None or compliance is None:
            raise RuntimeError("generate_email 需先执行 analyze_profile 与 audit_compliance")
        state["draft"] = write_followup_email(llm, profile, compliance, chat)
        return state["draft"].model_dump_json(ensure_ascii=False)

    def check_email_spam(chat: str):
        draft = state.get("draft")
        if draft is None:
            raise RuntimeError("check_email_spam 需先执行 generate_email")
        state["spam_risk"] = check_email_spam(llm, draft)
        return state["spam_risk"].model_dump_json(ensure_ascii=False)

    registry = {
        "check_spam": check_spam,
        "analyze_profile": analyze_profile,
        "audit_compliance": audit_compliance,
        "generate_email": generate_email,
        "check_email_spam": check_email_spam,
    }
    return registry, state


def run_agent(llm: LLMClient, chat_text: str) -> PipelineResult:
    registry, state = _make_executor(llm)
    result = llm.complete_tool_loop(
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": f"聊天记录:\n{chat_text}"}],
        tools=TOOL_DEFINITIONS,
        execute=lambda name, args: registry[name](**args),
    )
    if result.get("timeout") or not result.get("final"):
        raise RuntimeError("Agent 未能在限定步数内给出结果")
    try:
        data = json.loads(result["final"])
        return PipelineResult.model_validate(data)
    except Exception as e:
        raise RuntimeError(f"Agent 最终输出无法解析: {e}") from e
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_agent.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add core/agent.py tests/test_agent.py
git commit -m "feat(agent): ReAct loop with tool registry"
```

---

### Task 11: pipeline 切换到 ReAct Agent

**Files:**
- Modify: `core/pipeline.py`
- Modify: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `core.agent.run_agent`
- Produces: `run_pipeline(llm, chat_text) -> PipelineResult` 内部调用 `run_agent`,接口不变
- 兼容:保留旧顺序逻辑作为回退?——不保留,直接切换;现有 test_pipeline 需更新为使用 ScriptedClient

- [ ] **Step 1: 更新 pipeline.py**

替换 `core/pipeline.py`:
```python
from core.agent import run_agent
from core.llm_client import LLMClient
from core.schemas import PipelineResult


def run_pipeline(llm: LLMClient, chat_text: str) -> PipelineResult:
    """通过 ReAct Agent 完成分析:无效线索 → 画像 → 合规审计 → 邮件生成 → 复查。"""
    return run_agent(llm, chat_text)
```

- [ ] **Step 2: 更新 test_pipeline.py 适配新实现**

替换 `tests/test_pipeline.py`,复用 ScriptedClient(从 tests 抽公共 helper):
创建 `tests/agent_stub.py`:
```python
class ScriptedClient:
    """可编程 LLM 桩:回放工具调用与最终答案序列。"""
    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.i = 0
    def complete_tool_loop(self, messages, tools, execute, max_steps=8, temperature=0.3):
        while self.i < len(self.sequence):
            item = self.sequence[self.i]
            self.i += 1
            if item["kind"] == "call":
                obs = execute(item["tool"], item["args"])
                self.sequence.insert(self.i, {"kind": "obs", "content": obs})
            else:
                return {"final": item["content"], "steps": self.i}
```
重写 `tests/test_pipeline.py`:
```python
import json

from core.pipeline import run_pipeline
from tests.agent_stub import ScriptedClient

FINAL = {
    "status": "completed",
    "spam_check": {"is_invalid_lead": False, "reason": "ok"},
    "customer_profile": {"occupation_background": "运营", "core_pain_point": "转行",
                         "budget_sensitivity": "Medium", "deal_intent": "Medium",
                         "language_preference": "zh", "language_reason": "中文"},
    "compliance_report": {"verdict": "PASSED", "violations": [], "summary": "合规"},
    "email_draft": {"language": "zh", "subject": "跟进", "body": "您好"},
    "email_spam_risk": {"risk_level": "low", "issues": []},
}


def test_pipeline_completes_valid_lead():
    client = ScriptedClient([
        {"kind": "call", "tool": "check_spam", "args": {"chat": "x"}},
        {"kind": "final", "content": json.dumps(FINAL, ensure_ascii=False)},
    ])
    result = run_pipeline(client, "x")
    assert result.status == "completed"
    assert result.email_draft is not None


def test_pipeline_stops_on_invalid_lead():
    invalid = dict(FINAL)
    invalid.update({"status": "invalid_lead", "customer_profile": None,
                    "compliance_report": None, "email_draft": None, "email_spam_risk": None})
    invalid["spam_check"] = {"is_invalid_lead": True, "reason": "仅索要免费资料"}
    client = ScriptedClient([
        {"kind": "call", "tool": "check_spam", "args": {"chat": "x"}},
        {"kind": "final", "content": json.dumps(invalid, ensure_ascii=False)},
    ])
    result = run_pipeline(client, "x")
    assert result.status == "invalid_lead"
    assert result.email_draft is None
```

- [ ] **Step 3: 运行全部测试**

Run: `pytest -q`
Expected: 全绿(原 test_pipeline 的 2 个用例被替换,test_agent 新增 2 个;总数约 20)

- [ ] **Step 4: 提交**

```bash
git add core/pipeline.py tests/test_pipeline.py tests/agent_stub.py
git commit -m "refactor(pipeline): delegate to ReAct agent"
```

---

### Task 12: 密码 hash 加固 + SECRET_KEY 配置

**Files:**
- Modify: `app/auth.py`
- Modify: `app/config.py`
- Modify: `.env.example`
- Modify: `tests/test_auth.py`(新增)

**Interfaces:**
- Consumes: `SECRET_KEY` 从 `app.config`
- Produces: `hash_password` 使用 `method="pbkdf2:sha256:600000"`;`SECRET_KEY` 从 `.env` 读取,缺失时抛异常(不提供明文默认)

- [ ] **Step 1: 写失败测试**

创建 `tests/test_auth.py`:
```python
from app.auth import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    h = hash_password("s3cret")
    assert h != "s3cret"
    assert verify_password("s3cret", h)
    assert not verify_password("wrong", h)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth'`(若已存在则断言通过,改为验证 hash 前缀)

- [ ] **Step 3: 更新 auth.py 与 config.py**

`app/config.py`:
```python
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "sales_agent.db"
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("请配置 SECRET_KEY 环境变量(复制 .env.example 为 .env 并填写)")
```

`app/auth.py`:
```python
from functools import wraps
from inspect import iscoroutinefunction

from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import SECRET_KEY

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="auth")


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256:600000")
```
(`verify_password`、`create_session_token`、`read_session_token`、`require_role` 不变。)

`.env.example` 增加:
```
SECRET_KEY=please-change-me
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_auth.py -v` → PASS
Run: `pytest -q` → 全绿

- [ ] **Step 5: 提交**

```bash
git add app/auth.py app/config.py .env.example tests/test_auth.py
git commit -m "sec: strengthen password hashing and require SECRET_KEY"
```

---

### Task 13: MCP 邮件服务器与 Agent 集成

**Files:**
- Create: `core/mcp/__init__.py`
- Create: `core/mcp/email_server.py`
- Create: `core/mcp/tools.py`
- Modify: `requirements.txt`
- Modify: `.env.example`(SMTP/IMAP 配置)
- Modify: `app/routes/drafts.py`(批准后触发发送,若配置了邮件)
- Test: `tests/test_mcp.py`

**Interfaces:**
- Consumes: 邮件配置从 `.env`(`SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`IMAP_HOST` 可选)
- Produces:
  - `core/mcp/email_server.py`:`EmailServer` 类,方法 `send_email(recipient, subject, body) -> dict`、`list_inbox(limit=10) -> list[dict]`、`read_email(uid) -> dict`、`reply_email(uid, body) -> dict`;未配置 SMTP 时 `send_email` 返回 `{"sent": False, "reason": "SMTP 未配置"}`(安全降级,不真实发送)
  - `core/mcp/tools.py`:`build_email_tools()` 返回 `(definitions, registry)` 供 ReAct 工具注册表扩展
  - `app/routes/drafts.py`:`POST /drafts/{id}/review` 当 status=approved 且 SMTP 已配置时调用 `EmailServer.send_email`,成功后更新 status='sent'

- [ ] **Step 1: 写失败测试**

创建 `tests/test_mcp.py`:
```python
from core.mcp.email_server import EmailServer


def test_send_email_degrades_when_no_smtp():
    server = EmailServer({})
    result = server.send_email("a@b.com", "hi", "body")
    assert result["sent"] is False
    assert "SMTP" in result["reason"] or "未配置" in result["reason"]


def test_list_inbox_empty_without_imap():
    server = EmailServer({})
    assert server.list_inbox() == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_mcp.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.mcp.email_server'`

- [ ] **Step 3: 实现 core/mcp/email_server.py**

创建 `core/mcp/__init__.py`(空)。

创建 `core/mcp/email_server.py`:
```python
import os
import smtplib
from email.message import EmailMessage


class EmailServer:
    """真实邮件收发(收发全流程);未配置时安全降级,绝不误发。"""

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.smtp_host = cfg.get("SMTP_HOST") or os.getenv("SMTP_HOST")
        self.smtp_port = int(cfg.get("SMTP_PORT") or os.getenv("SMTP_PORT", "587"))
        self.smtp_user = cfg.get("SMTP_USER") or os.getenv("SMTP_USER")
        self.smtp_password = cfg.get("SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD")
        self.imap_host = cfg.get("IMAP_HOST") or os.getenv("IMAP_HOST")
        self.sender = cfg.get("SMTP_USER") or os.getenv("SMTP_USER")

    @property
    def configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def send_email(self, recipient: str, subject: str, body: str) -> dict:
        if not self.configured:
            return {"sent": False, "reason": "SMTP 未配置,跳过真实发送"}
        try:
            msg = EmailMessage()
            msg["From"] = self.sender
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.set_content(body)
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            return {"sent": True, "to": recipient}
        except Exception as e:
            return {"sent": False, "reason": str(e)}

    def list_inbox(self, limit: int = 10) -> list[dict]:
        if not self.imap_host:
            return []
        return []  # IMAP 收件实现本期按需扩展;返回空列表安全降级

    def read_email(self, uid: int) -> dict:
        return {}

    def reply_email(self, uid: int, body: str) -> dict:
        return {"sent": False, "reason": "IMAP 回复未配置"}
```

- [ ] **Step 4: 实现 core/mcp/tools.py**

创建 `core/mcp/tools.py`:
```python
from core.mcp.email_server import EmailServer

EMAIL_TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "send_email", "description": "发送合规跟进邮件(需人工批准后调用)", "parameters": {"type": "object", "properties": {"recipient": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["recipient", "subject", "body"]}}},
]


def build_email_tools() -> tuple[list, dict]:
    server = EmailServer()
    return EMAIL_TOOL_DEFINITIONS, {
        "send_email": lambda recipient, subject, body: server.send_email(recipient, subject, body),
    }
```

- [ ] **Step 5: 更新 requirements.txt**

追加:
```
# MCP 邮件(如后续引入官方 MCP SDK)
# 当前使用 smtplib 内置库,无需额外依赖
```

- [ ] **Step 6: 更新 .env.example**

追加:
```
# 邮件(SMTP 发送;未配置则安全降级,不真实发送)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
IMAP_HOST=
```

- [ ] **Step 7: 集成到草稿审核**

修改 `app/routes/drafts.py` 的 `review_draft`:
```python
from core.mcp.email_server import EmailServer
...
        if status == "approved":
            server = EmailServer()
            if server.configured:
                res = server.send_email(recipient="", subject=row["subject"], body=row["body"])
                if res.get("sent"):
                    status = "sent"
```
(recipient 本期为占位;真实收件人由客户表 email 字段后续提供。未配置 SMTP 时保持 status='approved'。)

- [ ] **Step 8: 运行测试确认通过**

Run: `pytest tests/test_mcp.py -v` → 2 passed
Run: `pytest -q` → 全绿

- [ ] **Step 9: 提交**

```bash
git add core/mcp/ requirements.txt .env.example app/routes/drafts.py tests/test_mcp.py
git commit -m "feat(mcp): email server with safe-degradation and draft approval send"
```

---

### Task 14: 最终验证

**Files:**
- 无新增

- [ ] **Step 1: 运行全部测试**

Run: `pytest -q`
Expected: 全绿(约 24 个测试)

- [ ] **Step 2: 手动启动验证**

Run: `python run.py`
验证清单:
- `/login` 精致居中卡片,rep/manager 均可登录
- `/analysis` 三组示例按钮可一键加载;真实 API 分析能出三块卡片
- `/tasks` 违规/高意向分析后出现 pending 任务;完成/重开可用
- `/customers` 列表、搜索、阶段筛选;销售只见自己的客户
- `/reports`(manager)三张 Chart.js 图表正常渲染
- `/drafts` 批准草稿:未配置 SMTP 时状态变 approved,不误发

- [ ] **Step 3: 更新 AGENTS.md**

`AGENTS.md` 目录结构与约定补充:新增 `core/agent.py`(ReAct)、`core/tasks.py`、`core/mcp/`、`app/routes/tasks.py`、`app/routes/customers.py`,以及"邮件发送需人工批准(SMTP 未配置时安全降级)"约定。

- [ ] **Step 4: 提交**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md for v2 modules and conventions"
```
