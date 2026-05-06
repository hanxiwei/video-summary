from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.db.models import VideoTask
from app.download.downloader import VideoDownloader


class SummaryPipeline:
    def __init__(self):
        self.downloader = VideoDownloader()

    async def run_download(self, task_id: str) -> None:
        async with async_session() as db:
            result = await db.execute(select(VideoTask).where(VideoTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

            try:
                info = self.downloader.get_info(task.url)
                task.title = info.title
                task.duration = info.duration
                task.thumbnail = info.thumbnail

                task.status = "downloading"
                await db.commit()

                def on_progress(d: dict) -> None:
                    pass  # Phase 2 will store progress

                video_path: Path = await self.downloader.download(task.url, task_id, on_progress)
                task.video_path = str(video_path)
                task.status = "downloaded"
                await db.commit()

            except Exception as e:
                task.status = "failed"
                task.error_message = str(e)
                await db.commit()
