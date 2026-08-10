# 销售 Agent 系统设计文档

- 日期:2026-08-10
- 状态:已确认
- 目标用户:销售部门(销售员 + 销售主管/经理)

## 1. 背景与目标

当前项目(`email/`、`bak/`)是一组 DeepSeek 驱动的销售脚本原型:读取聊天记录,提取客户画像,识别销售话术合规风险,生成英文跟进邮件草稿,人工确认后模拟发送。脚本间重复严重、密钥硬编码、逻辑与界面耦合,无法交付给销售部门使用。

目标:重构为 **本地运行的 Web 应用**,销售员上传/粘贴聊天记录,系统自动完成客户画像分析、合规风险审计、合规邮件草稿生成(含垃圾邮件过滤),主管可查看历史记录与报表。本版本只生成邮件草稿,不真实发送。

## 2. 需求确认

| 项 | 确认结果 |
|---|---|
| 交付形态 | Web 应用,本地运行 |
| 使用者 | 销售员 + 销售主管/经理 |
| 登录权限 | 需要登录,区分 `rep` / `manager` 角色 |
| 聊天记录来源 | 手动上传/粘贴 |
| 核心功能 | 客户画像分析、合规风险审计、合规邮件生成、历史记录与报表、垃圾邮件过滤(无效线索识别 + 邮件反垃圾) |
| 邮件发送 | 仅生成草稿,人工在网页审核,不真实发送 |
| 客户语言 | 中英混合自动适配 |
| 技术栈 | Python + DeepSeek + FastAPI + SQLite + Jinja2 |

## 3. 总体架构

核心原则:Agent 核心逻辑与 Web 界面彻底分离,核心可独立测试,未来接入 CRM 只需增加接口。

```
sales-agent/
├── run.py                  # 一键启动入口
├── requirements.txt
├── .env                    # DeepSeek 密钥(加入 .gitignore, 禁止硬编码)
├── README.md
├── app/                    # Web 层
│   ├── main.py             # FastAPI 入口 + 路由注册
│   ├── config.py           # 从 .env 读配置
│   ├── db.py               # SQLite 连接与建表
│   ├── auth.py             # 登录/会话/角色校验
│   ├── routes/
│   │   ├── auth.py         # 登录登出
│   │   ├── analysis.py     # 上传/粘贴聊天 → 分析
│   │   ├── drafts.py       # 草稿列表/查看/审核
│   │   └── reports.py      # 报表(仅 manager)
│   ├── templates/          # Jinja2 页面
│   └── static/
├── core/                   # Agent 核心(不依赖 Web)
│   ├── llm_client.py       # DeepSeek 封装
│   ├── schemas.py          # Pydantic 数据结构
│   ├── pipeline.py         # 步骤编排
│   └── analyzers/
│       ├── profiler.py     # 客户画像
│       ├── compliance.py   # 合规审计 + 生成邮件复查
│       ├── spam.py         # 无效线索识别 + 邮件反垃圾
│       └── email_writer.py # 合规邮件生成(结构化 JSON 输出)
└── tests/                  # 核心逻辑单元测试
```

### 3.1 与现有代码的关键差异

- 消灭 `email/main.py`、`email/agent_with_tools.py`、`bak/` 下的重复脚本,统一为 `core/pipeline.py` 一条流水线
- DeepSeek 密钥从硬编码改为 `.env` 加载,移除所有源码中的 key
- 邮件解析从"字符串切割"改为结构化 JSON 输出 + Pydantic 校验

## 4. 数据模型(SQLite)

| 表 | 字段 | 说明 |
|---|---|---|
| `users` | id, username, password_hash, role(`rep`/`manager`) | 用户 |
| `customers` | id, name, language, source_chat, lead_status(`valid`/`invalid`) | 客户主档,保存原始聊天 |
| `analyses` | id, customer_id, created_by, profile_json, compliance_json, spam_json, verdict | 一次分析的结果 |
| `email_drafts` | id, analysis_id, subject, body, language, status(`draft`/`approved`/`rejected`), created_by | 生成的草稿与审核状态 |

报表用 SQL 聚合 `analyses` / `email_drafts` 得出,不另建表。

## 5. Agent 流水线

`core/pipeline.py` 顺序执行:

```
Step 0  语言检测(中/英/混合 → 决定邮件语言)
Step 1  无效线索识别(spam)→ 判为无效线索则终止, 不再生成邮件
Step 2  客户画像分析 → 结构化 JSON(痛点/预算敏感度/成交概率)
Step 3  合规审计 → 提取销售话术中的违规承诺, 输出违规清单 + verdict
Step 4  邮件生成 → 结构化 JSON 输出 Subject/Body(Pydantic 校验)
Step 5  邮件复查 → 对生成的邮件再跑一次合规 + 反垃圾检查
Step 6  落库 + 保存草稿 → 销售员在网页审核(批准/拒绝)
```

### 5.1 合规规则(示例)

违规话术包括但不限于:
- 保证就业 / 保底年薪(如"保证 20 万年薪")
- 100% 掌握 / 包学会
- 虚假稀缺施压(如"仅剩最后一个名额")
- 拒绝退款等误导性承诺

生成的邮件必须避免上述承诺,并复查通过后才进入草稿。

## 6. Web 层与权限

- 页面:`/login`、`/analysis`(上传/粘贴聊天)、`/drafts`(草稿列表与审核)、`/reports`(主管报表)
- 权限:`rep` 只可见自己的分析与草稿;`manager` 可见全部 + 报表(违规率、各销售分析数)
- 会话使用 FastAPI session,密码使用 werkzeug 哈希存储

## 7. 错误处理

- LLM 调用超时/失败重试 1 次,统一返回中文错误提示
- 结构化 JSON 用 Pydantic 校验,校验失败自动重新生成(最多 2 次)
- 分析记录异常状态也落库,不中断整体流程

## 8. 测试

- 使用 mock LLM 客户端测试流水线各步骤(画像/合规/垃圾识别/邮件生成)及解析校验
- 测试用户权限逻辑与关键路由
- 不做真实接口调用测试

## 9. 非目标(本期不做)

- 不真实发送邮件(仅草稿)
- 不接入 IM / CRM 自动同步
- 不做多用户注册页面(用户由初始化脚本或种子数据创建)
