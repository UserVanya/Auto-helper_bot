from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy.orm import Session
from database.models import DbTask, DbUser
from dialogs.tasks_dialog import TasksStates, tasks_dialog
from utils.logger import tasks_logger
tasks_router = Router(name="TasksHandler")

# Command handler
@tasks_router.message(Command("tasks"))
async def cmd_tasks(message: Message, dialog_manager: DialogManager, db_session: Session, db_user: DbUser):
    """
    Command handler for /tasks - shows all user tasks
    """
    tasks_logger.info(f"Tasks command received from user {db_user.tg_id} ({db_user.name})")
    
    # Get user's tasks
    tasks = db_session.query(DbTask).filter(
        DbTask.user_id == db_user.id,
        DbTask.is_deleted == False
    ).order_by(DbTask.created.desc()).all()
    
    tasks_logger.info(f"Found {len(tasks)} tasks for user {db_user.tg_id}")

    if not tasks:
        tasks_logger.info(f"No tasks found for user {db_user.tg_id}")
        await message.answer("📋 У вас пока нет задач. Используйте голосовые команды для создания задач!")
        return
    
    # Start dialog with tasks data
    tasks_logger.info(f"Starting tasks dialog for user {db_user.tg_id} with {len(tasks)} tasks")
    await dialog_manager.start(
        TasksStates.TASKS_LIST,
        data={"tasks": tasks},
        mode=StartMode.RESET_STACK   
    )
