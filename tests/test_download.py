from unittest.mock import patch
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.download.downloader import VideoDownloader, VideoInfo


class TestVideoDownloader:
    def test_get_info_returns_video_info(self, mock_yt_dlp):
        downloader = VideoDownloader()
        info = downloader.get_info("https://youtube.com/watch?v=test")
        assert info.title == "Test Video"
        assert info.duration == 300
        assert info.thumbnail == "https://example.com/thumb.jpg"

    @pytest.mark.asyncio
    async def test_download_returns_path(self, mock_yt_dlp):
        downloader = VideoDownloader()
        with patch("builtins.open", create=True), patch("pathlib.Path.exists", return_value=True):
            path = await downloader.download("https://youtube.com/watch?v=test", "task-1")
            assert isinstance(path, Path)


class TestTaskAPI:
    @pytest.mark.asyncio
    async def test_create_task(self, client: AsyncClient):
        resp = await client.post("/api/v1/tasks", json={"url": "https://youtube.com/watch?v=test"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://youtube.com/watch?v=test"
        assert data["status"] in ("pending", "downloading", "downloaded")
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_task(self, client: AsyncClient):
        create = await client.post("/api/v1/tasks", json={"url": "https://youtube.com/watch?v=test"})
        task_id = create.json()["id"]

        resp = await client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    @pytest.mark.asyncio
    async def test_get_task_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/tasks/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_tasks(self, client: AsyncClient):
        await client.post("/api/v1/tasks", json={"url": "https://youtube.com/watch?v=a"})
        await client.post("/api/v1/tasks", json={"url": "https://youtube.com/watch?v=b"})

        resp = await client.get("/api/v1/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
