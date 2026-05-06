import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.summary.summarizer import VideoSummarizer
from app.summary.prompt import SYSTEM_PROMPT, CHUNK_SUMMARY_PROMPT, MERGE_PROMPT


@pytest.fixture
def mock_openai_client():
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = "## 视频摘要\n\n这是测试摘要内容。"
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=resp)
    with patch("app.summary.summarizer.AsyncOpenAI", return_value=client):
        yield client


class TestVideoSummarizer:
    @pytest.mark.asyncio
    async def test_summarize_short_text(self, mock_openai_client):
        summarizer = VideoSummarizer()
        result = await summarizer.summarize("短文本内容", "测试标题")
        assert "视频摘要" in result

    @pytest.mark.asyncio
    async def test_summarize_long_text_chunks(self, mock_openai_client):
        summarizer = VideoSummarizer()
        long_text = "测试内容。" * 3000
        result = await summarizer.summarize(long_text, "长视频")
        assert "视频摘要" in result

    def test_token_count(self):
        summarizer = VideoSummarizer()
        count = summarizer._count_tokens("Hello world")
        assert count > 0

    def test_split_text(self):
        summarizer = VideoSummarizer()
        text = "测试内容 " * 5000
        chunks = summarizer._split_text(text)
        assert len(chunks) >= 1


class TestPrompts:
    def test_system_prompt_exists(self):
        assert len(SYSTEM_PROMPT) > 0
        assert "Markdown" in SYSTEM_PROMPT or "markdown" in SYSTEM_PROMPT.lower()

    def test_chunk_prompt_exists(self):
        assert len(CHUNK_SUMMARY_PROMPT) > 0

    def test_merge_prompt_exists(self):
        assert len(MERGE_PROMPT) > 0


class TestSummaryAPI:
    @pytest.mark.asyncio
    async def test_task_has_summary_after_pipeline(self, client):
        # Create a task and directly set summary via the API's DB session
        resp = await client.post("/api/v1/tasks", json={
            "url": "https://youtube.com/watch?v=test"
        })
        assert resp.status_code == 201
        task_id = resp.json()["id"]

        # Directly update via DB to simulate pipeline completion
        from app.db.database import async_session
        from app.db.models import VideoTask
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(select(VideoTask).where(VideoTask.id == task_id))
            task = result.scalar_one_or_none()
            task.title = "Test Title"
            task.status = "completed"
            task.transcript = "转写文本"
            task.summary = "## 摘要\n\n总结内容"
            await db.commit()

        # Now verify the API returns the summary
        get_resp = await client.get(f"/api/v1/tasks/{task_id}")
        data = get_resp.json()
        assert data["status"] == "completed"
        assert data["summary"] == "## 摘要\n\n总结内容"


class TestWebRoutes:
    @pytest.mark.asyncio
    async def test_index_page(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Video Summary" in resp.text

    @pytest.mark.asyncio
    async def test_task_detail_page(self, client):
        create = await client.post("/api/v1/tasks", json={"url": "https://youtube.com/watch?v=test"})
        task_id = create.json()["id"]

        await asyncio.sleep(0.2)
        resp = await client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_task_list_partial(self, client):
        resp = await client.get("/partials/tasks")
        assert resp.status_code == 200
