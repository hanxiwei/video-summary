import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


@pytest.fixture
def mock_yt_dlp():
    with patch("app.download.downloader.yt_dlp.YoutubeDL") as mock:
        mock.return_value.__enter__.return_value.extract_info.return_value = {
            "title": "Test Video",
            "duration": 300,
            "thumbnail": "https://example.com/thumb.jpg",
        }
        mock.return_value.__enter__.return_value.prepare_filename.return_value = "/tmp/test.mp4"
        yield mock


@pytest.fixture
async def init_db():
    from app.db.database import engine
    from app.db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(init_db, mock_yt_dlp):
    from app.db.database import engine, get_db
    from app.main import app

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
