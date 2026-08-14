# 销售 Agent i18n 国际化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为销售 Agent 的 Web 界面与后端系统提示词增加 zh-CN / zh-HK / en-US 三语言国际化,右上角下拉切换,静态文本即时切换。

**Architecture:** 新增 `app/i18n.py` 提供翻译字典与查询函数;通过 context-aware Jinja filter `t` 与自动注入 `lang` 的 `template_response` 包装,使全部现有路由无需改动即可渲染对应语言;新增 `/set-language/{lang}` 端点写 cookie;`core/agent.py` 增加 `get_system_prompt(lang)` 本地化提示词。保持 core 与 Web 分离,分析器提示词不动(结果仍跟随聊天语言)。

**Tech Stack:** Python 3.13, FastAPI, Jinja2, Pico.css, pytest。

## Global Constraints

- 设计文档:`docs/superpowers/specs/2026-08-14-sales-agent-i18n-design.md`(逐条遵循)
- 支持语言:`zh-CN`、`zh-HK`、`en-US`;默认 `zh-CN`
- 语言持久化:cookie `lang`;非法/缺失回退 `zh-CN`
- 翻译 key 缺失:回退 zh-CN → 再回退返回 key 本身,不中断页面
- 数据库枚举/状态值(`WARNING`/`PASSED`/`high`/`medium`/`low`/`invalid_lead` 等)不翻译,保留原样
- LLM 生成字段值不翻译;仅模板静态文本与展示型状态值翻译
- 后端 Agent 仅本地化 `core/agent.py` 的 `SYSTEM_PROMPT` 与工具描述;分析器提示词不动
- 任何 Agent 逻辑改动必须在 `core/` 内完成,`app/` 只负责展示与调用(AGENTS.md)
- `run_pipeline` 对外接口保持 `(llm, chat_text) -> PipelineResult` 不变,新增可选 `lang` 参数且默认 `zh-CN`
- 现有 27 个测试必须持续通过
- DeepSeek 密钥从 `.env` 读取,禁止硬编码

---

### Task 1: 新增 `app/i18n.py` — 翻译字典与查询函数

**Files:**
- Create: `app/i18n.py`
- Test: `tests/test_i18n.py`

**Interfaces:**
- Produces:
  - `SUPPORTED: dict[str, str]` — `{"zh-CN": "简体中文", "zh-HK": "繁體中文", "en-US": "English"}`
  - `DEFAULT_LANG: str = "zh-CN"`
  - `TRANSLATIONS: dict[str, dict[str, str]]` — 每语言词条表
  - `is_supported(lang) -> bool`
  - `t(key: str, lang: str | None = None) -> str` — 查表,回退 zh-CN → key
  - `get_lang(request) -> str` — 从 cookie 解析,非法回退
  - `set_lang_cookie(response, lang)` — 写 `Set-Cookie: lang=<lang>`
  - `ALL_KEYS: set[str]` — 三语言 key 全集的并集(供测试)

- [ ] **Step 1: 写失败测试**

创建 `tests/test_i18n.py`:
```python
from app import i18n


def test_supported_languages_and_default():
    assert i18n.DEFAULT_LANG == "zh-CN"
    assert set(i18n.SUPPORTED) == {"zh-CN", "zh-HK", "en-US"}


def test_all_languages_have_same_keys():
    key_sets = [set(m) for m in i18n.TRANSLATIONS.values()]
    assert key_sets[0] == key_sets[1] == key_sets[2]


def test_t_returns_value_for_existing_key():
    assert isinstance(i18n.t("nav.analysis", "zh-CN"), str)
    assert i18n.t("nav.analysis", "en-US") != ""


def test_t_falls_back_to_zh_cn_then_key():
    en_only_key = "only_en_key"
    assert i18n.t(en_only_key, "zh-CN") == en_only_key
    assert i18n.t(en_only_key, "en-US") == en_only_key


def test_t_defaults_to_zh_cn_when_lang_none():
    assert i18n.t("nav.analysis") == i18n.t("nav.analysis", "zh-CN")


def test_is_supported():
    assert i18n.is_supported("en-US")
    assert not i18n.is_supported("fr-FR")
    assert not i18n.is_supported("")
    assert not i18n.is_supported(None)


def test_get_lang_parses_cookie():
    class FakeRequest:
        cookies = {"lang": "en-US"}
    assert i18n.get_lang(FakeRequest()) == "en-US"


def test_get_lang_falls_back_on_invalid():
    class FakeRequest:
        cookies = {"lang": "fr-FR"}
    assert i18n.get_lang(FakeRequest()) == "zh-CN"

    class EmptyRequest:
        cookies = {}
    assert i18n.get_lang(EmptyRequest()) == "zh-CN"


def test_set_lang_cookie():
    class FakeResp:
        def __init__(self):
            self.cookies = {}

        def set_cookie(self, key, value, **kw):
            self.cookies[key] = value
    response = FakeResp()
    i18n.set_lang_cookie(response, "zh-HK")
    assert response.cookies["lang"] == "zh-HK"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_i18n.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.i18n'`

- [ ] **Step 3: 写实现**

创建 `app/i18n.py`,完整词条表(三语言 key 完全一致):

```python
from __future__ import annotations

DEFAULT_LANG = "zh-CN"

SUPPORTED = {
    "zh-CN": "简体中文",
    "zh-HK": "繁體中文",
    "en-US": "English",
}

_ZH_CN = {
    "app.title": "EduTech 课程销售合规与多语言跟进 Agent 系统",
    "nav.brand": "EduTech 销售 Agent",
    "nav.analysis": "分析",
    "nav.tasks": "任务",
    "nav.customers": "客户",
    "nav.drafts": "草稿",
    "nav.reports": "报表",
    "nav.logout": "退出",
    "lang.current": "语言",
    "login.title": "登录",
    "login.subtitle": "EduTech 课程销售合规与多语言跟进 Agent 系统",
    "login.username": "用户名",
    "login.password": "密码",
    "login.submit": "登录",
    "login.default_accounts": "默认账号:rep/123456(销售)、manager/123456(主管)",
    "login.error": "用户名或密码错误",
    "analysis.title": "分析",
    "analysis.header": "客户分析",
    "analysis.subtitle": "上传或粘贴销售聊天记录,系统将自动进行画像分析、合规审计与合规邮件生成。",
    "analysis.customer_name": "客户姓名(选填)",
    "analysis.customer_name_ph": "如:张女士",
    "analysis.chat_text": "聊天记录",
    "analysis.chat_text_ph": "在此粘贴客户与销售的聊天记录...",
    "analysis.submit": "开始分析",
    "analysis.failed": "分析失败:",
    "sample.risk_chat.label": "加载违规案例",
    "sample.english_lead.label": "加载英文客户案例",
    "sample.invalid_lead.label": "加载垃圾线索案例",
    "result.invalid_lead": "无效线索",
    "result.invalid_badge": "无效线索",
    "result.back": "返回分析",
    "result.profile": "客户画像",
    "result.profile.occupation": "职业背景",
    "result.profile.pain_point": "核心痛点",
    "result.profile.budget": "预算敏感度",
    "result.profile.intent": "成交意向度",
    "result.profile.language": "语言偏好",
    "result.compliance": "合规审计",
    "result.compliance.violation_type": "违规类型",
    "result.compliance.quote": "违规原句",
    "result.email": "邮件草稿",
    "result.email.subject": "主题",
    "result.email.spam_risk": "反垃圾风险",
    "result.email.view_drafts": "查看草稿并审核",
    "result.email.analyze_again": "再次分析",
    "tasks.title": "跟进任务",
    "tasks.th.id": "ID",
    "tasks.th.customer": "客户",
    "tasks.th.task": "任务",
    "tasks.th.owner": "负责人",
    "tasks.th.due": "截止",
    "tasks.th.status": "状态",
    "tasks.th.actions": "操作",
    "tasks.empty": "暂无跟进任务。",
    "status.pending": "待处理",
    "status.done": "已完成",
    "action.reopen": "重开",
    "action.complete": "完成",
    "customers.title": "客户管理",
    "customers.search_ph": "搜索客户名",
    "customers.all_stages": "全部阶段",
    "customers.filter": "筛选",
    "customers.th.id": "ID",
    "customers.th.name": "客户名",
    "customers.th.stage": "阶段",
    "customers.th.owner": "负责人",
    "customers.th.language": "语言",
    "customers.th.lead_status": "线索状态",
    "customers.th.last_contact": "最近联系",
    "customers.empty": "暂无客户。",
    "stage.leads": "线索",
    "stage.active": "进行中",
    "stage.lost": "流失",
    "stage.won": "成交",
    "lead_status.valid": "有效",
    "lead_status.invalid": "无效",
    "drafts.title": "邮件草稿",
    "drafts.th.id": "ID",
    "drafts.th.language": "语言",
    "drafts.th.subject": "主题",
    "drafts.th.owner": "创建人",
    "drafts.th.status": "状态",
    "drafts.th.actions": "操作",
    "draft.status.draft": "草稿",
    "draft.status.approved": "已批准",
    "draft.status.rejected": "已拒绝",
    "draft.status.sent": "已发送",
    "drafts.approve": "批准",
    "drafts.reject": "拒绝",
    "drafts.processed": "已处理",
    "drafts.empty": "暂无草稿。",
    "reports.title": "主管报表",
    "reports.metric.total": "总分析数",
    "reports.metric.invalid": "无效线索",
    "reports.metric.warnings": "合规警告",
    "reports.by_user": "各销售员分析统计",
    "reports.th.salesperson": "销售员",
    "reports.th.analyses": "分析数",
    "reports.th.warnings": "合规警告",
    "reports.th.invalid": "无效线索",
    "reports.chart.by_user": "各销售员分析数",
    "reports.chart.intent": "成交意向分布",
    "reports.chart.trend": "每日分析与合规警告",
    "reports.chart.analyses": "分析数",
    "reports.chart.warnings": "合规警告",
}

_ZH_HK = {
    "app.title": "EduTech 課程銷售合規與多語言跟進 Agent 系統",
    "nav.brand": "EduTech 銷售 Agent",
    "nav.analysis": "分析",
    "nav.tasks": "任務",
    "nav.customers": "客戶",
    "nav.drafts": "草稿",
    "nav.reports": "報表",
    "nav.logout": "登出",
    "lang.current": "語言",
    "login.title": "登入",
    "login.subtitle": "EduTech 課程銷售合規與多語言跟進 Agent 系統",
    "login.username": "用戶名",
    "login.password": "密碼",
    "login.submit": "登入",
    "login.default_accounts": "默認賬號:rep/123456(銷售)、manager/123456(主管)",
    "login.error": "用戶名或密碼錯誤",
    "analysis.title": "分析",
    "analysis.header": "客戶分析",
    "analysis.subtitle": "上傳或粘貼銷售聊天記錄,系統將自動進行畫像分析、合規審計與合規郵件生成。",
    "analysis.customer_name": "客戶姓名(選填)",
    "analysis.customer_name_ph": "如:張女士",
    "analysis.chat_text": "聊天記錄",
    "analysis.chat_text_ph": "在此粘貼客戶與銷售的聊天記錄...",
    "analysis.submit": "開始分析",
    "analysis.failed": "分析失敗:",
    "sample.risk_chat.label": "載入違規案例",
    "sample.english_lead.label": "載入英文客戶案例",
    "sample.invalid_lead.label": "載入垃圾線索案例",
    "result.invalid_lead": "無效線索",
    "result.invalid_badge": "無效線索",
    "result.back": "返回分析",
    "result.profile": "客戶畫像",
    "result.profile.occupation": "職業背景",
    "result.profile.pain_point": "核心痛點",
    "result.profile.budget": "預算敏感度",
    "result.profile.intent": "成交意向度",
    "result.profile.language": "語言偏好",
    "result.compliance": "合規審計",
    "result.compliance.violation_type": "違規類型",
    "result.compliance.quote": "違規原句",
    "result.email": "郵件草稿",
    "result.email.subject": "主題",
    "result.email.spam_risk": "反垃圾風險",
    "result.email.view_drafts": "查看草稿並審核",
    "result.email.analyze_again": "再次分析",
    "tasks.title": "跟進任務",
    "tasks.th.id": "ID",
    "tasks.th.customer": "客戶",
    "tasks.th.task": "任務",
    "tasks.th.owner": "負責人",
    "tasks.th.due": "截止",
    "tasks.th.status": "狀態",
    "tasks.th.actions": "操作",
    "tasks.empty": "暫無跟進任務。",
    "status.pending": "待處理",
    "status.done": "已完成",
    "action.reopen": "重開",
    "action.complete": "完成",
    "customers.title": "客戶管理",
    "customers.search_ph": "搜索客戶名",
    "customers.all_stages": "全部階段",
    "customers.filter": "篩選",
    "customers.th.id": "ID",
    "customers.th.name": "客戶名",
    "customers.th.stage": "階段",
    "customers.th.owner": "負責人",
    "customers.th.language": "語言",
    "customers.th.lead_status": "線索狀態",
    "customers.th.last_contact": "最近聯繫",
    "customers.empty": "暫無客戶。",
    "stage.leads": "線索",
    "stage.active": "進行中",
    "stage.lost": "流失",
    "stage.won": "成交",
    "lead_status.valid": "有效",
    "lead_status.invalid": "無效",
    "drafts.title": "郵件草稿",
    "drafts.th.id": "ID",
    "drafts.th.language": "語言",
    "drafts.th.subject": "主題",
    "drafts.th.owner": "創建人",
    "drafts.th.status": "狀態",
    "drafts.th.actions": "操作",
    "draft.status.draft": "草稿",
    "draft.status.approved": "已批准",
    "draft.status.rejected": "已拒絕",
    "draft.status.sent": "已發送",
    "drafts.approve": "批准",
    "drafts.reject": "拒絕",
    "drafts.processed": "已處理",
    "drafts.empty": "暫無草稿。",
    "reports.title": "主管報表",
    "reports.metric.total": "總分析數",
    "reports.metric.invalid": "無效線索",
    "reports.metric.warnings": "合規警告",
    "reports.by_user": "各銷售員分析統計",
    "reports.th.salesperson": "銷售員",
    "reports.th.analyses": "分析數",
    "reports.th.warnings": "合規警告",
    "reports.th.invalid": "無效線索",
    "reports.chart.by_user": "各銷售員分析數",
    "reports.chart.intent": "成交意向分佈",
    "reports.chart.trend": "每日分析與合規警告",
    "reports.chart.analyses": "分析數",
    "reports.chart.warnings": "合規警告",
}

_EN = {
    "app.title": "EduTech Course Sales Compliance & Multilingual Follow-up Agent System",
    "nav.brand": "EduTech Sales Agent",
    "nav.analysis": "Analysis",
    "nav.tasks": "Tasks",
    "nav.customers": "Customers",
    "nav.drafts": "Drafts",
    "nav.reports": "Reports",
    "nav.logout": "Logout",
    "lang.current": "Language",
    "login.title": "Sign in",
    "login.subtitle": "EduTech Course Sales Compliance & Multilingual Follow-up Agent System",
    "login.username": "Username",
    "login.password": "Password",
    "login.submit": "Sign in",
    "login.default_accounts": "Default accounts: rep/123456 (sales), manager/123456 (manager)",
    "login.error": "Incorrect username or password",
    "analysis.title": "Analysis",
    "analysis.header": "Customer Analysis",
    "analysis.subtitle": "Upload or paste sales chat records; the system will automatically run profiling, compliance audit, and compliant email generation.",
    "analysis.customer_name": "Customer Name (optional)",
    "analysis.customer_name_ph": "e.g. Ms. Zhang",
    "analysis.chat_text": "Chat Record",
    "analysis.chat_text_ph": "Paste the chat log between the customer and the salesperson here...",
    "analysis.submit": "Start analysis",
    "analysis.failed": "Analysis failed:",
    "sample.risk_chat.label": "Load risk case",
    "sample.english_lead.label": "Load English customer case",
    "sample.invalid_lead.label": "Load spam lead case",
    "result.invalid_lead": "Invalid Lead",
    "result.invalid_badge": "Invalid Lead",
    "result.back": "Back to analysis",
    "result.profile": "Customer Profile",
    "result.profile.occupation": "Occupation Background",
    "result.profile.pain_point": "Core Pain Point",
    "result.profile.budget": "Budget Sensitivity",
    "result.profile.intent": "Deal Intent",
    "result.profile.language": "Language Preference",
    "result.compliance": "Compliance Audit",
    "result.compliance.violation_type": "Violation Type",
    "result.compliance.quote": "Original Quote",
    "result.email": "Email Draft",
    "result.email.subject": "Subject",
    "result.email.spam_risk": "Spam Risk",
    "result.email.view_drafts": "View drafts & review",
    "result.email.analyze_again": "Analyze again",
    "tasks.title": "Follow-up Tasks",
    "tasks.th.id": "ID",
    "tasks.th.customer": "Customer",
    "tasks.th.task": "Task",
    "tasks.th.owner": "Owner",
    "tasks.th.due": "Due",
    "tasks.th.status": "Status",
    "tasks.th.actions": "Actions",
    "tasks.empty": "No follow-up tasks.",
    "status.pending": "Pending",
    "status.done": "Done",
    "action.reopen": "Reopen",
    "action.complete": "Complete",
    "customers.title": "Customer Management",
    "customers.search_ph": "Search customer name",
    "customers.all_stages": "All stages",
    "customers.filter": "Filter",
    "customers.th.id": "ID",
    "customers.th.name": "Customer",
    "customers.th.stage": "Stage",
    "customers.th.owner": "Owner",
    "customers.th.language": "Language",
    "customers.th.lead_status": "Lead Status",
    "customers.th.last_contact": "Last Contact",
    "customers.empty": "No customers.",
    "stage.leads": "Leads",
    "stage.active": "Active",
    "stage.lost": "Lost",
    "stage.won": "Won",
    "lead_status.valid": "Valid",
    "lead_status.invalid": "Invalid",
    "drafts.title": "Email Drafts",
    "drafts.th.id": "ID",
    "drafts.th.language": "Language",
    "drafts.th.subject": "Subject",
    "drafts.th.owner": "Creator",
    "drafts.th.status": "Status",
    "drafts.th.actions": "Actions",
    "draft.status.draft": "Draft",
    "draft.status.approved": "Approved",
    "draft.status.rejected": "Rejected",
    "draft.status.sent": "Sent",
    "drafts.approve": "Approve",
    "drafts.reject": "Reject",
    "drafts.processed": "Processed",
    "drafts.empty": "No drafts.",
    "reports.title": "Manager Reports",
    "reports.metric.total": "Total analyses",
    "reports.metric.invalid": "Invalid leads",
    "reports.metric.warnings": "Compliance warnings",
    "reports.by_user": "Statistics by salesperson",
    "reports.th.salesperson": "Salesperson",
    "reports.th.analyses": "Analyses",
    "reports.th.warnings": "Compliance warnings",
    "reports.th.invalid": "Invalid leads",
    "reports.chart.by_user": "Analyses by salesperson",
    "reports.chart.intent": "Deal intent distribution",
    "reports.chart.trend": "Daily analyses & compliance warnings",
    "reports.chart.analyses": "Analyses",
    "reports.chart.warnings": "Compliance warnings",
}

TRANSLATIONS = {"zh-CN": _ZH_CN, "zh-HK": _ZH_HK, "en-US": _EN}

ALL_KEYS = set(_ZH_CN)


def is_supported(lang) -> bool:
    return lang in SUPPORTED


def t(key: str, lang: str | None = None) -> str:
    lang = lang if is_supported(lang) else DEFAULT_LANG
    table = TRANSLATIONS.get(lang, _ZH_CN)
    if key in table:
        return table[key]
    if key in _ZH_CN:
        return _ZH_CN[key]
    return key


def get_lang(request) -> str:
    cookie = request.cookies.get("lang")
    return cookie if is_supported(cookie) else DEFAULT_LANG


def set_lang_cookie(response, lang) -> None:
    response.set_cookie("lang", lang, max_age=31536000)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_i18n.py -v`
Expected: 全部 PASS(若拼写不一致导致 key 集合不等则修正字典)

- [ ] **Step 5: 提交**

```bash
git add app/i18n.py tests/test_i18n.py
git commit -m "feat: add i18n translation dictionaries and helpers"
```

---

### Task 2: 接线 `templating.py` — context filter + 自动注入 lang

**Files:**
- Modify: `app/templating.py`
- Test: `tests/test_i18n.py`(追加)

**Interfaces:**
- Consumes: `app.i18n.t`, `app.i18n.get_lang`, `app.i18n.SUPPORTED`, `app.i18n.DEFAULT_LANG`
- Produces: 模板上下文自动含 `lang` 与 `SUPPORTED`;模板内可用 `{{ t('key') }}` 得到当前语言文案。

- [ ] **Step 1: 写失败测试(追加到 tests/test_i18n.py)**

```python
def test_t_filter_is_context_aware():
    from app.templating import templates

    tmpl = templates.env.from_string("{{ t('nav.analysis') }}")
    assert tmpl.render(lang="en-US") == "Analysis"
    assert tmpl.render(lang="zh-HK") == "分析"
    assert tmpl.render(lang="zh-CN") == "分析"
    assert tmpl.render(lang="fr-FR") == "分析"  # 非法 lang 回退 zh-CN
```

> note: 该测试验证 context-aware filter `t` 读取上下文 `lang` 并按语言翻译(可以在模板中直接调用 `{{ t('key') }}`)。base.html 的完整翻译与注入断言在 Task 4。若 filter 未注册或非 context-aware,上述断言失败。

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_i18n.py::test_t_filter_is_context_aware -v`
Expected: FAIL(`UndefinedError` / 未注册 filter)

- [ ] **Step 3: 写实现**

重写 `app/templating.py`:
```python
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.config import BASE_DIR
from app.i18n import DEFAULT_LANG, SUPPORTED, get_lang, t as _t

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@pass_context
def t(context, key, lang=None):
    lang = lang or context.get("lang", DEFAULT_LANG)
    return _t(key, lang)


templates.env.filters["t"] = t
templates.env.globals["t"] = t

_original = templates.TemplateResponse


def template_response(request, name, context=None, **kw):
    context = dict(context or {})
    context.setdefault("lang", get_lang(request))
    context.setdefault("SUPPORTED", SUPPORTED)
    return _original(request, name, context, **kw)


templates.TemplateResponse = template_response
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_i18n.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/templating.py tests/test_i18n.py
git commit -m "feat: inject lang and t filter into templates"
```

---

### Task 3: `main.py` 中间件 + `/set-language` 端点

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_i18n.py`(追加)

**Interfaces:**
- Consumes: `app.i18n.get_lang`, `app.i18n.set_lang_cookie`, `app.i18n.is_supported`, `app.i18n.SUPPORTED`
- Produces: 请求 `request.state.lang`;`GET /set-language/{lang}` 写 cookie 并重定向回 `Referer`(缺省 `/`)。

- [ ] **Step 1: 写失败测试(追加到 tests/test_i18n.py)**

```python
from starlette.testclient import TestClient
from app.main import app


def test_set_language_sets_cookie_and_redirects():
    client = TestClient(app)
    resp = client.get("/set-language/en-US", headers={"referer": "/analysis"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/analysis"
    assert resp.cookies["lang"] == "en-US"


def test_set_language_default_redirect():
    client = TestClient(app)
    resp = client.get("/set-language/zh-HK", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    assert resp.cookies["lang"] == "zh-HK"


def test_set_language_invalid_falls_back_redirect():
    client = TestClient(app)
    resp = client.get("/set-language/fr-FR", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] in ("/", "/login")
    assert resp.cookies["lang"] == "zh-CN"
```

> note: 三个测试若端点不存在将返回 404 → FAIL。

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_i18n.py -k set_language -v`
Expected: FAIL(404)

- [ ] **Step 3: 写实现**

修改 `app/main.py`:
- 在 `load_session` 中间件中,读取 cookie 写入 `request.state.lang`(`request.state.lang = get_lang(request)`),无 cookie 时也写入默认值。
- 新增路由(在 `app` 定义后):

```python
from fastapi.responses import RedirectResponse
from app.i18n import SUPPORTED, is_supported, set_lang_cookie


@app.get("/set-language/{lang}")
def set_language(lang: str, request: Request):
    target = lang if is_supported(lang) else "zh-CN"
    referer = request.headers.get("referer") or "/"
    response = RedirectResponse(referer, status_code=303)
    set_lang_cookie(response, target)
    return response
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_i18n.py -k set_language -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/main.py tests/test_i18n.py
git commit -m "feat: add set-language endpoint and lang middleware"
```

---

### Task 4: 改造 `base.html` 与 `login.html`

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/templates/login.html`

**Interfaces:**
- Consumes: 上下文 `lang`, `SUPPORTED`, filter `t`
- Produces: 动态 `<html lang>`;右上角语言下拉(登录/未登录均可见);导航与登录文案翻译。

- [ ] **Step 1: 改写 `base.html`**

替换以下内容(保留其余结构):
```html
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="/static/img/favicon.svg">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <link rel="stylesheet" href="/static/css/app.css">
    <title>{% block title %}{{ t('app.title') }}{% endblock %}</title>
</head>
<body>
<nav class="container-fluid">
    <ul><li><strong class="brand">{{ t('nav.brand') }}</strong></li></ul>
    <ul>
        <li>
            <details class="dropdown" style="position:relative;">
                <summary role="button" class="secondary">{{ t('lang.current') }}</summary>
                <ul>
                    {% for code, label in SUPPORTED.items() %}
                    <li><a href="/set-language/{{ code }}">{{ label }}</a></li>
                    {% endfor %}
                </ul>
            </details>
        </li>
    {% if request.state.session.get('username') %}
        <li><a href="/analysis">{{ t('nav.analysis') }}</a></li>
        <li><a href="/tasks">{{ t('nav.tasks') }}</a></li>
        <li><a href="/customers">{{ t('nav.customers') }}</a></li>
        <li><a href="/drafts">{{ t('nav.drafts') }}</a></li>
        {% if request.state.session.get('role') == 'manager' %}<li><a href="/reports">{{ t('nav.reports') }}</a></li>{% endif %}
        <li><a href="/logout">{{ t('nav.logout') }} ({{ request.state.session.get('username') }})</a></li>
    {% endif %}
    </ul>
</nav>
<main class="container">
    {% block content %}{% endblock %}
</main>
</body>
</html>
```

- [ ] **Step 2: 改写 `login.html`**

```html
{% extends "base.html" %}
{% block title %}{{ t('login.title') }} - {{ t('app.title') }}{% endblock %}
{% block content %}
<div class="card" style="max-width: 420px; margin: 4rem auto;">
    <hgroup>
        <h1 style="margin-bottom:0;">{{ t('login.title') }}</h1>
        <p>{{ t('login.subtitle') }}</p>
    </hgroup>
    {% if error %}<div class="error">{{ t('login.error') }}</div>{% endif %}
    <form method="post" action="/login">
        <label for="username">{{ t('login.username') }}</label>
        <input type="text" id="username" name="username" required autocomplete="username">
        <label for="password">{{ t('login.password') }}</label>
        <input type="password" id="password" name="password" required autocomplete="current-password">
        <button type="submit" style="margin-top:1rem;">{{ t('login.submit') }}</button>
    </form>
    <p style="font-size:0.8rem;color:var(--pico-muted-color,#888);">{{ t('login.default_accounts') }}</p>
</div>
{% endblock %}
```

- [ ] **Step 3: 手动冒烟验证 + 注入断言**

追加到 `tests/test_i18n.py` 的失败测试(验证包装函数注入 lang 到每个模板上下文):
```python
def test_template_response_injects_lang():
    from starlette.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/login", cookies={"lang": "en-US"})
    assert resp.status_code == 200
    assert 'lang="en-US"' in resp.text
    assert "Sign in" in resp.text
    assert "简体中文" not in resp.text
```

先运行确认 FAIL,再 `python run.py`,访问 `/login`,右上角出现语言下拉;切换 en-US 后登录页、导航、标题变英文;再运行上述断言确认 PASS。

- [ ] **Step 4: 运行全量测试**

Run: `python -m pytest -q`
Expected: 全部 PASS(含 Task 2 的 filter 测试与本 Task 的注入断言)

- [ ] **Step 5: 提交**

```bash
git add app/templates/base.html app/templates/login.html
git commit -m "feat: localize base layout and login page with language dropdown"
```

---

### Task 5: 改造 `analysis.html` 与 `result.html`

**Files:**
- Modify: `app/templates/analysis.html`
- Modify: `app/templates/result.html`
- Modify: `core/mock_data.py`(仅在 SAMPLE_CASES 中新增 `label_key`,不改变 `label` 兼容性)
- Modify: `app/routes/analysis.py`(错误文案与样例 label 键)

**Interfaces:**
- Consumes: filter `t`,上下文 `lang`
- Produces: 分析页与结果页静态文本翻译;sample 按钮 label 通过 `t(case.label_key)` 渲染。

- [ ] **Step 1: 改 `core/mock_data.py`**

为每个 `SAMPLE_CASES` 元素新增 `label_key` 字段:risk_chat → `"sample.risk_chat.label"`,english_lead → `"sample.english_lead.label"`,invalid_lead → `"sample.invalid_lead.label"`。保留原 `label` 字段不动。

```python
SAMPLE_CASES = [
    {"key": "risk_chat", "label_key": "sample.risk_chat.label", "label": "加载违规案例", "title": "...", "text": "..."},
    {"key": "english_lead", "label_key": "sample.english_lead.label", "label": "加载英文客户案例", "title": "...", "text": "..."},
    {"key": "invalid_lead", "label_key": "sample.invalid_lead.label", "label": "加载垃圾线索案例", "title": "...", "text": "..."},
]
```

- [ ] **Step 2: 改 `analysis.html`**

替换模板文本为 `{{ t('...') }}`:
- `block title`:`{{ t('analysis.title') }} - {{ t('app.title') }}`
- h1 `客户分析` → `{{ t('analysis.header') }}`
- `<p>` 介绍 → `{{ t('analysis.subtitle') }}`
- 错误行:若存在 `error`,改为 `<div class="error">{{ t('analysis.failed') }} {{ error }}</div>`
- 样例按钮 label → `{{ t(case.label_key) }}`
- 表单三个 label / placeholder → `{{ t('analysis.customer_name') }}`、`{{ t('analysis.customer_name_ph') }}`、`{{ t('analysis.chat_text') }}`、`{{ t('analysis.chat_text_ph') }}`
- 提交按钮 → `{{ t('analysis.submit') }}`

- [ ] **Step 3: 改 `app/routes/analysis.py`**

错误返回块改为把 `analysis.failed` 前缀交给模板,路由只传具体错误文本:
```python
return templates.TemplateResponse(
    request,
    "analysis.html",
    {"sample_cases": SAMPLE_CASES, "error": str(e)},
)
```

- [ ] **Step 4: 改写 `result.html`**

替换静态文本:
- `block title` → `{{ t('result.profile') }} - {{ t('app.title') }}`
- invalid 分支:
  - h1 `无效线索` → `{{ t('result.invalid_lead') }}`;badge `无效线索` → `{{ t('result.invalid_badge') }}`
  - 返回按钮 → `{{ t('result.back') }}`
- 画像卡:h1 `客户画像` → `{{ t('result.profile') }}`(保留 `{% if customer_name %} - {{ customer_name }}{% endif %}`)
  - 表头职业背景/核心痛点/预算敏感度/成交意向度/语言偏好 → `{{ t('result.profile.occupation') }}` 等
  - 单元格内容(`result.customer_profile.*`)与 `language_preference.value` **不翻译**
- 合规卡:h1 `合规审计` → `{{ t('result.compliance') }}`;badge `WARNING`/`PASSED` 保持原样
  - `{{ result.compliance_report.summary }}` 不翻译
  - 表头 `违规类型`/`违规原句` → `{{ t('result.compliance.violation_type') }}` / `{{ t('result.compliance.quote') }}`;单元格 `v.violation_type`/`v.quote` 不翻译
- 邮件卡:h1 `邮件草稿 (...)` → `{{ t('result.email') }} (...)`;`Subject:` → `{{ t('result.email.subject') }}:`;`反垃圾风险:` → `{{ t('result.email.spam_risk') }}:`;high/medium/low badge 原样
  - 链接 → `{{ t('result.email.view_drafts') }}`、`{{ t('result.email.analyze_again') }}`

- [ ] **Step 5: 运行全量测试**

Run: `python -m pytest -q`
Expected: 全部 PASS(test_pipeline/test_agent 依赖的 schema 与行为不变)

- [ ] **Step 6: 提交**

```bash
git add app/templates/analysis.html app/templates/result.html core/mock_data.py app/routes/analysis.py
git commit -m "feat: localize analysis and result pages"
```

---

### Task 6: 改造 `tasks.html` / `customers.html` / `drafts.html`

**Files:**
- Modify: `app/templates/tasks.html`
- Modify: `app/templates/customers.html`
- Modify: `app/templates/drafts.html`

**Interfaces:**
- Consumes: filter `t`
- Produces: 页面标题、表头、状态徽章、按钮、空状态文案翻译。

- [ ] **Step 1: 改写 `tasks.html`**

```html
{% extends "base.html" %}
{% block title %}{{ t('tasks.title') }} - {{ t('app.title') }}{% endblock %}
{% block content %}
<h1>{{ t('tasks.title') }}</h1>
{% if tasks %}
<table>
    <thead><tr><th>{{ t('tasks.th.id') }}</th><th>{{ t('tasks.th.customer') }}</th><th>{{ t('tasks.th.task') }}</th><th>{{ t('tasks.th.owner') }}</th><th>{{ t('tasks.th.due') }}</th><th>{{ t('tasks.th.status') }}</th><th>{{ t('tasks.th.actions') }}</th></tr></thead>
    <tbody>
    {% for tsk in tasks %}
    <tr>
        <td>{{ tsk.id }}</td><td>{{ tsk.customer or '-' }}</td><td>{{ tsk.title }}</td><td>{{ tsk.owner }}</td><td>{{ tsk.due_date }}</td>
        <td><span class="badge {{ tsk.status }}">{{ t('status.' ~ tsk.status) }}</span></td>
        <td><form method="post" action="/tasks/{{ tsk.id }}/toggle" style="display:inline;">
            <button type="submit">{% if tsk.status == 'done' %}{{ t('action.reopen') }}{% else %}{{ t('action.complete') }}{% endif %}</button>
        </form></td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">{{ t('tasks.empty') }}</div>
{% endif %}
{% endblock %}
```

> note: 原模板变量名是 `t`,与 filter `t` 冲突。上面改用 `tsk`。`t('status.' ~ tsk.status)` 支持 `status.pending`/`status.done`。flexible 变量命名须在实现中全局一致。

- [ ] **Step 2: 改写 `customers.html`**

替换:h1 → `{{ t('customers.title') }}`;搜索 placeholder → `{{ t('customers.search_ph') }}`;`全部阶段` → `{{ t('customers.all_stages') }}`;`筛选` → `{{ t('customers.filter') }}`;表头 → `{{ t('customers.th.*') }}`;`stage` 徽章 → `{{ t('stage.' ~ c.stage) }}`;`lead_status` 徽章 → `{{ t('lead_status.' ~ c.lead_status) }}`;空状态 → `{{ t('customers.empty') }}`。`c.stage`/`c.lead_status`/`c.language` 的原始值不翻译(仅徽章展示文本翻译)。

- [ ] **Step 3: 改写 `drafts.html`**

替换:h1 → `{{ t('drafts.title') }}`;表头 → `{{ t('drafts.th.*') }}`;状态徽章 → `{{ t('draft.status.' ~ d.status) }}`;按钮 `批准`/`拒绝` → `{{ t('drafts.approve') }}`/`{{ t('drafts.reject') }}`;`已处理` → `{{ t('drafts.processed') }}`;空状态 → `{{ t('drafts.empty') }}`。`d.language`/`d.subject` 原值不翻译。

- [ ] **Step 4: 运行全量测试**

Run: `python -m pytest -q`
Expected: 全部 PASS

- [ ] **Step 5: 手动冒烟**

Run: `python run.py`,切换 en-US 后检查任务/客户/草稿三页表头与状态徽章为英文。

- [ ] **Step 6: 提交**

```bash
git add app/templates/tasks.html app/templates/customers.html app/templates/drafts.html
git commit -m "feat: localize tasks, customers, drafts pages"
```

---

### Task 7: 改造 `reports.html`

**Files:**
- Modify: `app/templates/reports.html`

**Interfaces:**
- Consumes: filter `t`
- Produces: 指标名、表头、图表标题与 dataset label 翻译。

- [ ] **Step 1: 改写 `reports.html` 静态文本与图表标签**

替换:
- `block title` → `{{ t('reports.title') }} - {{ t('app.title') }}`;h1 → `{{ t('reports.title') }}`
- 三个指标文案 → `{{ t('reports.metric.total') }}` / `{{ t('reports.metric.invalid') }}` / `{{ t('reports.metric.warnings') }}`
- `各销售员分析统计` → `{{ t('reports.by_user') }}`;表头 → `{{ t('reports.th.salesperson') }}`/`{{ t('reports.th.analyses') }}`/`{{ t('reports.th.warnings') }}`/`{{ t('reports.th.invalid') }}`
- 图表标题(三个 `<h2>`):
  - `各销售员分析数` → `{{ t('reports.chart.by_user') }}`
  - `成交意向分布` → `{{ t('reports.chart.intent') }}`
  - `每日分析与合规警告` → `{{ t('reports.chart.trend') }}`
- 图表 JS dataset label(用 Jinja 在 tojson 前翻译):
```html
<script>
const byUser = {{ by_user | tojson }};
const intentData = {{ intent_data | tojson }};
const trendData = {{ trend_data | tojson }};
new Chart(document.getElementById('byUserChart'), { type: 'bar', data: { labels: byUser.map(r=>r.username), datasets: [{ label: {{ t('reports.chart.analyses') | tojson }}, data: byUser.map(r=>r.analyses), backgroundColor:'#1976d2' }] } });
new Chart(document.getElementById('intentChart'), { type: 'pie', data: { labels: intentData.map(r=>r.intent), datasets: [{ data: intentData.map(r=>r.n), backgroundColor:['#1976d2','#e65100','#2e7d32'] }] } });
new Chart(document.getElementById('trendChart'), { type: 'line', data: { labels: trendData.map(r=>r.day), datasets: [{ label: {{ t('reports.chart.analyses') | tojson }}, data: trendData.map(r=>r.n), borderColor:'#1976d2' }, { label: {{ t('reports.chart.warnings') | tojson }}, data: trendData.map(r=>r.warns), borderColor:'#e65100' }] } });
</script>
```

- [ ] **Step 2: 运行全量测试 + 手动冒烟**

Run: `python -m pytest -q`;`python run.py` 以 manager 登录切换语言确认报表页翻译。
Expected: 全部 PASS;报表页指标/表头/图表英文。

- [ ] **Step 3: 提交**

```bash
git add app/templates/reports.html
git commit -m "feat: localize reports page and charts"
```

---

### Task 8: 后端 Agent 提示词本地化

**Files:**
- Modify: `core/agent.py`
- Modify: `core/pipeline.py`
- Modify: `app/routes/analysis.py`
- Modify: `tests/test_agent.py`(追加)

**Interfaces:**
- Consumes: `app.i18n` 需要语言常量;但为保持 core 不依赖 app,在 `core/agent.py` 内定义 `AGENT_DEFAULT_LANG = "zh-CN"` 与适配器 `_is_supported`.
- Produces:
  - `core/agent.get_system_prompt(lang) -> tuple[str, list[dict]]` 返回 `(本地化 SYSTEM_PROMPT, 本地化 TOOL_DEFINITIONS)`
  - `core/agent.run_agent(llm, chat_text, lang=AGENT_DEFAULT_LANG)`
  - `core.pipeline.run_pipeline(llm, chat_text, lang="zh-CN")`
  - `app/routes/analysis.py` 把 `request.state.lang` 传入 `run_pipeline`

- [ ] **Step 1: 写失败测试(追加到 tests/test_agent.py)**

```python
from core import agent


def test_get_system_prompt_default_is_chinese():
    sys, tools = agent.get_system_prompt("zh-CN")
    assert "数据分析" in sys
    assert tools[0]["function"]["name"] == "check_spam"


def test_get_system_prompt_english():
    sys, tools = agent.get_system_prompt("en-US")
    assert "compliance" in sys.lower() or "agent" in sys.lower()
    assert len(tools) == 5


def test_get_system_prompt_invalid_falls_back():
    sys, _ = agent.get_system_prompt("fr-FR")
    assert "数据分析" in sys
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_agent.py -k get_system_prompt -v`
Expected: FAIL(`AttributeError: module 'core.agent' has no attribute 'get_system_prompt'`)

- [ ] **Step 3: 写实现**

在 `core/agent.py` 添加:

```python
AGENT_DEFAULT_LANG = "zh-CN"
_AGENT_LANGS = {"zh-CN", "zh-HK", "en-US"}

_AGENT_SYSTEM_PROMPTS = {
    "zh-CN": (
        "你是 EduTech《数据分析与 AI 工具实战班》(售价 ¥2,999,4 周线上课程)的销售合规 Agent。\n"
        "合规红线:严禁保证就业、保底薪资、包学会、拒绝退款、虚假稀缺。\n"
        "流程:先用 check_spam 判断线索有效性;有效则用 analyze_profile 提取画像,"
        "用 audit_compliance 审计聊天合规性,再用 generate_email 生成合规邮件(语言跟随客户画像),"
        "最后用 check_email_spam 复查。工具观察结果请基于聊天记录推理,最终只输出一个符合 PipelineResult 的 JSON。"
    ),
    "zh-HK": (
        "你是 EduTech《數據分析與 AI 工具實戰班》(售價 ¥2,999,4 週線上課程)的銷售合規 Agent。\n"
        "合規紅線:嚴禁保證就業、保底薪資、包學會、拒絕退款、虛假稀缺。\n"
        "流程:先用 check_spam 判斷線索有效性;有效則用 analyze_profile 提取畫像,"
        "用 audit_compliance 審計聊天合規性,再用 generate_email 生成合規郵件(語言跟隨客戶畫像),"
        "最後用 check_email_spam 複查。工具觀察結果請基於聊天記錄推理,最終只輸出一個符合 PipelineResult 的 JSON。"
    ),
    "en-US": (
        "You are the sales-compliance Agent for EduTech's \"Data Analytics & AI Tools Bootcamp\" "
        "(price ¥2,999, 4-week online course).\n"
        "Compliance red lines: NO guaranteed employment, NO minimum-salary promises, NO \"100% learned\" claims, "
        "NO refusing refunds, and NO creating false scarcity.\n"
        "Flow: first call check_spam to decide if the lead is valid; if valid, extract a profile with "
        "analyze_profile, audit the chat with audit_compliance, then generate a compliant follow-up email "
        "with generate_email (language follows the customer profile), and finally re-check the email with "
        "check_email_spam. Reason about tool observations from the chat record; return exactly one JSON "
        "matching the PipelineResult schema."
    ),
}

_TOOL_DESCRIPTIONS = {
    "check_spam": {
        "zh-CN": "判断聊天是否为无效线索",
        "zh-HK": "判斷聊天是否為無效線索",
        "en-US": "Decide whether the chat is an invalid/spam lead",
    },
    "analyze_profile": {
        "zh-CN": "提取客户画像",
        "zh-HK": "提取客戶畫像",
        "en-US": "Extract the customer profile",
    },
    "audit_compliance": {
        "zh-CN": "审计聊天记录合规风险",
        "zh-HK": "審計聊天記錄合規風險",
        "en-US": "Audit the chat record for compliance risks",
    },
    "generate_email": {
        "zh-CN": "生成合规跟进邮件",
        "zh-HK": "生成合規跟進郵件",
        "en-US": "Generate a compliant follow-up email",
    },
    "check_email_spam": {
        "zh-CN": "检查邮件反垃圾风险",
        "zh-HK": "檢查郵件反垃圾風險",
        "en-US": "Check the email for spam risk",
    },
}

_BASE_TOOL_NAMES = [
    "check_spam", "analyze_profile", "audit_compliance", "generate_email", "check_email_spam",
]


def _resolve_lang(lang):
    return lang if lang in _AGENT_LANGS else AGENT_DEFAULT_LANG


def get_system_prompt(lang="zh-CN"):
    lang = _resolve_lang(lang)
    system = _AGENT_SYSTEM_PROMPTS[lang]
    tools = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": _TOOL_DESCRIPTIONS[name][lang],
                "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]},
            },
        }
        for name in _BASE_TOOL_NAMES
    ]
    return system, tools
```

修改 `run_agent`:
```python
def run_agent(llm: LLMClient, chat_text: str, lang: str = AGENT_DEFAULT_LANG):
    system_prompt, tools = get_system_prompt(lang)
    registry, state = _make_executor(llm)
    llm.complete_tool_loop(
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": f"聊天记录:\n{chat_text}"}],
        tools=tools,
        execute=lambda name, args: registry[name](**args),
    )
    ...  # 其余不变
```

> note: 保留原模块级 `SYSTEM_PROMPT` 与 `TOOL_DEFINITIONS` 常量不变(若有测试引用),`get_system_prompt` 默认值等价 zh-CN。

修改 `core/pipeline.py`:
```python
from core.agent import AGENT_DEFAULT_LANG, run_agent


def run_pipeline(llm: LLMClient, chat_text: str, lang: str = AGENT_DEFAULT_LANG) -> PipelineResult:
    return run_agent(llm, chat_text, lang=lang)
```

修改 `app/routes/analysis.py` 的调用:
```python
lang = getattr(request.state, "lang", "zh-CN")
result = run_pipeline(llm, chat_text, lang=lang)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest -q`
Expected: 全部 PASS(现有 test_agent/test_pipeline 仍绿,因默认 zh-CN 等价)

- [ ] **Step 5: 提交**

```bash
git add core/agent.py core/pipeline.py app/routes/analysis.py tests/test_agent.py
git commit -m "feat: localize agent system prompt and tool descriptions"
```

---

### Task 9: 全量回归与完成

**Files:**
- None(仅验证)

- [ ] **Step 1: 运行全部测试**

Run: `python -m pytest -q`
Expected: 全部 PASS(27 个原测试 + 新增 i18n/agent prompt 测试)

- [ ] **Step 2: 手动端到端验证**

Run: `python run.py`
- 首访 `/login`:`<html lang="zh-CN">`,右上角下拉,默认简体。
- 切 en-US → 整站静态文本英文;切 zh-HK → 繁体;刷新保持。
- 以 rep 登录跑一次分析,结果页表头翻译、LLM 单元格内容英文/中文随聊天语言。
- manager 登录 `/reports`:指标、表头、图表标题英文。
- 直接访问 `/set-language/fr-FR`:重定向且 cookie 回退 zh-CN,页面不报错。

- [ ] **Step 3: 确认 git 状态干净**

Run: `git status`
Expected: 无未提交改动。

- [ ] **Step 4: 提交收尾(若有遗漏)**(如需合并且有未提交改动):`git add . && git commit -m "chore: i18n final fixes"`