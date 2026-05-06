from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import VideoTask
from app.download.downloader import VideoDownloader
from app.download.schema import TaskCreateRequest, TaskResponse, TaskListResponse
from app.tasks.pipeline import SummaryPipeline

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _to_response(task: VideoTask) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        url=task.url,
        title=task.title,
        duration=task.duration,
        thumbnail=task.thumbnail,
        status=task.status,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task = VideoTask(url=body.url, status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)

    pipeline = SummaryPipeline()
    background_tasks.add_task(pipeline.run, task.id)
    return _to_response(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VideoTask).order_by(VideoTask.created_at.desc()))
    tasks = result.scalars().all()
    return TaskListResponse(
        items=[_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VideoTask).where(VideoTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _to_response(task)
