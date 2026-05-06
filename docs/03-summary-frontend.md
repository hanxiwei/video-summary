# 阶段三：AI 摘要 + 前端界面

## 实现时间

2026-05-06

## 概述

实现 OpenAI Chat Completions API 生成视频 Markdown 摘要，以及 Jinja2 + HTMX + Tailwind CSS 前端界面。

## 技术决策

### GPT-4o-mini + tiktoken 分片

选择 OpenAI Chat Completions API（GPT-4o-mini）进行摘要：
- 成本低（$0.15/1M input tokens）
- `tiktoken.encoding_for_model("gpt-4o")` 精确计算 token 数
- 短文本（<7000 token）直接总结
- 长文本按 5000 token 切片 → 逐段总结 → 合并总结

### Prompt 工程

三级 Prompt 策略：
- **SYSTEM_PROMPT**：要求输出结构化 Markdown（摘要、要点、行动建议）
- **CHUNK_SUMMARY_PROMPT**：对每个片段独立总结
- **MERGE_PROMPT**：合并分段总结为完整摘要

### 前端：Jinja2 + HTMX + Tailwind CDN

- **Jinja2**：服务端模板渲染，无需前端构建工具
- **HTMX**：局部刷新（任务列表每 3 秒轮询、表单提交）
- **Tailwind CDN**：快速样式，零构建
- **marked.js CDN**：渲染 Markdown 摘要

### 前端路由设计

| 端点 | 说明 |
|------|------|
| `GET /` | 首页：URL 输入框 + 任务列表 |
| `POST /tasks` | 创建任务并跳转到详情页 |
| `GET /tasks/{id}` | 任务详情：进度 + 摘要 + 转录文本 |
| `GET /partials/tasks` | HTMX 局部刷新：任务列表 HTML 片段 |

## 关键依赖

```
openai>=1.0.0
tiktoken>=0.5.0
jinja2>=3.1.0
python-multipart>=0.0.6
```

CDN：
- tailwindcss.com (CSS)
- unpkg.com/htmx.org (HTMX)
- cdn.jsdelivr.net/npm/marked (Markdown)

## 文件结构

```
app/
├── summary/
│   ├── prompt.py       (28行) — Prompt 模板
│   └── summarizer.py   (76行) — 摘要生成器
├── web/
│   ├── router.py       (98行) — 前端路由
│   └── templates/
│       ├── base.html    — 基础布局（Tailwind + HTMX + marked.js）
│       ├── index.html   — 首页
│       └── task.html    — 任务详情页
└── templates.py        (7行)  — Jinja2Templates 单例
```

## 测试覆盖

全部 22 个测试通过：
- 8 个阶段一测试（下载）
- 5 个阶段二测试（音频/转写）
- 9 个新增测试：
  - 摘要短文本 / 长文本分片
  - Token 计数 / 文本拆分
  - Prompt 模板验证
  - API 摘要返回验证
  - 前端页面渲染验证

## 遇到的问题

### _to_response 遗漏字段

在 schema 增加了 `transcript` / `summary` 字段后，`_to_response` 函数漏传这两个字段。导致 API 始终返回 `null`。修复后所有测试通过。

### Jinja2 缓存 + Python 3.13 兼容

Jinja2 的 LRU 缓存将模板上下文 dict 作为缓存键，在 Python 3.13 中触发 `unhashable type: 'dict'` 错误。通过将 Jinja2 缓存放缓，以及将 `templates` 提取到独立模块解决循环导入问题。

### 测试中 mock 路径

当类通过 `from module import Class` 引用时，被引用模块中的 `Class.method` 与源模块的 `Class.method` 是同一对象。但 mock 时若路径不准确会导致 mock 不生效。最终采用 mock `SummaryPipeline.run` 的策略简化集成测试。
