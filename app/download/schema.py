from pydantic import BaseModel
from datetime import datetime


class TaskCreateRequest(BaseModel):
    url: str


class TaskResponse(BaseModel):
    id: str
    url: str
    title: str | None
    duration: int | None
    thumbnail: str | None
    status: str
    transcript: str | None = None
    summary: str | None = None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
