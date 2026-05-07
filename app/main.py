from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.models import Base
from app.db.database import engine
from app.download.router import router as task_router
from app.web.router import router as web_router
from app.templates import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Video Summary", version="0.1.0", lifespan=lifespan)
app.include_router(task_router)
app.include_router(web_router)
