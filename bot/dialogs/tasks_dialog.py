import operator
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.text import Const, Format, List, Case
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
    Multiselect,
)
from aiogram_dialog.widgets.input import MessageInput, TextInput, ManagedTextInput
from aiogram_dialog.widgets.kbd import Keyboard
from aiogram.types import Message

from sqlalchemy.orm import Session
from database.models import DbTask, TaskStatus, DbUser, DbSubtask, DbEvent, DbNote, DbGoal, DbIdea, DbTag
from datetime import datetime
from aiogram.fsm.state import State, StatesGroup
from utils.logger import tasks_logger
from pprint import pprint
from aiogram.types import CallbackQuery
from aiogram_dialog.widgets.common import ManagedWidget
from magic_filter import F
import enum


class TaskMode(enum.Enum):
    EDIT = "Режим: ✏️ Редактирование"
    CHANGE_STATUS = "Режим: 📊 Изменение статуса"


class SubtaskMode(enum.Enum):
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
            text += f"• {subtask.name} {'✅' if subtask.is_done else '⬜'}\n"
    # Connected events, notes, goals, ideas
    if task.events and len(task.events) > 0:
        events_text = "\n".join([f"• {event.name}" for event in task.events])
        text += f"🔗 Связанные события 📅:\n {events_text}\n"
    if task.notes and len(task.notes) > 0:
        notes_text = "\n".join([f"• {note.name}" for note in task.notes])
        text += (
            f"🔗 Связанные заметки 🗒️:\n {notes_text}\n"
        )
    if task.goals and len(task.goals) > 0:
        goals_text = "\n".join([f"• {goal.name}" for goal in task.goals])
        text += (
            f"🔗 Связанные цели 🎯:\n {goals_text}\n"
        )
    if task.ideas and len(task.ideas) > 0:
        ideas_text = "\n".join([f"• {idea.name}" for idea in task.ideas])
        text += (
            f"🔗 Связанные идеи 💡:\n {ideas_text}\n"
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
    CHANGE_EVENTS = State()
    CHANGE_NOTES = State()
    CHANGE_GOALS = State()
    CHANGE_IDEAS = State()

    ADD_SUBTASK = State()

    DELETE_TASK = State()
    # Новые состояния для управления подзадачами
    SUBTASKS_LIST = State()
    SUBTASK_DETAILS = State()
    CHANGE_SUBTASK_NAME = State()
    DELETE_SUBTASK = State()


# Data getters
async def get_tasks_data(dialog_manager: DialogManager, **kwargs) -> dict:
    db_session: Session = kwargs["db_session"]
    db_user: DbUser = kwargs["db_user"]
    tasks = (
        db_session.query(DbTask)
        .filter(DbTask.user_id == db_user.id, DbTask.is_deleted == False)
        .order_by(DbTask.id.desc())
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


async def get_events_data(dialog_manager: DialogManager, **kwargs) -> dict:
    """Получение данных для управления связанными событиями"""
    db_session: Session = kwargs["db_session"]
    db_user: DbUser = kwargs["db_user"]
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    
    # Получаем все события пользователя
    all_events = (
        db_session.query(DbEvent)
        .filter(DbEvent.user_id == db_user.id, DbEvent.is_deleted == False)
        .order_by(DbEvent.id)
        .all()
    )
    
    # Получаем текущую задачу для определения уже связанных событий
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    selected_event_ids = [event.id for event in current_task.events] if current_task else []
    
    # Устанавливаем начальное состояние multiselect
    if not dialog_manager.dialog_data.get("events_checked_set"):
        events_widget = dialog_manager.dialog().find("select_events")
        if events_widget:
            for event_id in selected_event_ids:
                events_widget.set_checked(dialog_manager, str(event_id), True)
        dialog_manager.dialog_data["events_checked_set"] = True
    
    return {
        "all_events": all_events,
        "selected_event_ids": selected_event_ids,
        "current_task": current_task,
    }


async def get_notes_data(dialog_manager: DialogManager, **kwargs) -> dict:
    """Получение данных для управления связанными заметками"""
    db_session: Session = kwargs["db_session"]
    db_user: DbUser = kwargs["db_user"]
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    
    # Получаем все заметки пользователя
    all_notes = (
        db_session.query(DbNote)
        .filter(DbNote.user_id == db_user.id, DbNote.is_deleted == False)
        .order_by(DbNote.id)
        .all()
    )
    
    # Получаем текущую задачу для определения уже связанных заметок
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    selected_note_ids = [note.id for note in current_task.notes] if current_task else []
    
    # Устанавливаем начальное состояние multiselect
    if not dialog_manager.dialog_data.get("notes_checked_set"):
        notes_widget = dialog_manager.dialog().find("select_notes")
        if notes_widget:
            for note_id in selected_note_ids:
                notes_widget.set_checked(dialog_manager, str(note_id), True)
        dialog_manager.dialog_data["notes_checked_set"] = True
    
    return {
        "all_notes": all_notes,
        "selected_note_ids": selected_note_ids,
        "current_task": current_task,
    }


async def get_goals_data(dialog_manager: DialogManager, **kwargs) -> dict:
    """Получение данных для управления связанными целями"""
    db_session: Session = kwargs["db_session"]
    db_user: DbUser = kwargs["db_user"]
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    
    # Получаем все цели пользователя
    all_goals = (
        db_session.query(DbGoal)
        .filter(DbGoal.user_id == db_user.id, DbGoal.is_deleted == False)
        .order_by(DbGoal.id)
        .all()
    )
    
    # Получаем текущую задачу для определения уже связанных целей
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    selected_goal_ids = [goal.id for goal in current_task.goals] if current_task else []
    
    # Устанавливаем начальное состояние multiselect
    if not dialog_manager.dialog_data.get("goals_checked_set"):
        goals_widget = dialog_manager.dialog().find("select_goals")
        if goals_widget:
            for goal_id in selected_goal_ids:
                goals_widget.set_checked(dialog_manager, str(goal_id), True)
        dialog_manager.dialog_data["goals_checked_set"] = True
    
    return {
        "all_goals": all_goals,
        "selected_goal_ids": selected_goal_ids,
        "current_task": current_task,
    }


async def get_ideas_data(dialog_manager: DialogManager, **kwargs) -> dict:
    """Получение данных для управления связанными идеями"""
    db_session: Session = kwargs["db_session"]
    db_user: DbUser = kwargs["db_user"]
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    
    # Получаем все идеи пользователя
    all_ideas = (
        db_session.query(DbIdea)
        .filter(DbIdea.user_id == db_user.id, DbIdea.is_deleted == False)
        .order_by(DbIdea.id)
        .all()
    )
    
    # Получаем текущую задачу для определения уже связанных идей
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    selected_idea_ids = [idea.id for idea in current_task.ideas] if current_task else []
    
    # Устанавливаем начальное состояние multiselect
    if not dialog_manager.dialog_data.get("ideas_checked_set"):
        ideas_widget = dialog_manager.dialog().find("select_ideas")
        if ideas_widget:
            for idea_id in selected_idea_ids:
                ideas_widget.set_checked(dialog_manager, str(idea_id), True)
        dialog_manager.dialog_data["ideas_checked_set"] = True
    
    return {
        "all_ideas": all_ideas,
        "selected_idea_ids": selected_idea_ids,
        "current_task": current_task,
    }


async def get_tags_data(dialog_manager: DialogManager, **kwargs) -> dict:
    """Получение данных для управления связанными тегами"""
    db_session: Session = kwargs["db_session"]
    db_user: DbUser = kwargs["db_user"]
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    
    # Получаем все теги пользователя
    all_tags = (
        db_session.query(DbTag)
        .filter(DbTag.user_id == db_user.id, DbTag.is_deleted == False)
        .order_by(DbTag.id)
        .all()
    )
    
    # Получаем текущую задачу для определения уже связанных тегов
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    selected_tag_ids = [tag.id for tag in current_task.tags] if current_task else []
    
    # Устанавливаем начальное состояние multiselect
    if not dialog_manager.dialog_data.get("tags_checked_set"):
        tags_widget = dialog_manager.dialog().find("select_tags")
        if tags_widget:
            for tag_id in selected_tag_ids:
                tags_widget.set_checked(dialog_manager, str(tag_id), True)
        dialog_manager.dialog_data["tags_checked_set"] = True
    
    return {
        "all_tags": all_tags,
        "selected_tag_ids": selected_tag_ids,
        "current_task": current_task,
    }





async def get_subtasks_list_data(dialog_manager: DialogManager, **kwargs) -> dict:
    """Получение данных для списка подзадач с режимами"""
    db_session: Session = kwargs["db_session"]
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    
    # Получаем текущую задачу
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not current_task:
        return {"current_task": None, "subtasks": [], "mode": SubtaskMode.CHANGE_STATUS.value}
    
    # Получаем все подзадачи текущей задачи (не удаленные)
    subtasks = (
        db_session.query(DbSubtask)
        .filter(DbSubtask.task_id == task_id, DbSubtask.is_deleted == False)
        .order_by(DbSubtask.id)
        .all()
    )
    
    # Устанавливаем режим по умолчанию
    dialog_manager.dialog_data["subtask_mode"] = dialog_manager.dialog_data.get(
        "subtask_mode", SubtaskMode.CHANGE_STATUS.value
    )
    subtasks_info = [
        {
            "id": item.id,
            "info": f"{'✅' if item.is_done else '⬜'} {item.name}",
        }
        for item in subtasks
    ]
    print(subtasks_info)
    tasks_logger.info(f"Retrieved {len(subtasks)} subtasks for task {task_id}")
    return {
        "current_task": current_task,
        "subtasks_info": subtasks_info,
        "mode": dialog_manager.dialog_data.get("subtask_mode", SubtaskMode.CHANGE_STATUS.value),
    }


async def get_current_subtask_data(dialog_manager: DialogManager, **kwargs) -> dict:
    """Получение данных текущей подзадачи"""
    db_session: Session = kwargs["db_session"]
    subtask_id = dialog_manager.dialog_data.get("selected_subtask_id")
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    
    if not subtask_id:
        tasks_logger.warning("No selected_subtask_id in dialog_data")
        return {"current_subtask": None, "current_task": None}
    
    subtask = db_session.query(DbSubtask).filter(DbSubtask.id == subtask_id).first()
    if not subtask:
        tasks_logger.warning(f"Subtask with id {subtask_id} not found")
        return {"current_subtask": None, "current_task": None}
    
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    
    tasks_logger.info(f"Retrieved subtask {subtask_id} for details window")
    return {
        "current_subtask": subtask,
        "current_task": current_task,
        "done_info": f"✅ Выполнена" if subtask.is_done else f"⬜ Не выполнена",
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


async def on_subtask_selected(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager, item_id: int
) -> None:
    manager.dialog_data["selected_subtask_id"] = item_id
    tasks_logger.info(f"Subtask selected: {item_id}")
    db_session: Session = manager.middleware_data["db_session"]
    if manager.dialog_data["subtask_mode"] == SubtaskMode.CHANGE_STATUS.value:
        db_current_subtask = db_session.query(DbSubtask).filter(DbSubtask.id == item_id).first()
        db_current_subtask.is_done = not db_current_subtask.is_done
        db_session.commit()
        status_text = "выполнена" if db_current_subtask.is_done else "не выполнена"
        await callback.answer(f"Подзадача теперь {status_text}")
    else:
        await manager.switch_to(TasksStates.SUBTASK_DETAILS)


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


async def on_subtask_mode_select(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager
) -> None:
    manager.dialog_data["subtask_mode"] = (
        SubtaskMode.CHANGE_STATUS.value
        if manager.dialog_data["subtask_mode"] == SubtaskMode.EDIT.value
        else SubtaskMode.EDIT.value
    )
    tasks_logger.info(f"Subtask mode select button clicked: {manager.dialog_data['subtask_mode']}")


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
    error: ValueError,
) -> None:
    tasks_logger.error(f"Error changing task name: {message.text}")
    await message.answer("Название задачи не должно превышать 50 символов")


def on_change_task_name_type_factory(text: str) -> str:
    if len(text) > 50:
        raise ValueError("Название задачи не должно превышать 50 символов")
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
    error: ValueError,
) -> None:
    tasks_logger.error(f"Error changing task description: {message.text}")
    await message.answer("Описание задачи не должно превышать 500 символов")


def on_change_task_description_type_factory(text: str) -> str:
    if len(text) > 500:
        raise ValueError("Описание задачи не должно превышать 500 символов")
    return text


# --- DEADLINE ---
async def on_change_task_deadline_success(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, deadline: datetime
) -> None:
    tasks_logger.info(f"Task deadline changed: {message.text}")
    db_session: Session = dialog_manager.middleware_data["db_session"]
    task_id = dialog_manager.dialog_data["selected_task_id"]
    db_current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    db_current_task.deadline = deadline
    db_session.commit()
    await dialog_manager.switch_to(TasksStates.TASK_DETAILS)


async def on_change_task_deadline_error(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError,
) -> None:
    tasks_logger.error(f"Error changing task deadline: {message.text}")
    await message.answer("Некорректный формат даты. Используйте ГГГГ-ММ-ДД ЧЧ:ММ:CC")


def on_change_task_deadline_type_factory(text: str) -> str:
    try:
        val = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        return val
    except Exception as e:
        tasks_logger.error(f"Invalid deadline format: {text}, {e}")
        raise ValueError("Некорректный формат даты. Используйте ГГГГ-ММ-ДД ЧЧ:ММ:CC")
    

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
    error: ValueError,
) -> None:
    tasks_logger.error(f"Error changing task status: {message.text}")
    await message.answer(
        "Некорректный статус. Используйте один из: "
        + ", ".join([s.value for s in TaskStatus])
    )


def on_change_task_status_type_factory(text: str) -> str:
    if text not in [s.value for s in TaskStatus]:
        raise ValueError("Некорректный статус")
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


# Обработчики multiselect виджетов
async def on_events_selection_changed(
    callback: CallbackQuery, widget: Multiselect, manager: DialogManager, *_
) -> None:
    """Обработчик изменения выбора событий"""
    db_session: Session = manager.middleware_data["db_session"]
    task_id = manager.dialog_data["selected_task_id"]
    
    # Получаем текущую задачу
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not current_task:
        await callback.answer("Ошибка: задача не найдена", show_alert=True)
        return
    
    # Получаем выбранные события
    selected_event_ids = widget.get_checked()
    
    # Очищаем текущие связи
    current_task.events.clear()
    
    # Добавляем новые связи
    if selected_event_ids:
        selected_events = (
            db_session.query(DbEvent)
            .filter(DbEvent.id.in_(selected_event_ids))
            .all()
        )
        current_task.events.extend(selected_events)
    
    db_session.commit()
    tasks_logger.info(f"Updated events for task {task_id}: {selected_event_ids}")
    await callback.answer("Связанные события обновлены")


async def on_notes_selection_changed(
    callback: CallbackQuery, widget: Multiselect, manager: DialogManager, *_
) -> None:
    """Обработчик изменения выбора заметок"""
    db_session: Session = manager.middleware_data["db_session"]
    task_id = manager.dialog_data["selected_task_id"]
    
    # Получаем текущую задачу
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not current_task:
        await callback.answer("Ошибка: задача не найдена", show_alert=True)
        return
    
    # Получаем выбранные заметки
    selected_note_ids = widget.get_checked()
    
    # Очищаем текущие связи
    current_task.notes.clear()
    
    # Добавляем новые связи
    if selected_note_ids:
        selected_notes = (
            db_session.query(DbNote)
            .filter(DbNote.id.in_(selected_note_ids))
            .all()
        )
        current_task.notes.extend(selected_notes)
    
    db_session.commit()
    tasks_logger.info(f"Updated notes for task {task_id}: {selected_note_ids}")
    await callback.answer("Связанные заметки обновлены")


async def on_goals_selection_changed(
    callback: CallbackQuery, widget: Multiselect, manager: DialogManager, *_
) -> None:
    """Обработчик изменения выбора целей"""
    db_session: Session = manager.middleware_data["db_session"]
    task_id = manager.dialog_data["selected_task_id"]
    
    # Получаем текущую задачу
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not current_task:
        await callback.answer("Ошибка: задача не найдена", show_alert=True)
        return
    
    # Получаем выбранные цели
    selected_goal_ids = widget.get_checked()
    
    # Очищаем текущие связи
    current_task.goals.clear()
    
    # Добавляем новые связи
    if selected_goal_ids:
        selected_goals = (
            db_session.query(DbGoal)
            .filter(DbGoal.id.in_(selected_goal_ids))
            .all()
        )
        current_task.goals.extend(selected_goals)
    
    db_session.commit()
    tasks_logger.info(f"Updated goals for task {task_id}: {selected_goal_ids}")
    await callback.answer("Связанные цели обновлены")


async def on_ideas_selection_changed(
    callback: CallbackQuery, widget: Multiselect, manager: DialogManager, *_
) -> None:
    """Обработчик изменения выбора идей"""
    db_session: Session = manager.middleware_data["db_session"]
    task_id = manager.dialog_data["selected_task_id"]
    
    # Получаем текущую задачу
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not current_task:
        await callback.answer("Ошибка: задача не найдена", show_alert=True)
        return
    
    # Получаем выбранные идеи
    selected_idea_ids = widget.get_checked()
    
    # Очищаем текущие связи
    current_task.ideas.clear()
    
    # Добавляем новые связи
    if selected_idea_ids:
        selected_ideas = (
            db_session.query(DbIdea)
            .filter(DbIdea.id.in_(selected_idea_ids))
            .all()
        )
        current_task.ideas.extend(selected_ideas)
    
    db_session.commit()
    tasks_logger.info(f"Updated ideas for task {task_id}: {selected_idea_ids}")
    await callback.answer("Связанные идеи обновлены")


async def on_tags_selection_changed(
    callback: CallbackQuery, widget: Multiselect, manager: DialogManager, *_
) -> None:
    """Обработчик изменения выбора тегов"""
    db_session: Session = manager.middleware_data["db_session"]
    task_id = manager.dialog_data["selected_task_id"]
    
    # Получаем текущую задачу
    current_task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not current_task:
        await callback.answer("Ошибка: задача не найдена", show_alert=True)
        return
    
    # Получаем выбранные теги
    selected_tag_ids = widget.get_checked()
    
    # Очищаем текущие связи
    current_task.tags.clear()
    
    # Добавляем новые связи
    if selected_tag_ids:
        selected_tags = (
            db_session.query(DbTag)
            .filter(DbTag.id.in_(selected_tag_ids))
            .all()
        )
        current_task.tags.extend(selected_tags)
    
    db_session.commit()
    tasks_logger.info(f"Updated tags for task {task_id}: {selected_tag_ids}")
    await callback.answer("Связанные теги обновлены")


async def on_add_subtask_button(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager
) -> None:
    """Переход к добавлению новой подзадачи"""
    await manager.switch_to(TasksStates.ADD_SUBTASK)


# Обработчики для текстовых полей подзадач
async def on_add_subtask_success(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str
) -> None:
    """Успешное добавление новой подзадачи"""
    db_session: Session = dialog_manager.middleware_data["db_session"]
    task_id = dialog_manager.dialog_data["selected_task_id"]
    
    # Создаем новую подзадачу
    new_subtask = DbSubtask(
        name=text,
        task_id=task_id,
        is_done=False,
        is_deleted=False
    )
    
    db_session.add(new_subtask)
    db_session.commit()
    
    tasks_logger.info(f"Added new subtask: {text} for task {task_id}")
    await dialog_manager.switch_to(TasksStates.SUBTASKS_LIST)


async def on_add_subtask_error(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError,
) -> None:
    """Ошибка при добавлении подзадачи"""
    tasks_logger.error(f"Error adding subtask: {message.text}")
    await message.answer("Название подзадачи не должно превышать 100 символов")


def on_add_subtask_type_factory(text: str) -> str:
    """Валидация названия подзадачи"""
    if len(text) > 100:
        raise ValueError("Название подзадачи не должно превышать 100 символов")
    return text


# --- SUBTASK NAME ---
async def on_change_subtask_name_success(
    message: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str
) -> None:
    tasks_logger.info(f"Subtask name changed: {message.text}")
    db_session: Session = dialog_manager.middleware_data["db_session"]
    subtask_id = dialog_manager.dialog_data["selected_subtask_id"]
    db_current_subtask = db_session.query(DbSubtask).filter(DbSubtask.id == subtask_id).first()
    db_current_subtask.name = text
    db_session.commit()
    await dialog_manager.switch_to(TasksStates.SUBTASK_DETAILS)


async def on_change_subtask_name_error(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError,
) -> None:
    tasks_logger.error(f"Error changing subtask name: {message.text}")
    await message.answer("Название подзадачи не должно превышать 100 символов")


def on_change_subtask_name_type_factory(text: str) -> str:
    if len(text) > 100:
        raise ValueError("Название подзадачи не должно превышать 100 символов")
    return text





# --- SUBTASK STATUS TOGGLE ---
async def on_subtask_status_toggle(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager
) -> None:
    """Переключение статуса выполнения подзадачи"""
    db_session: Session = manager.middleware_data["db_session"]
    subtask_id = manager.dialog_data["selected_subtask_id"]
    
    subtask = db_session.query(DbSubtask).filter(DbSubtask.id == subtask_id).first()
    if not subtask:
        await callback.answer("Ошибка: подзадача не найдена", show_alert=True)
        return
    
    subtask.is_done = not subtask.is_done
    db_session.commit()
    
    status_text = "выполнена" if subtask.is_done else "не выполнена"
    tasks_logger.info(f"Toggled subtask {subtask_id} status to {subtask.is_done}")
    await callback.answer(f"Подзадача теперь {status_text}")


# --- SUBTASK DELETE ---
async def on_delete_subtask_confirm(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager
) -> None:
    """Подтверждение удаления подзадачи"""
    db_session: Session = manager.middleware_data["db_session"]
    subtask_id = manager.dialog_data["selected_subtask_id"]
    
    subtask = db_session.query(DbSubtask).filter(DbSubtask.id == subtask_id).first()
    if not subtask:
        await callback.answer("Ошибка: подзадача не найдена", show_alert=True)
        return
    
    subtask.is_deleted = True
    db_session.commit()
    
    tasks_logger.info(f"Deleted subtask {subtask_id}")
    await manager.switch_to(TasksStates.SUBTASKS_LIST)
    await callback.answer("Подзадача удалена")


# Обработчик удаления задачи
async def on_delete_task_confirm(
    callback: CallbackQuery, widget: ManagedWidget, manager: DialogManager
) -> None:
    """Подтверждение удаления задачи"""
    db_session: Session = manager.middleware_data["db_session"]
    task_id = manager.dialog_data["selected_task_id"]
    
    # Помечаем задачу как удаленную
    task = db_session.query(DbTask).filter(DbTask.id == task_id).first()
    if not task:
        await callback.answer("Ошибка: задача не найдена", show_alert=True)
        return
    
    task.is_deleted = True
    db_session.commit()
    
    tasks_logger.info(f"Deleted task {task_id}")
    await manager.switch_to(TasksStates.TASKS_LIST)
    await callback.answer("Задача удалена")


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
                Const("🧩 Подзадачи"),
                id="manage_subtasks",
                state=TasksStates.SUBTASKS_LIST,
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
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_description", state=TasksStates.TASK_DETAILS),
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
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_deadline", state=TasksStates.TASK_DETAILS),
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
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_status", state=TasksStates.TASK_DETAILS),
        state=TasksStates.CHANGE_STATUS,
        getter=get_current_task_data,
    ),
    # --- EVENTS ---
    Window(
        Const("🔗 Управление связанными событиями"),
        Format("📅 Задача: {current_task.name}"),
        Const("Выберите события для связывания с задачей:"),
        ScrollingGroup(
            Multiselect(
                Format("☑️ {item.name}"),
                Format("☐ {item.name}"),
                id="task_select_events",
                item_id_getter=lambda event: event.id,
                items="all_events",
                on_state_changed=on_events_selection_changed,
            ),
            id="task_events_scroll",
            width=1,
            height=8,
            when="all_events",
        ),
        Const("У вас пока нет событий", when=~F["all_events"]),
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_events", state=TasksStates.TASK_DETAILS),
        state=TasksStates.CHANGE_EVENTS,
        getter=get_events_data,
    ),
    # --- NOTES ---
    Window(
        Const("🔗 Управление связанными заметками"),
        Format("🗒️ Задача: {current_task.name}"),
        Const("Выберите заметки для связывания с задачей:"),
        ScrollingGroup(
            Multiselect(
                Format("☑️ {item.name}"),
                Format("☐ {item.name}"),
                id="select_notes",
                item_id_getter=lambda note: note.id,
                items="all_notes",
                on_state_changed=on_notes_selection_changed,
            ),
            id="notes_scroll",
            width=1,
            height=8,
            when="all_notes",
        ),
        Const("У вас пока нет заметок", when=~F["all_notes"]),
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_notes", state=TasksStates.TASK_DETAILS),
        state=TasksStates.CHANGE_NOTES,
        getter=get_notes_data,
    ),
    # --- GOALS ---
    Window(
        Const("🔗 Управление связанными целями"),
        Format("🎯 Задача: {current_task.name}"),
        Const("Выберите цели для связывания с задачей:"),
        ScrollingGroup(
            Multiselect(
                Format("☑️ {item.name}"),
                Format("☐ {item.name}"),
                id="select_goals",
                item_id_getter=lambda goal: goal.id,
                items="all_goals",
                on_state_changed=on_goals_selection_changed,
            ),
            id="goals_scroll",
            width=1,
            height=8,
            when="all_goals",
        ),
        Const("У вас пока нет целей", when=~F["all_goals"]),
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_goals", state=TasksStates.TASK_DETAILS),
        state=TasksStates.CHANGE_GOALS,
        getter=get_goals_data,
    ),
    # --- IDEAS ---
    Window(
        Const("🔗 Управление связанными идеями"),
        Format("💡 Задача: {current_task.name}"),
        Const("Выберите идеи для связывания с задачей:"),
        ScrollingGroup(
            Multiselect(
                Format("☑️ {item.name}"),
                Format("☐ {item.name}"),
                id="select_ideas",
                item_id_getter=lambda idea: idea.id,
                items="all_ideas",
                on_state_changed=on_ideas_selection_changed,
            ),
            id="ideas_scroll",
            width=1,
            height=8,
            when="all_ideas",
        ),
        Const("У вас пока нет идей", when=~F["all_ideas"]),
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_ideas", state=TasksStates.TASK_DETAILS),
        state=TasksStates.CHANGE_IDEAS,
        getter=get_ideas_data,
    ),
    # --- TAGS (обновленный для multiselect) ---
    Window(
        Const("🏷️ Управление связанными тегами"),
        Format("🏷️ Задача: {current_task.name}"),
        Const("Выберите теги для связывания с задачей:"),
        ScrollingGroup(
            Multiselect(
                Format("☑️ {item.name}"),
                Format("☐ {item.name}"),
                id="select_tags",
                item_id_getter=lambda tag: tag.id,
                items="all_tags",
                on_state_changed=on_tags_selection_changed,
            ),
            id="tags_scroll",
            width=1,
            height=8,
            when="all_tags",
        ),
        Const("У вас пока нет тегов", when=~F["all_tags"]),
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_tags", state=TasksStates.TASK_DETAILS),
        state=TasksStates.CHANGE_TAGS,
        getter=get_tags_data,
    ),
    # --- SUBTASKS LIST ---
    Window(
        Const("🧩 Подзадачи задачи:"),
        Format("📋 Задача: {current_task.name}"),
        ScrollingGroup(
            Select(
                Format("{item[info]}"),
                id="select_subtask",
                item_id_getter=lambda x: x["id"],
                items="subtasks_info",
                on_click=on_subtask_selected,
            ),
            #hide_on_single_page=True,
            id="scroll_subtasks",
            height=8,
            width=1,
        ),
        Button(Format("{mode}"), id="select_subtask_mode", on_click=on_subtask_mode_select),
        Button(Const("➕ Добавить подзадачу"), id="add_subtask", on_click=on_add_subtask_button),
        SwitchTo(Const("🔙 Назад"), id="back_to_task_details_from_subtasks", state=TasksStates.TASK_DETAILS),
        state=TasksStates.SUBTASKS_LIST,
        getter=get_subtasks_list_data,
    ),
    # --- SUBTASK DETAILS ---
    Window(
        Format("🔹 {current_subtask.name}"),
        Format("📝 Статус: {done_info}"),
        Group(
            SwitchTo(
                Const("✏️ Имя"), id="change_subtask_name", state=TasksStates.CHANGE_SUBTASK_NAME
            ),
            Button(
                Const("🔄 Переключить статус"),
                id="toggle_subtask_status",
                on_click=on_subtask_status_toggle,
            ),
            SwitchTo(
                Const("🗑️ Удалить"), id="delete_subtask", state=TasksStates.DELETE_SUBTASK
            ),
            width=2,
        ),
        SwitchTo(Const("🔙 Назад"), id="back_to_subtasks", state=TasksStates.SUBTASKS_LIST),
        state=TasksStates.SUBTASK_DETAILS,
        getter=get_current_subtask_data,
    ),
    # --- ADD SUBTASK ---
    Window(
        Const("➕ Добавление новой подзадачи"),
        Format("📋 Задача: {current_task.name}"),
        Const("⚠️ Название подзадачи не должно превышать 100 символов"),
        Const("📝 Введите название подзадачи:"),
        TextInput(
            id="add_subtask_input",
            type_factory=on_add_subtask_type_factory,
            on_success=on_add_subtask_success,
            on_error=on_add_subtask_error,
        ),
        SwitchTo(Const("🔙 Назад"), id="back_to_subtasks_from_add_subtask", state=TasksStates.SUBTASKS_LIST),
        state=TasksStates.ADD_SUBTASK,
        getter=get_current_task_data,
    ),
    # --- CHANGE SUBTASK NAME ---
    Window(
        Const("✏️ Меню изменения названия подзадачи"),
        Format("🏷️ Текущее название: {current_subtask.name}"),
        Const("⚠️ Название подзадачи не должно превышать 100 символов"),
        Const("📝 Введите новое название подзадачи:"),
        TextInput(
            id="change_subtask_name_input",
            type_factory=on_change_subtask_name_type_factory,
            on_success=on_change_subtask_name_success,
            on_error=on_change_subtask_name_error,
        ),
        SwitchTo(Const("🔙 Назад"), id="back_to_subtask_details", state=TasksStates.SUBTASK_DETAILS),
        state=TasksStates.CHANGE_SUBTASK_NAME,
        getter=get_current_subtask_data,
    ),

    # --- DELETE SUBTASK ---
    Window(
        Const("🗑️ Удаление подзадачи"),
        Format("⚠️ Вы действительно хотите удалить подзадачу:\n🔹 {current_subtask.name}"),
        Const("❗ Это действие нельзя отменить!"),
        Group(
            Button(
                Const("✅ Да, удалить"),
                id="confirm_delete_subtask",
                on_click=on_delete_subtask_confirm,
            ),
            SwitchTo(Const("❌ Отмена"), id="cancel_delete_subtask", state=TasksStates.SUBTASK_DETAILS),
            width=2,
        ),
        state=TasksStates.DELETE_SUBTASK,
        getter=get_current_subtask_data,
    ),
    # --- DELETE TASK ---
    Window(
        Const("🗑️ Удаление задачи"),
        Format("⚠️ Вы действительно хотите удалить задачу:\n🔹 {current_task.name}"),
        Const("❗ Это действие нельзя отменить!"),
        Group(
            Button(
                Const("✅ Да, удалить"),
                id="confirm_delete",
                on_click=on_delete_task_confirm,
            ),
            SwitchTo(Const("❌ Отмена"), id="cancel_delete", state=TasksStates.TASK_DETAILS),
            width=2,
        ),
        state=TasksStates.DELETE_TASK,
        getter=get_current_task_data,
    ),
)
