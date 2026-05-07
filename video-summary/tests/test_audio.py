import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

import pytest

from app.audio.extractor import AudioExtractor
from app.audio.transcriber import WhisperTranscriber


@pytest.fixture
def mock_ffmpeg():
    proc = AsyncMock()
    proc.communicate.return_value = (b"", b"")
    proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock:
        yield mock


@pytest.fixture
def mock_openai():
    resp = MagicMock()
    resp.strip.return_value = "测试转写文本"
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(return_value=resp)
    with patch("app.audio.transcriber.AsyncOpenAI", return_value=client) as mock:
        yield mock


class TestAudioExtractor:
    @pytest.mark.asyncio
    async def test_extract_returns_audio_path(self, mock_ffmpeg, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_text("fake video")
        fake_audio = tmp_path / "test.mp3"
        fake_audio.write_text("fake audio")

        extractor = AudioExtractor()
        with patch.object(extractor, "extract", wraps=extractor.extract):
            with patch("pathlib.Path.exists", return_value=True):
                result = await extractor.extract(video, tmp_path)
                assert result.suffix == ".mp3"

    @pytest.mark.asyncio
    async def test_split_returns_chunks(self, mock_ffmpeg, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_text("audio data")
        chunk1 = tmp_path / "test_chunk_001.mp3"
        chunk1.write_text("chunk1")

        extractor = AudioExtractor()
        with patch.object(extractor, "split", wraps=extractor.split):
            chunks = await extractor.split(audio, chunk_seconds=1)
            assert len(chunks) > 0


class TestWhisperTranscriber:
    @pytest.mark.asyncio
    async def test_transcribe_small_file(self, mock_openai, tmp_path):
        audio = tmp_path / "small.mp3"
        audio.write_text("small audio data")

        transcriber = WhisperTranscriber(language="zh")
        result = await transcriber.transcribe(audio)
        assert result == "测试转写文本"

    @pytest.mark.asyncio
    async def test_transcribe_large_file_chunks(self, mock_openai, tmp_path):
        audio = tmp_path / "large.mp3"
        audio.write_bytes(b"x" * (26 * 1024 * 1024))

        chunk = tmp_path / "large_chunk_001.mp3"
        chunk.write_bytes(b"small chunk")

        transcriber = WhisperTranscriber(language="zh")
        with patch.object(transcriber, "_transcribe_chunked", wraps=transcriber._transcribe_chunked):
            with patch("app.audio.extractor.AudioExtractor.split", return_value=[chunk]):
                result = await transcriber.transcribe(audio)
                assert result == "测试转写文本"


class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline_completes(self, client):
        async def fake_run(self, task_id):
            from app.db.database import async_session
            from app.db.models import VideoTask
            from sqlalchemy import select
            async with async_session() as db:
                result = await db.execute(select(VideoTask).where(VideoTask.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.title = "Test"
                    task.duration = 120
                    task.status = "completed"
                    task.transcript = "完整转写结果"
                    task.summary = "## 摘要"
                    await db.commit()

        with patch("app.tasks.pipeline.SummaryPipeline.run", fake_run):
            resp = await client.post("/api/v1/tasks", json={
                "url": "https://youtube.com/watch?v=test"
            })
            assert resp.status_code == 201

            await asyncio.sleep(0.2)

            task_id = resp.json()["id"]
            get_resp = await client.get(f"/api/v1/tasks/{task_id}")
            data = get_resp.json()
            assert data["status"] == "completed"
            assert data["summary"] == "## 摘要"
