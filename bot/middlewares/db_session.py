from aiogram.dispatcher.middlewares.base import BaseMiddleware
from sqlalchemy.orm import sessionmaker, Session
from typing import Callable, Awaitable, Dict, Any
from database.models import User
from aiogram.types import Message
from utils.logger import db_logger

class DBSessionMiddleware(BaseMiddleware):
    """
    Мидлварь для управления сессией БД в каждом запросе.
    """
    def __init__(self):
        super().__init__()

    async def __call__(self, handler: Callable, message: Message, data: Dict[str, Any]) -> Awaitable:
        session_factory = data.get("session_factory", None)
        if session_factory is None:
            db_logger.error("session_factory is not set")
            raise ValueError("session_factory is not set")
        
        session: Session = session_factory()
        data["db_session"] = session
        db_logger.debug(f"Database session created for message from user {message.from_user.id}")
        
        try:
            return await handler(message, data)
        finally:
            session.close()
            db_logger.debug("Database session closed")

class LoginMiddleware(BaseMiddleware):
    """
    Мидлварь для проверки авторизации пользователя.
    """
    def __init__(self):
        super().__init__()

    async def __call__(self, handler: Callable, message: Message, data: Dict[str, Any]) -> Awaitable:
        session: Session = data.get("db_session", None)
        if session is None:
            db_logger.error("db_session is not set")
            raise ValueError("db_session is not set")
        
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user is None:
            db_logger.warning(f"Unauthorized access attempt from user {message.from_user.id}")
            await message.answer("❌ Для начала работы выполните команду /start")
            return
        
        db_logger.debug(f"User authenticated: {user.tg_id} ({user.name})")
        data["db_user"] = user
        return await handler(message, data)