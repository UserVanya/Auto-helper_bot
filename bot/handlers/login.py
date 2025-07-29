from aiogram import Router, Bot
from aiogram.types import Message, BotCommand, BotCommandScopeChat
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardRemove

login_router = Router(name="LoginHandler")



@login_router.message(CommandStart())
async def start_command(message: Message, bot: Bot):
    """
    Команда /start: создаёт пользователя в базе данных, если его ещё нет.
    """
    await bot.set_my_commands(commands=[
            #BotCommand(command="start", description="Начать работу с ботом"),
            #BotCommand(command="help", description="Помощь по командам"),
            BotCommand(command="tasks", description="Управление задачами"),
            #BotCommand(command="events", description="Управление событиями"),
            #BotCommand(command="goals", description="Управление целями"),
        ],
        scope=BotCommandScopeChat(chat_id=message.chat.id)
    )
    await message.answer(f"Привет, {message.from_user.username or 'пользователь'}! Я готов помочь с организацией твоих задач.",
                         reply_markup=ReplyKeyboardRemove())