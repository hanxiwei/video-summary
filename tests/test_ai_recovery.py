"""AI 自主修复测试 —— 验证 pipeline 在面对已知错误时的恢复能力。

测试场景：
1. 下载阶段失败：yt-dlp 不可达视频 → 应标记 failed + 记录错误
2. 音频提取失败：ffmpeg 不可用 → 应标记 failed + 记录错误
3. 转写 API 失败：Whisper API 返回错误 → 应标记 failed + 记录错误
4. 摘要 API 失败：DeepSeek API 返回错误 → 应标记 failed + 记录错误
5. 部分失败恢复：下载成功但提取失败 → 下载文件应保留，状态 failed
6. 异常类型覆盖：空消息异常 → error_message 不能为空
"""

import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.db.database import engine
from app.db.models import VideoTask
from app.tasks.pipeline import SummaryPipeline


def _make_session():
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


class TestAIRecovery:
    """验证 pipeline 在各类错误场景下的行为。"""

    @pytest.mark.asyncio
    async def test_download_failure_records_error(self, init_db):
        """下载阶段 yt-dlp 失败 → 状态 failed + 错误信息记录。"""
        async with _make_session() as db:
            task = VideoTask(id="err-001", url="https://example.com/broken", status="pending")
            db.add(task)
            await db.commit()

        pipeline = SummaryPipeline()

        with patch.object(pipeline.downloader, "get_info", side_effect=RuntimeError("yt-dlp: video unavailable")):
            await pipeline.run("err-001")

        async with _make_session() as db:
            result = await db.execute(select(VideoTask).where(VideoTask.id == "err-001"))
            task = result.scalar_one()
            assert task.status == "failed"
            assert "yt-dlp" in task.error_message

    @pytest.mark.asyncio
    async def test_extract_failure_keeps_video(self, init_db):
        """音频提取失败 → 状态 failed，视频文件路径保留。"""
        async with _make_session() as db:
            task = VideoTask(
                id="err-002", url="https://example.com/video",
                status="downloaded", video_path="downloads/err-002.mp4",
                title="Test", duration=60
            )
            db.add(task)
            await db.commit()

        pipeline = SummaryPipeline()

        async def fake_download(task, db):
            pass
        async def fake_extract(task, db):
            raise RuntimeError("ffmpeg: codec not supported")

        with patch.object(pipeline, "_do_download", fake_download):
            with patch.object(pipeline, "_do_extract", fake_extract):
                await pipeline.run("err-002")

        async with _make_session() as db:
            result = await db.execute(select(VideoTask).where(VideoTask.id == "err-002"))
            task = result.scalar_one()
            assert task.status == "failed"
            assert "ffmpeg" in task.error_message
            assert task.video_path is not None

    @pytest.mark.asyncio
    async def test_transcribe_failure_records_error(self, init_db):
        """Whisper API 转写失败 → 状态 failed + 错误信息。"""
        async with _make_session() as db:
            task = VideoTask(
                id="err-003", url="https://example.com/video",
                status="extracted", audio_path="downloads/err-003.mp3",
                title="Test", duration=60
            )
            db.add(task)
            await db.commit()

        pipeline = SummaryPipeline()

        async def fake_download(task, db):
            pass
        async def fake_extract(task, db):
            pass
        async def fake_transcribe(task, db):
            raise RuntimeError("OpenAI API: rate limit exceeded")

        with patch.object(pipeline, "_do_download", fake_download):
            with patch.object(pipeline, "_do_extract", fake_extract):
                with patch.object(pipeline, "_do_transcribe", fake_transcribe):
                    await pipeline.run("err-003")

        async with _make_session() as db:
            result = await db.execute(select(VideoTask).where(VideoTask.id == "err-003"))
            task = result.scalar_one()
            assert task.status == "failed"
            assert "rate limit" in task.error_message

    @pytest.mark.asyncio
    async def test_summarize_failure_records_error(self, init_db):
        """DeepSeek API 摘要失败 → 状态 failed + 错误信息。"""
        async with _make_session() as db:
            task = VideoTask(
                id="err-004", url="https://example.com/video",
                status="transcribed", transcript="测试转写文本",
                title="Test", duration=60
            )
            db.add(task)
            await db.commit()

        pipeline = SummaryPipeline()

        async def fake_download(task, db):
            pass
        async def fake_extract(task, db):
            pass
        async def fake_transcribe(task, db):
            pass
        async def fake_summarize(task, db):
            raise RuntimeError("DeepSeek API: authentication failed")

        with patch.object(pipeline, "_do_download", fake_download):
            with patch.object(pipeline, "_do_extract", fake_extract):
                with patch.object(pipeline, "_do_transcribe", fake_transcribe):
                    with patch.object(pipeline, "_do_summarize", fake_summarize):
                        await pipeline.run("err-004")

        async with _make_session() as db:
            result = await db.execute(select(VideoTask).where(VideoTask.id == "err-004"))
            task = result.scalar_one()
            assert task.status == "failed"
            assert "DeepSeek" in task.error_message

    @pytest.mark.asyncio
    async def test_task_not_found_is_silent(self, init_db):
        """不存在的 task_id → 静默返回，不抛异常。"""
        pipeline = SummaryPipeline()
        await pipeline.run("nonexistent-id")

    @pytest.mark.asyncio
    async def test_empty_error_message_not_produced(self, init_db):
        """任何阶段抛出异常时，error_message 不能为空字符串。"""
        async with _make_session() as db:
            task = VideoTask(id="err-005", url="https://example.com/video", status="pending")
            db.add(task)
            await db.commit()

        pipeline = SummaryPipeline()

        with patch.object(pipeline.downloader, "get_info", side_effect=Exception("")):
            await pipeline.run("err-005")

        async with _make_session() as db:
            result = await db.execute(select(VideoTask).where(VideoTask.id == "err-005"))
            task = result.scalar_one()
            assert task.status == "failed"
            assert task.error_message is not None
            assert len(task.error_message) > 0
