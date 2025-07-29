from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.text import Const, Format, List
from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    Column,
    ScrollingGroup,
    Select,
    Cancel,
    Back,
    Group,
    Checkbox,
    SwitchTo,
)
from aiogram_dialog.widgets.input import MessageInput, TextInput, ManagedTextInput
from aiogram_dialog.widgets.kbd import Keyboard
from aiogram.types import Message
from pydantic import ValidationError
from sqlalchemy.orm import Session
from database.models import DbTask, TaskStatus, DbUser, DbSubtask
from datetime import datetime
from aiogram.fsm.state import State, StatesGroup
from utils.logger import tasks_logger
from pprint import pprint
from aiogram.types import CallbackQuery
from aiogram_dialog.widgets.common import ManagedWidget
import enum


class TaskMode(enum.Enum):
    EDIT = "Режим: ✏️ Редактирование"
    CHANGE_STATUS = "Режим: 📊 Изменение статуса"


def get_task_text(task: DbTask) -> str:
    """
    Format("🔹 {current_task.name}"),
    Format("📝 Описание: {current_task.description}"),
    Format("🔍 Статус: {current_task.status.value}"),
    Const("🧩 Подзадачи:", when="has_subtasks"),
    List(
        field= Format("• {item}"),
        items="text_for_subtasks"
    ),
    Format("🕒 Срок: {current_task.deadline}"),
    Format("🏷️ Теги: {current_task.tag}"),
    """
    text = f"🔹 {task.name}\n"
    if task.description:
        text += f"📝 Описание: {task.description}\n"
    text += f"🔍 Статус: {task.status.value}\n"
    if task.deadline:
        text += f"🕒 Срок: {task.deadline}\n"
    if task.tags:
        text += f"🏷️ Теги: {', '.join([tag.name for tag in task.tags])}\n"
    if task.subtasks and len(task.subtasks) > 0:
        text += f"🧩 Подзадачи:\n"
        for subtask in task.subtasks:
            text += f"• {subtask.name} {subtask.deadline}\n"
    # Connected events, notes, goals, ideas
    if task.events and len(task.events) > 0:
        text += f"🔗 Связанные события 📅: {', '.join([event.name for event in task.events])}\n"
    if task.notes and len(task.notes) > 0:
        text += (
            f"🔗 Связанные заметки 🗒️: {', '.join([note.name for note in task.notes])}\n"
        )
    if task.goals and len(task.goals) > 0:
        text += (
            f"🔗 Связанные цели 🎯: {', '.join([goal.name for goal in task.goals])}\n"
        )
    if task.ideas and len(task.ideas) > 0:
        text += (
            f"🔗 Связанные идеи 💡: {', '.join([idea.name for idea in task.ideas])}\n"
        )
    return text


# States
class TasksStates(StatesGroup):
    TASKS_LIST = State()
    TASK_DETAILS = State()
    ADD_TASK = State()
    CHANGE_NAME = State()
    CHANGE_DESCRIPTION = State()
    CHANGE_DEADLINE = State()
    CHANGE_STATUS = State()
    CHANGE_TAGS = State()
    DELETE_TASK = State()


# Data getters
async def get_tasks_data(dialog_manager: DialogManager, **kwargs) -> dict:
    db_session: Session = kwargs["db_session"]
    db_user: DbUser = kwargs["db_user"]
    tasks = (
        db_session.query(DbTask)
        .filter(DbTask.user_id == db_user.id, DbTask.is_deleted == False)
        .order_by(DbTask.created.desc())
        .all()
    )
    dialog_manager.dialog_data["mode"] = dialog_manager.dialog_data.get(
        "mode", TaskMode.CHANGE_STATUS.value
    )
    tasks_logger.info(f"Retrieved {len(tasks)} tasks for user {db_user.tg_id}")
    return {
        "tasks": tasks,
        "mode": dialog_manager.dialog_data.get("mode", TaskMode.CHANGE_STATUS.value),
    }


def get_subtask_text(subtask: DbSubtask) -> str:
    text = f"✅ " if subtask.is_done else f"❌ "
    text += f"{subtask.name}"
    if subtask.deadline:
        text += f" ({subtask.deadline})"
    return text


async def get_current_task_data(dialog_manager: DialogManager, **kwargs) -> dict:
    db_session: Session = kwargs["db_session"]
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    if not task_id:
        tasks_logger.warning("No selected_task_id in dialog_data")
        return {"current_task": None}
    task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not task:
        tasks_logger.warning(f"Task with id {task_id} not found")
        return {"current_task": None}
    tasks_logger.info(f"Retrieved task {task_id} for details window")
    return {
        "current_task": task,
        "has_subtasks": len(task.subtasks) > 0,
        "task_text": get_task_text(task),
    }


async def on_task_selected(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager, item_id: int
) -> None:
    manager.dialog_data["selected_task_id"] = item_id
    tasks_logger.info(f"Task selected: {item_id}")
    db_session: Session = manager.middleware_data["db_session"]
    if manager.dialog_data["mode"] == TaskMode.CHANGE_STATUS.value:
        db_current_task = db_session.query(DbTask).filter(DbTask.id == item_id).first()
        db_current_task.status = TaskStatus(db_current_task.status).next()
        db_session.commit()
        await callback.answer(f"Статус обновлён: {db_current_task.status.value}")
    else:
        await manager.switch_to(TasksStates.TASK_DETAILS)


async def on_add_task(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager
) -> None:
    tasks_logger.info("Add task button clicked")
    await manager.switch_to(TasksStates.ADD_TASK)


async def on_task_mode_select(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager
) -> None:
    manager.dialog_data["mode"] = (
        TaskMode.CHANGE_STATUS.value
        if manager.dialog_data["mode"] == TaskMode.EDIT.value
        else TaskMode.EDIT.value
    )
    tasks_logger.info(f"Task mode select button clicked: {manager.dialog_data['mode']}")


# --- NAME ---
async def on_change_task_name_success(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str
) -> None:
    tasks_logger.info(f"Task name changed: {message.text}")
    db_session: Session = dialog_manager.middleware_data["db_session"]
    task_id = dialog_manager.dialog_data["selected_task_id"]
    db_current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    db_current_task.name = text
    db_session.commit()
    await dialog_manager.switch_to(TasksStates.TASK_DETAILS)


async def on_change_task_name_error(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValidationError,
) -> None:
    tasks_logger.error(f"Error changing task name: {message.text}")
    await message.answer("Название задачи не должно превышать 50 символов")


def on_change_task_name_type_factory(text: str) -> str:
    if len(text) > 50:
        raise ValidationError("Название задачи не должно превышать 50 символов")
    return text


# --- DESCRIPTION ---
async def on_change_task_description_success(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str
) -> None:
    tasks_logger.info(f"Task description changed: {message.text}")
    db_session: Session = dialog_manager.middleware_data["db_session"]
    task_id = dialog_manager.dialog_data["selected_task_id"]
    db_current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    db_current_task.description = text
    db_session.commit()
    await dialog_manager.switch_to(TasksStates.TASK_DETAILS)


async def on_change_task_description_error(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValidationError,
) -> None:
    tasks_logger.error(f"Error changing task description: {message.text}")
    await message.answer("Описание задачи не должно превышать 500 символов")


def on_change_task_description_type_factory(text: str) -> str:
    if len(text) > 500:
        raise ValidationError("Описание задачи не должно превышать 500 символов")
    return text


# --- DEADLINE ---
async def on_change_task_deadline_success(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str
) -> None:
    tasks_logger.info(f"Task deadline changed: {message.text}")
    db_session: Session = dialog_manager.middleware_data["db_session"]
    task_id = dialog_manager.dialog_data["selected_task_id"]
    db_current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    try:
        deadline = datetime.strptime(text, "%Y-%m-%d %H:%M")
    except Exception as e:
        tasks_logger.error(f"Invalid deadline format: {text}")
        await message.answer("Некорректный формат даты. Используйте ГГГГ-ММ-ДД ЧЧ:ММ")
        return
    db_current_task.deadline = deadline
    db_session.commit()
    await dialog_manager.switch_to(TasksStates.TASK_DETAILS)


async def on_change_task_deadline_error(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValidationError,
) -> None:
    tasks_logger.error(f"Error changing task deadline: {message.text}")
    await message.answer("Некорректный формат даты. Используйте ГГГГ-ММ-ДД ЧЧ:ММ")


def on_change_task_deadline_type_factory(text: str) -> str:
    try:
        datetime.strptime(text, "%Y-%m-%d %H:%M")
    except Exception:
        raise ValidationError("Некорректный формат даты. Используйте ГГГГ-ММ-ДД ЧЧ:ММ")
    return text


# --- STATUS ---
async def on_change_task_status_success(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str
) -> None:
    tasks_logger.info(f"Task status changed: {message.text}")
    db_session: Session = dialog_manager.middleware_data["db_session"]
    task_id = dialog_manager.dialog_data["selected_task_id"]
    db_current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    # Поддерживаем только значения из TaskStatus
    status_map = {s.value: s for s in TaskStatus}
    if text not in status_map:
        await message.answer(
            "Некорректный статус. Используйте один из: "
            + ", ".join([s.value for s in TaskStatus])
        )
        return
    db_current_task.status = status_map[text]
    db_session.commit()
    await dialog_manager.switch_to(TasksStates.TASK_DETAILS)


async def on_change_task_status_error(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValidationError,
) -> None:
    tasks_logger.error(f"Error changing task status: {message.text}")
    await message.answer(
        "Некорректный статус. Используйте один из: "
        + ", ".join([s.value for s in TaskStatus])
    )


def on_change_task_status_type_factory(text: str) -> str:
    if text not in [s.value for s in TaskStatus]:
        raise ValidationError("Некорректный статус")
    return text


async def change_task_status(
    callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str
) -> None:
    """
    Handler for changing the status of a task via Select widget.
    item_id: TaskStatus.name (str)
    """
    db_session: Session = manager.middleware_data["db_session"]
    task_id = manager.dialog_data["selected_task_id"]
    db_current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not db_current_task:
        await callback.answer("Ошибка: задача не найдена в базе", show_alert=True)
        return
    new_status = TaskStatus[item_id]
    tasks_logger.info(f"Changing task status to: {new_status}")
    db_current_task.status = new_status
    db_session.commit()
    await manager.switch_to(TasksStates.TASK_DETAILS)
    await callback.answer("Статус обновлён")


tasks_dialog = Dialog(
    Window(
        Const("📋 Ваши задачи:"),
        ScrollingGroup(
            Row(
                Select(
                    Format("{item.status.value} {item.name}"),
                    id="select_task",
                    item_id_getter=lambda x: x.id,
                    items="tasks",
                    on_click=on_task_selected,
                    when="tasks",
                )
            ),
            hide_on_single_page=True,
            id="scroll_tasks",
            height=8,
            width=1,
        ),
        Button(Format("{mode}"), id="select_task_mode", on_click=on_task_mode_select),
        Button(Const("➕ Добавить задачу"), id="add_task", on_click=on_add_task),
        Cancel(Const("🔙 Закрыть")),
        state=TasksStates.TASKS_LIST,
        getter=get_tasks_data,
    ),
    Window(
        Format("{task_text}"),
        Group(
            SwitchTo(
                Const("✏️ Имя"), id="change_task_name", state=TasksStates.CHANGE_NAME
            ),
            SwitchTo(
                Const("📝 Описание"),
                id="change_task_description",
                state=TasksStates.CHANGE_DESCRIPTION,
            ),
            SwitchTo(
                Const("⏰ Срок"),
                id="change_task_deadline",
                state=TasksStates.CHANGE_DEADLINE,
            ),
            SwitchTo(
                Const("🏷️ Теги"), id="change_task_tags", state=TasksStates.CHANGE_TAGS
            ),
            SwitchTo(
                Const("🔄 Статус"),
                id="change_task_status",
                state=TasksStates.CHANGE_STATUS,
            ),
            SwitchTo(
                Const("🔗 Cобытия 📅"),
                id="change_task_events",
                state=TasksStates.CHANGE_EVENTS,
            ),
            SwitchTo(
                Const("🔗 Заметки 🗒️"),
                id="change_task_notes",
                state=TasksStates.CHANGE_NOTES,
            ),
            SwitchTo(
                Const("🔗 Цели 🎯"),
                id="change_task_goals",
                state=TasksStates.CHANGE_GOALS,
            ),
            SwitchTo(
                Const("🔗 Идеи 💡"),
                id="change_task_ideas",
                state=TasksStates.CHANGE_IDEAS,
            ),
            SwitchTo(
                Const("🗑️ Удалить"), id="delete_task", state=TasksStates.DELETE_TASK
            ),
            width=2,
        ),
        Back(Const("🔙 Назад"), id="back_to_tasks"),
        state=TasksStates.TASK_DETAILS,
        getter=get_current_task_data,
    ),
    # --- NAME ---
    Window(
        Const("✏️ Меню изменения названия задачи"),
        Format("🏷️ Текущее название: {current_task.name}"),
        Const("⚠️ Название задачи не должно превышать 50 символов"),
        Const("📝 Введите новое название задачи:"),
        TextInput(
            id="change_task_name_input",
            type_factory=on_change_task_name_type_factory,
            on_success=on_change_task_name_success,
            on_error=on_change_task_name_error,
        ),
        Back(Const("🔙 Назад"), id="back_to_task_details"),
        state=TasksStates.CHANGE_NAME,
        getter=get_current_task_data,
    ),
    # --- DESCRIPTION ---
    Window(
        Const("📝 Меню изменения описания задачи"),
        Format("📝 Текущее описание: {current_task.description}"),
        Const("⚠️ Описание задачи не должно превышать 500 символов"),
        Const("📝 Введите новое описание задачи:"),
        TextInput(
            id="change_task_description_input",
            type_factory=on_change_task_description_type_factory,
            on_success=on_change_task_description_success,
            on_error=on_change_task_description_error,
        ),
        Back(Const("🔙 Назад"), id="back_to_task_details"),
        state=TasksStates.CHANGE_DESCRIPTION,
        getter=get_current_task_data,
    ),
    # --- DEADLINE ---
    Window(
        Const("⏰ Меню изменения срока задачи"),
        Format("🕒 Текущий срок: {current_task.deadline}"),
        Const("⚠️ Введите срок в формате: ГГГГ-ММ-ДД ЧЧ:ММ"),
        Const("📝 Введите новый срок задачи:"),
        TextInput(
            id="change_task_deadline_input",
            type_factory=on_change_task_deadline_type_factory,
            on_success=on_change_task_deadline_success,
            on_error=on_change_task_deadline_error,
        ),
        Back(Const("🔙 Назад"), id="back_to_task_details"),
        state=TasksStates.CHANGE_DEADLINE,
        getter=get_current_task_data,
    ),
    # --- STATUS ---
    Window(
        Const("🔄 Меню изменения статуса задачи"),
        Format("🔍 Текущий статус: {current_task.status.value}"),
        Const("Выберите новый статус:"),
        Select(
            Format("{item.value}"),
            id="select_task_status",
            item_id_getter=lambda status: status.name,
            items=list(TaskStatus),
            on_click=change_task_status,
        ),
        Back(Const("🔙 Назад"), id="back_to_task_details"),
        state=TasksStates.CHANGE_STATUS,
        getter=get_current_task_data,
    ),
)
