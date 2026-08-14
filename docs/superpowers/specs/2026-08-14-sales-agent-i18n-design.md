# 设计:销售 Agent 国际化 (i18n)

**日期**:2026-08-14
**状态**:已评审
**范围**:为 Web 界面与后端 Agent 增加多语言国际化。

## 1. 目标

- 支持三种语言:**简体中文 (zh-CN)、繁体中文 (zh-HK)、英文 (en-US)**。
- Web 界面右上角提供语言切换下拉菜单;切换后所有静态文本(标题、按钮、表单标签、质检报告表头等)即时切换。
- 后端 Agent 的系统提示词 / 工具描述本地化;Agent 的分析结果(画像、合规摘要、邮件正文)仍按聊天记录语言生成,维持「多语言跟进」现状。

## 2. 关键决策

| 决策点 | 选择 | 说明 |
|---|---|---|
| 实现机制 | 内置翻译字典 + Jinja filter | 零新依赖,最轻量易测 |
| 语言持久化 | Cookie | 写 `lang` cookie,刷新/再访问保持 |
| 默认语言 | zh-CN | 无 cookie / 非法值时回退 zh-CN |
| 后端 Agent 范围 | 仅提示词本地化 | 结果内容仍跟随聊天语言 |
| 结果页单元格 | 不翻译 LLM 生成内容 | 仅表头等静态文本翻译 |
| 数据库枚举值 | 不翻译,保留原样 | 避免破坏存储值与业务逻辑 |
| 展示型状态值 | 模板层映射翻译 | 状态徽章、图表标签等 UI 展示文本 |

## 3. 架构

### 3.1 新增 `app/i18n.py`

单一时钟源,核心组件:

- `SUPPORTED = {"zh-CN": "简体中文", "zh-HK": "繁體中文", "en-US": "English"}`
- `DEFAULT_LANG = "zh-CN"`
- 嵌套字典 `TRANSLATIONS`,每语言一份词条,key 统一英文标识符(如 `nav.analysis`、`analysis.title`、`result.profile.occupation`)。zh-CN 值即现有界面文案;zh-HK 为繁体;en-US 为英文。
- 函数:
  - `get_lang(request) -> str`:从 `request.cookies.get("lang")` 读取,非法/缺失回退 `DEFAULT_LANG`。
  - `set_lang_cookie(response, lang)`:写 `Set-Cookie: lang=<lang>`。
  - `t(key, lang) -> str`:查表,缺失回退 zh-CN,再回退返回 key 本身。

### 3.2 修改 `app/templating.py`

- 注册为 **context-aware Jinja filter** `t`,渲染时自动读取模板上下文里的 `lang`(由 `template_response` 注入),因此模板内仅需写 `{{ t('key') }}` 即可:

```python
from jinja2 import pass_context

@pass_context
def t(context, key, lang=None):
    lang = lang or context.get("lang", DEFAULT_LANG)
    return translate_key(key, lang)  # 即 app/i18n.t(key, lang)
templates.env.filters["t"] = t
```
- 用包装函数替换 `templates.TemplateResponse`,自动注入 `lang`(来自 `get_lang(request)`)到每个模板上下文,使所有现有路由调用点无需改动。

```python
original = templates.TemplateResponse
def template_response(request, name, context=None, **kw):
    context = dict(context or {})
    context.setdefault("lang", get_lang(request))
    context.setdefault("SUPPORTED", SUPPORTED)
    return original(request, name, context, **kw)
```

`templates.TemplateResponse = template_response`

### 3.3 修改 `app/main.py`

- 中间件读取 cookie 写入 `request.state.lang`。
- 新增 `GET /set-language/{lang}`:校验 lang → `set_lang_cookie` → 重定向回 `Referer`(缺失则 `/`)。

### 3.4 模板(`base.html` + 6 个子模板)

- 用 `{{ t('key') }}` 替换硬编码中文。
- `<html lang="{{ lang }}">` 动态。
- `base.html` 右上角(nav)新增 Pico `dropdown`,登录与未登录均可见:

```html
<li>
  <details class="dropdown">
    <summary role="button" class="secondary">{{ t('lang.current') }}</summary>
    <ul>
      {% for code, label in SUPPORTED.items() %}
      <li><a href="/set-language/{{ code }}">{{ label }}</a></li>
      {% endfor %}
    </ul>
  </details>
</li>
```

### 3.5 后端 Agent(`core/agent.py` 与 `core/pipeline.py`)

- 新增 `get_system_prompt(lang)`:返回本地化 `SYSTEM_PROMPT` 与工具描述。
- `run_agent(llm, chat_text, lang=DEFAULT_LANG)`、`run_pipeline(llm, chat_text, lang=DEFAULT_LANG)` 接受可选 `lang`。
- `app/routes/analysis.py` 把 `request.state.lang` 传给 `run_pipeline`。

## 4. 数据流

1. 用户点右上角下拉 → 点击 `<a href="/set-language/{{ code }}">` 链接。
2. `GET /set-language/{lang}` 校验 → `set_lang_cookie` → 重定向回 `Referer`。
3. 后续请求中间件读 cookie → `request.state.lang` / `get_lang(request)`。
4. `template_response` 注入 `lang` → 模板 `{{ t('...') }}` 渲染对应语言。
5. Agent:路由把 `request.state.lang` 传给 `run_pipeline(...)` → `get_system_prompt(lang)`。

## 5. 数据渲染细节

- **结果页表头**:`result.html` 静态表头(职业背景/核心痛点/预算敏感度/成交意向度/语言偏好、违规类型/违规原句等)全部走 `t()`。**LLM 生成的单元格内容不翻译**。
- **状态徽章枚举**:`WARNING`/`PASSED`、`high`/`medium`/`low`、`invalid_lead` 等保留原样(数据库与逻辑值)。
- **展示型状态值**(UI 展示文本,模板层映射):`tasks.html` 的 `{{ t('status.' ~ t.status) }}`;`customers.html` 的 `stage`/`lead_status`;`drafts.html` 的 `d.status` 与「批准/拒绝」按钮;`reports.html` 图表 `label` 与指标名。

## 6. 错误处理

- 非法 lang cookie/URL → 回退 `DEFAULT_LANG`,不报错。
- 翻译 key 缺失 → 回退 zh-CN → 再回退返回 key 本身(便于发现漏翻,不中断页面)。
- `/set-language/{lang}` 无 referer → 重定向 `/`。

## 7. 测试

- `tests/test_i18n.py`:
  - 三语言翻译 key 集合一致(完整性)。
  - `t()` 缺失 key 回退逻辑。
  - `get_lang` cookie 解析与非法回退。
  - `/set-language/{lang}` 写入 cookie 并重定向(含无 referer 场景)。
  - `get_system_prompt(lang)` 返回对应语言,缺省 zh-CN。

## 8. 非范围

- 不翻译 LLM 生成的分析结果内容。
- 不翻译数据库枚举/状态值。
- 不做 Accept-Language 自动探测、不做按用户数据库配置语言。
- 不引入第三方 i18n 依赖。