from datetime import datetime, timezone

from sqlalchemy import select

from app.models.task import Task, TaskStatus
from app.repositories.base_repository import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def get_by_assigned_user(self, user_id: int) -> list[Task]:
        stmt = select(Task).where(Task.assigned_to == user_id).order_by(Task.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_overdue(self, user_id: int | None = None) -> list[Task]:
        now = datetime.now(timezone.utc)
        stmt = select(Task).where(
            Task.due_date.is_not(None),
            Task.due_date < now,
            Task.status.in_([TaskStatus.pending, TaskStatus.in_progress]),
        )
        if user_id is not None:
            stmt = stmt.where(Task.assigned_to == user_id)
        stmt = stmt.order_by(Task.due_date)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
