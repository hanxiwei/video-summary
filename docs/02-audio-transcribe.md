# 阶段二：音频提取 + Whisper 转写

## 实现时间

2026-05-06

## 概述

在下载完成后自动提取音频（ffmpeg），通过 OpenAI Whisper API 转写为中文字幕文本，处理完成后删除视频和音频文件。

## 技术决策

### ffmpeg subprocess 而非 Python 绑定

选择 `asyncio.create_subprocess_exec` 调用 ffmpeg CLI：
- 零额外依赖，Windows/Linux 通用
- 参数灵活，bitrate/sample_rate 可配置
- 分片时直接复用 ffmpeg segment 功能

### Whisper API 而非本地模型

选择 OpenAI Whisper API：
- 无需 GPU / 内存开销
- 中文识别精度高，自动断句
- 25MB 文件限制，超过时自动分片

### 文件清理策略

- 提取音频后立即删除视频文件
- 转写完成后立即删除音频文件
- 仅保留转录文本在数据库中

### 分片处理

- 文件 <=25MB：直接发送 Whisper API
- 文件 >25MB：ffmpeg segment 按 10 分钟切片，逐一转写后拼接

## 数据流

```
视频文件 (.mp4)
  → ffmpeg 提取音频 (.mp3)
  → 删除视频文件
  → Whisper API 转写
  → 删除音频文件
  → 文本存入 DB
```

## 关键依赖

```
openai>=1.0.0  (AsyncOpenAI + audio.transcriptions.create)
ffmpeg (系统工具)
```

## 测试覆盖

5 个测试全部通过：
- `test_extract_returns_audio_path` — ffmpeg 提取音频
- `test_split_returns_chunks` — 大文件分片
- `test_transcribe_small_file` — 小文件转写
- `test_transcribe_large_file_chunks` — 大文件分片转写
- `test_full_pipeline_updates_status` — 完整流程集成测试

所有外部依赖（ffmpeg, OpenAI）均 mock，不产生真实 API 调用。

## 遇到的问题

### 分片文件清理
转写完成后需要清理分片文件（`chunk.unlink()`），避免残留。分片是临时产物，不做保留。

### CREATE_NO_WINDOW on Windows
ffmpeg subprocess 在 Windows 上会弹出命令行窗口。通过 `creationflags` 参数抑制（仅在可用时设置）。
