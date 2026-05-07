# 项目：Video Summary（视频摘要工具）

## 技术栈
- Python 3.11+，FastAPI，SQLAlchemy async，aiosqlite
- DeepSeek Chat API（AI 摘要）+ OpenAI Whisper API（语音转写）
- 前端：Jinja2 + HTMX + Tailwind CSS CDN
- 外部工具：yt-dlp（视频下载）、ffmpeg（音频提取）

## 目录结构
```
app/
  main.py          -- FastAPI 入口，注册路由
  config.py         -- 环境变量配置（.env 加载）
  templates.py      -- Jinja2 模板引擎实例
  db/               -- 数据库层
    database.py     -- 异步引擎 + session + get_db 依赖
    models.py       -- VideoTask ORM 模型
  download/         -- 视频下载模块
    downloader.py   -- yt-dlp 封装
    router.py       -- /api/v1/tasks REST API
    schema.py       -- Pydantic 请求/响应模型
  audio/            -- 音频处理模块
    extractor.py    -- ffmpeg 音频提取 + 切片
    transcriber.py  -- Whisper API 语音转写
  summary/          -- AI 摘要模块
    summarizer.py   -- DeepSeek 长文本分段摘要
    prompt.py       -- 中文 System Prompt 模板
  tasks/            -- 任务编排
    pipeline.py     -- 完整流水线：下载→提取→转写→摘要
  web/              -- Web 前端
    router.py       -- 页面路由（首页 + 任务详情 + HTMX 局部刷新）
    templates/      -- Jinja2 HTML 模板
tests/              -- pytest 异步测试
docs/               -- 项目文档
```

## 架构规则
- `main.py` 只注册路由，不直接操作数据库或调用外部 API
- 视图层（`web/router.py`、`download/router.py`）不直接调用 yt-dlp / ffmpeg / OpenAI API，必须通过 service 类
- 数据库模型只在 `db/models.py` 中定义，其他地方只引用 `VideoTask`
- 所有新 service 类必须在对应 `__init__.py` 中显式导出
- 异步函数统一使用 `async def` + `await`，禁止同步阻塞调用
- 配置项统一在 `config.py` 通过环境变量读取，禁止硬编码

## 外部依赖
- yt-dlp>=2024.0 — 视频元数据提取和下载
- ffmpeg（系统级）— 音频提取和切片
- OpenAI Whisper API — 语音转写（需要 OPENAI_API_KEY）
- DeepSeek Chat API — AI 摘要生成（需要 DEEPSEEK_API_KEY）
- SQLite（aiosqlite）— 任务持久化

## 任务拆分原则
- 每个功能点单独一个分支，分支名格式：`feature/<功能描述>`
- 功能设计文档放在 `docs/plans/` 目录下
- 完成后通过 PR 合并到 master，合并后删除分支

## 相关文档
- 架构设计：见 `docs/architecture.md`
- 运行指南：见 `docs/getting-started.md`
- 功能计划：见 `docs/plans/`
