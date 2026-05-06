from fastapi import APIRouter, Request, Depends, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db, async_session
from app.db.models import VideoTask
from app.tasks.pipeline import SummaryPipeline
from app.templates import templates

router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    html = templates.get_template("index.html").render(request=request)
    return HTMLResponse(html)


@router.post("/tasks")
async def create_task_web(url: str = Form(...), background_tasks: BackgroundTasks = None):
    async with async_session() as db:
        task = VideoTask(url=url, status="pending")
        db.add(task)
        await db.commit()
        task_id = task.id

    pipeline = SummaryPipeline()
    background_tasks.add_task(pipeline.run, task_id)
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VideoTask).where(VideoTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        html = templates.get_template("index.html").render(request=request, error="任务不存在")
        return HTMLResponse(html, status_code=404)
    html = templates.get_template("task.html").render(request=request, task=task)
    return HTMLResponse(html)


@router.get("/partials/tasks", response_class=HTMLResponse)
async def task_list_partial(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VideoTask).order_by(VideoTask.created_at.desc()))
    tasks = result.scalars().all()
    return _render_task_list(tasks)


def _status_icon(status: str) -> str:
    icons = {
        "completed": "✅",
        "failed": "❌",
        "summarizing": "🔄",
        "transcribing": "🔄",
        "extracting": "🔄",
        "downloading": "🔄",
        "transcribed": "⏳",
        "extracted": "⏳",
        "downloaded": "⏳",
        "pending": "⬜",
    }
    return icons.get(status, "⬜")


def _status_text(status: str) -> str:
    texts = {
        "pending": "等待中",
        "downloading": "下载中",
        "downloaded": "已下载",
        "extracting": "提取中",
        "extracted": "已提取",
        "transcribing": "转写中",
        "transcribed": "已转写",
        "summarizing": "摘要中",
        "completed": "已完成",
        "failed": "失败",
    }
    return texts.get(status, status)


def _render_task_list(tasks) -> str:
    if not tasks:
        return '<p class="text-sm text-gray-400">暂无任务</p>'

    rows = []
    for t in tasks:
        rows.append(
            f'<a href="/tasks/{t.id}" class="block p-3 border-b hover:bg-gray-50 transition">'
            f'<div class="flex items-center justify-between">'
            f'<span class="text-sm font-medium truncate flex-1">{t.title or t.url}</span>'
            f'<span class="text-xs ml-2 whitespace-nowrap">{_status_icon(t.status)} {_status_text(t.status)}</span>'
            f'</div>'
            f'<div class="text-xs text-gray-400 mt-1">{t.created_at.strftime("%m-%d %H:%M")}</div>'
            f'</a>'
        )
    return "".join(rows)
