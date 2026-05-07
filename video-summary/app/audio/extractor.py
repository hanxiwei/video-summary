import asyncio
from pathlib import Path


class AudioExtractor:
    def __init__(self, sample_rate: int = 16000, bitrate: str = "64k"):
        self.sample_rate = sample_rate
        self.bitrate = bitrate

    async def extract(self, video_path: Path, output_dir: Path) -> Path:
        audio_path = output_dir / f"{video_path.stem}.mp3"

        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "libmp3lame",
            "-ar", str(self.sample_rate),
            "-b:a", self.bitrate,
            str(audio_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=0x08000000 if hasattr(asyncio.subprocess, "CREATE_NO_WINDOW") else 0,
        )
        await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed with code {proc.returncode}")

        if not audio_path.exists():
            raise RuntimeError(f"Audio extraction failed: {audio_path} not created")

        return audio_path

    async def split(self, audio_path: Path, chunk_seconds: int = 600) -> list[Path]:
        out_pattern = str(audio_path.parent / f"{audio_path.stem}_chunk_%03d{audio_path.suffix}")

        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-f", "segment", "-segment_time", str(chunk_seconds),
            "-c", "copy", out_pattern,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=0x08000000 if hasattr(asyncio.subprocess, "CREATE_NO_WINDOW") else 0,
        )
        await proc.communicate()

        chunks = sorted(audio_path.parent.glob(f"{audio_path.stem}_chunk_*{audio_path.suffix}"))
        return chunks or [audio_path]
