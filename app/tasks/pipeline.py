from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import DOWNLOADS_DIR
from app.db.database import async_session
from app.db.models import VideoTask
from app.download.downloader import VideoDownloader
from app.audio.extractor import AudioExtractor
from app.audio.transcriber import WhisperTranscriber
from app.summary.summarizer import VideoSummarizer


class SummaryPipeline:
    def __init__(self):
        self.downloader = VideoDownloader()
        self.extractor = AudioExtractor()
        self.transcriber = WhisperTranscriber(language="zh")
        self.summarizer = VideoSummarizer()

    async def run(self, task_id: str) -> None:
        async with async_session() as db:
            result = await db.execute(select(VideoTask).where(VideoTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

            try:
                await self._do_download(task, db)
                await self._do_extract(task, db)
                await self._do_transcribe(task, db)
                await self._do_summarize(task, db)
                task.status = "completed"
                await db.commit()
            except Exception as e:
                task.status = "failed"
                task.error_message = str(e) or type(e).__name__
                await db.commit()

    async def _do_download(self, task: VideoTask, db: AsyncSession) -> None:
        info = self.downloader.get_info(task.url)
        task.title = info.title
        task.duration = info.duration
        task.thumbnail = info.thumbnail
        task.status = "downloading"
        await db.commit()

        video_path = await self.downloader.download(task.url, task.id)
        task.video_path = str(video_path)
        task.status = "downloaded"
        await db.commit()

    async def _do_extract(self, task: VideoTask, db: AsyncSession) -> None:
        if not task.video_path:
            raise RuntimeError("No video to extract audio from")

        task.status = "extracting"
        await db.commit()

        video_path = Path(task.video_path)
        audio_path = await self.extractor.extract(video_path, DOWNLOADS_DIR)
        task.audio_path = str(audio_path)
        task.status = "extracted"
        await db.commit()

        video_path.unlink(missing_ok=True)
        task.video_path = None
        await db.commit()

    async def _do_transcribe(self, task: VideoTask, db: AsyncSession) -> None:
        if not task.audio_path:
            raise RuntimeError("No audio to transcribe")

        task.status = "transcribing"
        await db.commit()

        audio_path = Path(task.audio_path)
        transcript = await self.transcriber.transcribe(audio_path)
        task.transcript = transcript
        task.status = "transcribed"
        await db.commit()

        audio_path.unlink(missing_ok=True)
        task.audio_path = None
        await db.commit()

    async def _do_summarize(self, task: VideoTask, db: AsyncSession) -> None:
        if not task.transcript:
            raise RuntimeError("No transcript to summarize")

        task.status = "summarizing"
        await db.commit()

        summary = await self.summarizer.summarize(task.transcript, task.title or "")
        task.summary = summary
        await db.commit()
