# 销售 Agent v2 设计文档

- 日期:2026-08-11
- 状态:已确认
- 基础:基于 `2026-08-10-sales-agent-design.md` 的 v1 迭代

## 1. 目标

在 v1(EduTech 合规销售 Agent)基础上做 4 项升级:

| 阶段 | 内容 |
|---|---|
| A | UI 美化(精致简洁风,引入 Pico.css) |
| B | 新增功能:跟进提醒/任务、可视化报表、客户管理 |
| C | 核心改造:固定流水线 → ReAct 自主决策 Agent 循环 |
| D | 安全加固(hash 加盐)+ MCP 真实邮件收发全流程 |

## 2. A. UI 美化

- 引入 **Pico.css**(单文件、语义化、无构建步骤),配合 `app/static/css/app.css` 定制
- 重做全部 6 个模板(`base/login/analysis/result/drafts/reports`)的样式
- **约束:页面结构、路由、表单字段不变,只改样式**,最小化回归风险

## 3. B. 新增功能

### B1 跟进提醒 / 任务
- 新表 `tasks`:id, assigned_to, customer_id, title, due_date, status(`pending`/`done`/`overdue`)
- `/tasks` 页面:销售员看自己的待办与逾期(逾期标红),主管看全部
- 自动建任务规则:`analyses` 判定 `WARNING` 或成交意向 `High` 时,为分析人创建跟进任务

### B2 可视化报表
- `reports.html` 引入 **Chart.js**(CDN),数据仍由现有 SQL 聚合提供
- 新增图表:违规率趋势、各销售员分析数柱状图、成交意向分布饼图

### B3 客户管理
- `customers` 表扩展列:stage(`leads`/`active`/`lost`/`won`)、owner_id、last_contact_at
- 新页面 `/customers`:客户列表、搜索、状态筛选、查看客户全部分析历史
- 权限:销售员只见自己的客户,主管可见全部

### DB 迁移
- 启动时执行轻量迁移:`CREATE TABLE IF NOT EXISTS tasks` + `ALTER TABLE customers ADD COLUMN ...`
- 迁移幂等(用列存在性检查),放在 `app/db.py`

## 4. C. ReAct 自主决策改造

### 4.1 `core/llm_client.py` 扩展
- 新增 `complete_tool_loop(...)`:OpenAI 工具调用(DeepSeek 兼容 function calling)循环
- 循环逻辑:模型输出 → 请求工具则执行并回传结果 → 继续,直到产出最终结构化答案
- 保留 `complete_structured` 供简单步骤使用

### 4.2 `core/agent.py`(新)
- ReAct 主循环:`Thought → Action(工具调用)→ Observation → ... → Final Answer`
- 工具注册表,现有分析器包装为工具:
  - `analyze_profile(chat)`
  - `audit_compliance(chat)`
  - `check_spam(chat)`
  - `generate_email(profile, violations)`
  - `check_email_spam(draft)`
  - `search_customer(name)`
  - `create_followup_task(...)`
- 系统提示注入 EduTech 业务上下文与合规红线
- 最大迭代上限(8 步)防死循环

### 4.3 `core/pipeline.py`
- 保留 `run_pipeline` 对外接口(Web 层与现有测试不破坏),内部改为调用 agent 循环
- 输出仍为 `PipelineResult`

### 4.4 测试
- 现有 13 个测试保持通过
- 新增 agent 循环测试:mock LLM 返回工具调用序列,验证多步编排与最终结果

## 5. D. 安全 + MCP 邮件

### D1 密码安全(hash 加盐)
- 沿用 werkzeug `generate_password_hash`(PBKDF2 加盐),提高迭代轮数(`pbkdf2:sha256:600000`)
- `SECRET_KEY` 从 `.env` 配置,不提供明文默认值

### D2 MCP 真实邮件(收发全流程)
- `core/mcp/email_server.py`:MCP 服务器,暴露工具 `send_email`、`list_inbox`、`read_email`、`reply_email`
- `core/mcp/tools.py`:供 ReAct 工具注册表调用的封装
- 邮件服务默认 **Gmail(Google Workspace MCP)**,实现时按实际邮箱调整;配置从 `.env` 读取
- 流程:生成草稿 → 人工审核批准(HITL)→ Agent 调用 `send_email` 真实发送;支持收取并解析新邮件作为分析输入
- 邮件动作更新 `email_drafts.status`(draft/approved/sent/rejected)

### 安全边界
- 发送必须经过人工批准(HITL),Agent 不得未经审核直接发邮件

## 6. 验证

- 每阶段完成跑 `pytest` 保持全绿
- 最终手动 `python run.py` 验证页面、权限与邮件流程

## 7. 非目标(本期不做)

- 不做 RSA 密码存储(经确认,采用 hash 加盐)
- 不接入 IM / CRM 自动同步
