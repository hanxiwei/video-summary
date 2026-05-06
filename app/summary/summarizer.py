import tiktoken
from openai import AsyncOpenAI

from app.config import OPENAI_API_KEY
from app.summary.prompt import SYSTEM_PROMPT, CHUNK_SUMMARY_PROMPT, MERGE_PROMPT

MAX_TOKENS = 7000
CHUNK_TOKENS = 5000


class VideoSummarizer:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        self.encoder = tiktoken.encoding_for_model("gpt-4o")

    def _count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    async def summarize(self, transcript: str, video_title: str) -> str:
        if self._count_tokens(transcript) <= MAX_TOKENS:
            return await self._summarize_text(transcript, video_title)
        return await self._summarize_chunked(transcript, video_title)

    async def _summarize_text(self, text: str, title: str) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"视频标题：{title}\n\n转录文本：\n{text}"},
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""

    async def _summarize_chunked(self, transcript: str, title: str) -> str:
        chunks = self._split_text(transcript)
        summaries: list[str] = []

        for i, chunk in enumerate(chunks):
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CHUNK_SUMMARY_PROMPT},
                    {"role": "user", "content": f"视频标题：{title}\n片段 {i + 1}：\n{chunk}"},
                ],
                temperature=0.3,
            )
            summaries.append(resp.choices[0].message.content or "")

        combined = "\n\n".join(f"片段 {i + 1}：\n{s}" for i, s in enumerate(summaries))
        return await self._merge_summaries(combined, title)

    async def _merge_summaries(self, chunk_summaries: str, title: str) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": MERGE_PROMPT},
                {"role": "user", "content": f"视频标题：{title}\n\n{chunk_summaries}"},
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""

    def _split_text(self, text: str) -> list[str]:
        tokens = self.encoder.encode(text)
        chunks: list[str] = []
        i = 0
        while i < len(tokens):
            chunk_tokens = tokens[i : i + CHUNK_TOKENS]
            chunks.append(self.encoder.decode(chunk_tokens))
            i += CHUNK_TOKENS
        return chunks
