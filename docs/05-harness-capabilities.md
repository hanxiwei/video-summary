# 阶段五：Harness 执行能力增强（里程碑 2）

## 实现时间

2026-05-07

## 概述

按照 Harness 工程方法论，为项目添加 MCP 配置、Agent Skills 和 AI 自主修复测试，提升 AI 辅助开发的执行能力。

## 实现内容

### 1. MCP 配置（.claude/settings.json）

配置了两个 MCP Server：

| MCP Server | 用途 |
|------------|------|
| firecrawl | 抓取 yt-dlp / OpenAI / DeepSeek 最新文档 |
| context7 | 自动获取 FastAPI / SQLAlchemy / yt-dlp 等依赖库最新 API |

同时配置了项目级规则：
- 代码提交前必须通过 `scripts/lint-architecture.py` 检查
- 新功能必须先在 `docs/plans/` 下写方案文档
- 每个里程碑完成后打 git tag

### 2. Agent Skills

#### transcript-quality Skill（.claude/skills/transcript-quality.md）

定义了转写质量对比 Skill：
- **触发条件**：修改 Whisper 参数时自动触发
- **执行流程**：准备测试音频 → 参数矩阵测试（language/temperature/format）→ 四维度评分（CER/标点/数字处理/噪音鲁棒性）→ 生成推荐报告
- **实现提示**：复用 `WhisperTranscriber`，评分脚本写入 `scripts/transcript-bench.py`

### 3. AI 自主修复测试（tests/test_ai_recovery.py）

新增 6 个错误恢复测试用例，覆盖全部 pipeline 阶段：

| 测试用例 | 验证场景 |
|---------|---------|
| test_download_failure_records_error | yt-dlp 下载失败 → status=failed + 错误信息 |
| test_extract_failure_keeps_video | ffmpeg 提取失败 → 视频文件保留 |
| test_transcribe_failure_records_error | Whisper API 转写失败 → 正确记录 |
| test_summarize_failure_records_error | DeepSeek API 摘要失败 → 正确记录 |
| test_task_not_found_is_silent | 不存在的 task → 静默返回 |
| test_empty_error_message_not_produced | 空消息异常 → 至少记录异常类型名 |

### 4. 配套修复

- **pipeline.py**：修复空消息异常导致 `error_message` 为空的问题（`str(e) or type(e).__name__`）
- **extractor.py**：`FFMPEG_PATH` 从模块级变量改为方法内延迟读取，解决 `.env` 加载时序问题
- **downloader.py**：添加 `nocheckcertificate: True` 修复 B 站 SSL 错误
- **.env / .env.example**：新增 `FFMPEG_PATH` 配置项

## 文件变更

| 文件 | 状态 | 说明 |
|------|------|------|
| .claude/settings.json | 新增 | MCP 配置 + 项目规则 |
| .claude/skills/transcript-quality.md | 新增 | 转写质量对比 Skill |
| tests/test_ai_recovery.py | 新增 | AI 自主修复测试（6 个用例） |
| app/tasks/pipeline.py | 修改 | 空消息异常处理 |
| app/audio/extractor.py | 修改 | FFMPEG_PATH 延迟读取 |
| app/download/downloader.py | 修改 | B 站 SSL 修复 |
| .env / .env.example | 修改 | 新增 FFMPEG_PATH |

## 验证

- `pytest tests/` — 28 个测试全部通过（+6 个新增）
- `python scripts/lint-architecture.py` — 21 个文件架构检查通过
