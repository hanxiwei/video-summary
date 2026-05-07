import asyncio
from pathlib import Path

from openai import AsyncOpenAI

from app.config import OPENAI_API_KEY

WHISPER_FILE_LIMIT = 25 * 1024 * 1024  # 25MB


class WhisperTranscriber:
    def __init__(self, language: str = "zh"):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.language = language

    async def transcribe(self, audio_path: Path) -> str:
        if audio_path.stat().st_size > WHISPER_FILE_LIMIT:
            return await self._transcribe_chunked(audio_path)

        with open(audio_path, "rb") as f:
            resp = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=self.language,
                response_format="text",
            )
        return resp.strip()

    async def _transcribe_chunked(self, audio_path: Path) -> str:
        from app.audio.extractor import AudioExtractor

        extractor = AudioExtractor()
        chunks = await extractor.split(audio_path)
        texts: list[str] = []

        for i, chunk in enumerate(chunks):
            with open(chunk, "rb") as f:
                resp = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=self.language,
                    response_format="text",
                )
            texts.append(resp.strip())
            chunk.unlink(missing_ok=True)

        return "\n".join(texts)
