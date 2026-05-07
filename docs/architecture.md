# 架构设计文档

## 整体架构

```
用户浏览器 (HTMX + Tailwind)
       |
       v
  FastAPI 应用
       |
  +----+----+----+----+
  |    |    |    |    |
 Web  API  Task DB
 路由  路由  编排  层
  |    |    |    |
  +----+----+----+----+
       |
  外部服务
  (yt-dlp / ffmpeg / Whisper / DeepSeek)
```

## 分层设计

### 路由层（app/download/router.py, app/web/router.py）

- 处理 HTTP 请求/响应
- 参数验证（Pydantic schemas）
- 不包含业务逻辑，只做编排和响应

### 服务层（app/download/downloader.py, app/audio/*, app/summary/*）

- 封装外部工具和 API 调用
- 每个类单一职责：
  - `VideoDownloader` — yt-dlp 封装
  - `AudioExtractor` — ffmpeg 音频提取
  - `WhisperTranscriber` — Whisper API 转写
  - `VideoSummarizer` — DeepSeek API 摘要

### 编排层（app/tasks/pipeline.py）

- `SummaryPipeline` 串联完整流水线
- 管理任务状态转换
- 处理错误和清理中间文件

### 数据层（app/db/）

- `VideoTask` 单一 ORM 模型
- 异步 SQLAlchemy + aiosqlite
- 状态机驱动任务生命周期

## 数据流

```
URL 输入 → POST /api/v1/tasks (status=pending)
  → SummaryPipeline.run(task_id)
    → VideoDownloader.download()     (status: downloading → downloaded)
    → AudioExtractor.extract()      (status: extracting → extracted)
    → WhisperTranscriber.transcribe() (status: transcribing → transcribed)
    → VideoSummarizer.summarize()     (status: summarizing → completed)
  → 前端 HTMX 轮询 /partials/tasks 获取实时状态
```

## 状态机

```
pending → downloading → downloaded → extracting → extracted
  → transcribing → transcribed → summarizing → completed

任意阶段出错 → failed
```

## 技术决策

1. **FastAPI BackgroundTasks 而非 Celery**：MVP 阶段任务量小，单进程足够
2. **yt-dlp Python API 而非 CLI**：更精确的错误处理和进度回调
3. **SQLite + aiosqlite**：零配置，适合单机部署
4. **DeepSeek 用于摘要 + OpenAI 用于转写**：DeepSeek 中文摘要性价比高，Whisper 是中文转写的事实标准
5. **HTMX + Tailwind CDN**：无构建步骤，极简前端架构
