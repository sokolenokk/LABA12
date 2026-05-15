from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus, TaskType


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority = TaskPriority.medium
    task_type: TaskType = TaskType.other


class TaskCreate(TaskBase):
    assigned_to: int | None = None
    client_id: int | None = None
    deal_id: int | None = None
    status: TaskStatus = TaskStatus.pending


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority | None = None
    task_type: TaskType | None = None
    assigned_to: int | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TaskStatus
    assigned_to: int | None
    client_id: int | None
    deal_id: int | None
    created_at: datetime
    updated_at: datetime
