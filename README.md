# 销售 Agent — EduTech 课程销售合规与多语言跟进 Agent 系统

本地运行的 Web 应用,面向销售部门。销售员上传/粘贴聊天记录,系统自动完成客户画像分析、培训行业合规风险审计、合规邮件草稿生成(语言自适应 + 垃圾邮件过滤),主管可查看历史与报表。

设计文档:`docs/superpowers/specs/2026-08-10-sales-agent-design.md`

## 功能

- **客户画像分析**:职业背景、核心痛点、预算敏感度(围绕 ¥2,999)、成交意向度、语言文化偏好
- **合规风险审计**:针对培训行业红线(保证就业/保底薪资/包学会/拒绝退款/虚假稀缺)
- **合规邮件生成**:根据客户语言偏好生成中文/英文/中英双语邮件,自动修正聊天中的违规承诺
- **垃圾邮件过滤**:无效线索识别 + 生成邮件反垃圾风险检查
- **历史与报表**:主管查看各销售员分析数与违规率
- **一键加载示例**:分析页内置 3 组 demo 对话

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置密钥:复制 .env.example 为 .env 并填入 DEEPSEEK_API_KEY
# 3. 启动
python run.py
```

访问 `http://127.0.0.1:8000`。

默认账号(首次启动自动创建):

| 角色 | 用户名 | 密码 |
|---|---|---|
| 销售员 | rep | 123456 |
| 主管 | manager | 123456 |

> 仅生成邮件草稿,不真实发送邮件。

## 运行测试

```bash
pytest
```

## 目录结构

- `core/` — Agent 核心逻辑(不依赖 Web,可独立测试)
  - `llm_client.py` — DeepSeek 封装(密钥从环境变量读取,结构化输出校验重试)
  - `schemas.py` — Pydantic 数据结构
  - `pipeline.py` — 流水线编排
  - `analyzers/` — `profiler.py`、`compliance.py`、`spam.py`、`email_writer.py`
  - `mock_data.py` — 3 组 demo 场景
- `app/` — Web 层(FastAPI 路由、Jinja2 模板、auth、db)
- `tests/` — 单元测试(mock LLM)
