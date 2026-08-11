# AGENTS.md — 销售 Agent 项目

本文件为 AI 助手在该仓库工作时的行为约定与项目指南。

## 项目概述

销售 Agent:本地运行的 Web 应用,供销售部门使用。销售员上传/粘贴聊天记录,系统自动完成客户画像分析、合规风险审计、合规邮件草稿生成(含垃圾邮件过滤),主管可查看历史与报表。基于 Python + DeepSeek + FastAPI + SQLite + Jinja2。

设计文档见 `docs/superpowers/specs/2026-08-10-sales-agent-design.md`;v2 设计见 `docs/superpowers/specs/2026-08-11-sales-agent-v2-design.md`,实施计划见 `docs/superpowers/plans/2026-08-11-sales-agent-v2.md`。

## 目录结构

- `core/` — Agent 核心逻辑(不依赖 Web,可独立测试)
  - `llm_client.py` — DeepSeek 封装(含 ReAct 工具循环 `complete_tool_loop`)
  - `schemas.py` — Pydantic 数据结构
  - `agent.py` — ReAct Agent 主循环(工具注册表 + 系统提示 + 最终 PipelineResult 组装)
  - `pipeline.py` — `run_pipeline` 委托 ReAct Agent
  - `tasks.py` — 跟进任务自动创建规则(WARNING/High 意向)
  - `analyzers/` — `profiler.py`(画像)、`compliance.py`(合规)、`spam.py`(垃圾识别)、`email_writer.py`(邮件)
  - `mcp/` — `email_server.py`(SMTP 收发,安全降级)、`tools.py`(邮件工具定义)
- `app/` — Web 层(FastAPI 路由、Jinja2 模板、auth、db)
  - `routes/` — `auth`、`analysis`、`drafts`、`reports`、`tasks`、`customers`
- `tests/` — 单元测试(mock LLM:`tests/agent_stub.py` 提供 ScriptedClient)
- `docs/superpowers/specs/` — 设计文档
- `docs/superpowers/plans/` — 实施计划

## 关键约定

- **核心与 Web 分离**:任何 Agent 逻辑改动必须在 `core/` 内完成,`app/` 只负责展示与调用。
- **禁止硬编码密钥**:DeepSeek 密钥(`DEEPSEEK_API_KEY`)与 `SECRET_KEY` 一律从 `.env` 读取,`SECRET_KEY` 缺失时启动报错,源码中禁止硬编码。
- **结构化输出**:模型输出必须用 Pydantic schema 校验,禁止用字符串切割解析。
- **邮件发送需人工批准(HITL)**:Agent 不直接发邮件;SMTP 未配置时安全降级,绝不误发。
- **中英自动适配**:邮件语言跟随聊天记录语言。
- **密码 hash 加盐**:使用 werkzeug `pbkdf2:sha256:600000`,不使用明文或 RSA。
- **git 提交**:关键代码完成后及时 `git add` + `git commit`。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
python run.py

# 运行测试
pytest
```

## 验证

- 改动 `core/` 后运行 `pytest`,确保单元测试通过。
- 改动 Web 层后手动启动 `python run.py` 验证页面与权限。
