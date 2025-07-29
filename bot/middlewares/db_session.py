from aiogram.dispatcher.middlewares.base import BaseMiddleware
from sqlalchemy.orm import sessionmaker, Session
from typing import Callable, Awaitable, Dict, Any, Optional
from database.models import DbUser
from aiogram.types import User, Update
from utils.logger import db_logger
from pprint import pprint

def get_or_create_user(session: Session, tg_id: int, name: str = None, last_name: str = None, username: str = None) -> DbUser:
    """
    Получает пользователя из базы по tg_id или создаёт нового, если не найден.
    """
    user = session.query(DbUser).filter(DbUser.tg_id == tg_id).first()
    if not user:
        user = DbUser(tg_id=tg_id, name=name, last_name=last_name, username=username)
        session.add(user)
        session.commit()
    return user

class DbSessionMiddleware(BaseMiddleware):
    """
    Мидлварь для управления сессией БД в каждом запросе.
    """
    def __init__(self):
        super().__init__()

    async def __call__(self, handler: Callable, update: Update, data: Dict[str, Any]) -> Awaitable:
        session_factory: Optional[Callable[[], Session]] = data.get("session_factory", None)
        if session_factory is None:
            db_logger.error("session_factory is not set")
            raise ValueError("session_factory is not set")
        
        session: Session = session_factory()
        data["db_session"] = session

        event_from_user: Optional[User] = data.get("event_from_user", None)
        if event_from_user is None:
            db_logger.error("event_from_user is not set")
            raise ValueError("event_from_user is not set")
        
        user: DbUser = get_or_create_user(session, event_from_user.id, event_from_user.username)
        data["db_user"] = user
        
        db_logger.debug(f"Database session created for update from user {user.tg_id} {user.username}")
        
        try:
            return await handler(update, data)
        finally:
            session.close()
            db_logger.debug("Database session closed")
