from app.repositories.base_repository import BaseRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.deal_repository import DealRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ClientRepository",
    "DealRepository",
    "ContactRepository",
    "TaskRepository",
]
