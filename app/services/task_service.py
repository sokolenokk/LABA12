from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TaskRepository(session)

    async def list_for_user(self, user: User) -> list[Task]:
        if user.role in (UserRole.admin, UserRole.manager):
            return await self.repo.get_multi(skip=0, limit=1000)
        return await self.repo.get_by_assigned_user(user.id)

    async def list_overdue(self, user: User) -> list[Task]:
        if user.role in (UserRole.admin, UserRole.manager):
            return await self.repo.get_overdue()
        return await self.repo.get_overdue(user_id=user.id)

    async def get_or_404(self, task_id: int, user: User) -> Task:
        task = await self.repo.get(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        if user.role == UserRole.sales_rep and task.assigned_to != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not your task"
            )
        return task

    async def create(self, data: TaskCreate, user: User) -> Task:
        payload = data.model_dump()
        if user.role == UserRole.sales_rep or payload.get("assigned_to") is None:
            payload["assigned_to"] = user.id
        return await self.repo.create(payload)

    async def update(self, task_id: int, data: TaskUpdate, user: User) -> Task:
        task = await self.get_or_404(task_id, user)
        payload = data.model_dump(exclude_unset=True)
        if user.role == UserRole.sales_rep:
            payload.pop("assigned_to", None)
        updated = await self.repo.update(task.id, payload)
        assert updated is not None
        return updated

    async def change_status(
        self, task_id: int, new_status: TaskStatus, user: User
    ) -> Task:
        task = await self.get_or_404(task_id, user)
        updated = await self.repo.update(task.id, {"status": new_status})
        assert updated is not None
        return updated

    async def delete(self, task_id: int, user: User) -> None:
        if user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin only"
            )
        ok = await self.repo.delete(task_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
