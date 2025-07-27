from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardRemove
from sqlalchemy.orm import Session
from database.models import User
from utils.markdown import escape_md

login_router = Router(name="LoginHandler")

def get_or_create_user(session: Session, tg_id: int, name: str = None, last_name: str = None) -> User:
    """
    Получает пользователя из базы по tg_id или создаёт нового, если не найден.
    """
    user = session.query(User).filter(User.tg_id == tg_id).first()
    if not user:
        user = User(tg_id=tg_id, name=name, last_name=last_name)
        session.add(user)
        session.commit()
    return user

@login_router.message(CommandStart())
async def start_command(message: types.Message, db_session: Session):
    """
    Команда /start: создаёт пользователя в базе данных, если его ещё нет.
    """
    user = get_or_create_user(
        db_session, 
        message.from_user.id, 
        message.from_user.first_name, 
        message.from_user.last_name
    )
    await message.answer(escape_md(f"Привет, {user.name or 'пользователь'}! Я готов помочь с организацией твоих задач."),
                         reply_markup=ReplyKeyboardRemove())