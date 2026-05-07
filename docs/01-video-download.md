# 阶段一：视频下载

## 实现时间

2026-05-06

## 概述

实现了视频下载功能，包括后端 API、数据库模型、yt-dlp 封装和自动化测试。

## 技术决策

### yt-dlp 使用 Python API 而非 subprocess

选择 `import yt_dlp` 的 `YoutubeDL` 类而非 CLI subprocess 调用：
- 进度 hooks 提供结构化进度回调，无需解析 stdout
- `extract_info(url, download=False)` 直接返回元信息 dict
- 错误处理更精确，不依赖 exit code 和 stderr

### SQLite + SQLAlchemy 2.0 async

单表 `video_tasks` 驱动状态机，status 字段串联各阶段：
```
pending → downloading → downloaded → ... → completed/failed
```

### FastAPI BackgroundTasks 而非 Celery

任务量小，无需外部消息队列。直接在单进程中用 asyncio 线程池跑 yt-dlp 同步调用（`run_in_executor`）。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/tasks | 创建下载任务 |
| GET  | /api/v1/tasks | 任务列表 |
| GET  | /api/v1/tasks/{id} | 任务详情 |

## 关键依赖

```
yt-dlp>=2024.0
fastapi>=0.100.0
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
```

## 测试覆盖

6 个测试全部通过：
- `test_get_info_returns_video_info` — yt-dlp info 提取
- `test_download_returns_path` — 下载路径返回
- `test_create_task` — 创建任务 API
- `test_get_task` — 查询任务 API
- `test_get_task_404` — 任务不存在
- `test_list_tasks` — 任务列表

Mock yt-dlp 避免真实网络请求。

## 遇到的问题

### in-memory SQLite 隔离问题
`sqlite+aiosqlite://` 每次 `create_engine` 创建独立的内存数据库。测试中需要确保 lifespan 和 test session 使用同一个 engine 实例。解决：conftest 中通过环境变量统一 URL，共用 `app.db.database.engine`。

### datetime.utcnow 弃用警告
SQLAlchemy `Column(default=utcnow)` 触发 Python 3.12+ 的 deprecation warning。改用 `lambda: datetime.now(timezone.utc)`。
