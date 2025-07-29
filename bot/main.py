from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from environs import Env
from handlers.voice import voice_router as voice_router
from handlers.login import login_router as login_router
from handlers.tasks import tasks_router as tasks_router
from dialogs.tasks_dialog import tasks_dialog
from aiogram_dialog import setup_dialogs
from middlewares.db_session import DbSessionMiddleware
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from utils.logger import bot_logger
import sys
import os

# Инициализация переменных окружения
env = Env()
env.read_env()

bot_logger.info("Starting bot initialization...")
bot_logger.info(f"Bot token: {env('TELEGRAM_BOT_TOKEN')[:10]}...")

bot = Bot(token=env("TELEGRAM_BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Инициализация SQLAlchemy engine и sessionmaker для PostgreSQL
DATABASE_URL = env("DATABASE_URL")
bot_logger.info(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Проверка инициализации базы
from database.models import Base, DbTask, DbEvent, DbGoal, DbIdea, DbNote, DbTag
inspector = inspect(engine)
required_tables = [cls.__tablename__ for cls in [DbTask, DbEvent, DbGoal, DbIdea, DbNote, DbTag]]
missing = [t for t in required_tables if not inspector.has_table(t)]
if missing:
    bot_logger.error(f"Database not initialized. Missing tables: {', '.join(missing)}")
    bot_logger.error("Run 'alembic upgrade head' to initialize schema.")
    sys.exit(1)
else:
    bot_logger.info("Database schema check passed")

dp = Dispatcher(session_factory=SessionLocal)
dp.include_router(login_router)
dp.include_router(voice_router)
dp.include_router(tasks_router)
dp.include_router(tasks_dialog)

setup_dialogs(dp)


dp.update.middleware(DbSessionMiddleware())

bot_logger.info("Bot setup completed, starting polling...")

if __name__ == "__main__":
    bot_logger.info("Starting bot polling...")
    dp.run_polling(bot)