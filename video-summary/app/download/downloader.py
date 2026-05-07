import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

import yt_dlp

from app.config import DOWNLOADS_DIR


@dataclass
class VideoInfo:
    title: str
    duration: int
    thumbnail: str
    url: str


class VideoDownloader:
    def __init__(self, output_dir: Path = DOWNLOADS_DIR):
        self.output_dir = output_dir

    def get_info(self, url: str) -> VideoInfo:
        opts = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return VideoInfo(
                title=info.get("title", ""),
                duration=info.get("duration", 0) or 0,
                thumbnail=info.get("thumbnail", ""),
                url=url,
            )

    async def download(
        self, url: str, task_id: str, progress_callback: Callable[[dict], None] | None = None
    ) -> Path:
        hooks = [progress_callback] if progress_callback else []

        opts = {
            "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
            "outtmpl": str(self.output_dir / f"{task_id}.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": hooks,
        }

        loop = asyncio.get_running_loop()
        filename: str = ""

        def run() -> None:
            nonlocal filename
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

        await loop.run_in_executor(None, run)
        video_path = Path(filename)
        if not video_path.exists():
            candidates = list(self.output_dir.glob(f"{task_id}.*"))
            if candidates:
                video_path = candidates[0]
        return video_path
