# 阶段四：Harness 工作环境搭建（里程碑 1）

## 实现时间

2026-05-07

## 概述

按照 Harness 工程方法论，为项目搭建结构化开发环境：编写项目上下文文件（AGENTS.md）、架构护栏校验脚本（lint-architecture.py）、建立 Git 规范。

## 实现内容

### 1. AGENTS.md — 项目上下文文件

编写了 `AGENTS.md`，作为 AI 和开发者协作的"宪章"，包含：

- **技术栈**：Python 3.11+、FastAPI、SQLAlchemy async、aiosqlite、DeepSeek/OpenAI API
- **目录结构说明**：每个模块的职责和边界
- **架构规则**：6 条强制规则，防止架构腐化
  - main.py 只注册路由，不直接操作数据库或调用外部 API
  - 视图层不直接调用 yt-dlp / ffmpeg / OpenAI API
  - ORM 模型只在 db/models.py 中定义
  - 新 service 类必须在 __init__.py 中导出
  - 异步函数统一使用 async/await
  - 配置统一走 config.py + 环境变量
- **任务拆分原则**：功能分支命名、PR 流程、文档规范

### 2. lint-architecture.py — 架构护栏脚本

编写了 `scripts/lint-architecture.py`，自动化检查 4 条架构规则：

| 规则 | 说明 |
|------|------|
| 规则 1 | main.py 不得直接导入 service 层模块 |
| 规则 2 | router.py 不得包含 ORM 模型定义或直接调用外部 CLI |
| 规则 3 | 每个 __init__.py 必须导出公开类 |
| 规则 4 | ORM 模型只能在 db/models.py 中定义 |

采用 Python AST 解析，无需额外依赖。当前 21 个 Python 文件全部通过。

### 3. Git 存档点规范

- 每个里程碑完成后打 tag（如 `v0.4-harness`）
- 分支命名：`feature/<功能描述>`
- 通过 PR 合并到 master

## 文件变更

| 文件 | 状态 | 说明 |
|------|------|------|
| AGENTS.md | 新增 | 项目上下文文件 |
| scripts/lint-architecture.py | 新增 | 架构护栏校验脚本 |

## 验证

- `python scripts/lint-architecture.py` — 21 个文件全部通过
- `pytest tests/` — 22 个测试全部通过
