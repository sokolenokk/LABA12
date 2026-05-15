from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskService(session).list_for_user(current_user)


@router.get("/overdue", response_model=list[TaskResponse])
async def list_overdue(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskService(session).list_overdue(current_user)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskService(session).create(data, current_user)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskService(session).update(task_id, data, current_user)


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def change_status(
    task_id: int,
    data: TaskStatusUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskService(session).change_status(task_id, data.status, current_user)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await TaskService(session).delete(task_id, current_user)
