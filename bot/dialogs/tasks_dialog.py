from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, Column, ScrollingGroup, Select, Cancel, Back
from aiogram_dialog.widgets.input import MessageInput
from sqlalchemy.orm import Session
from database.models import Task, TaskStatus, User
from datetime import datetime
from aiogram.fsm.state import State, StatesGroup
from utils.logger import tasks_logger
from pprint import pprint
# States
class TasksStates(StatesGroup):
    main = State()
    task_details = State()
    add_task = State()
    edit_name = State()
    edit_description = State()
    edit_status = State()
    edit_deadline = State()
    edit_tag = State()
    delete_task = State()

# Data getters
async def get_tasks_data(**kwargs):
    """Get tasks for the current user"""
    db_session: Session = kwargs["db_session"]
    db_user: User = kwargs["db_user"]
    
    tasks = db_session.query(Task).filter(
        Task.user_id == db_user.id,
        Task.is_deleted == False
    ).order_by(Task.created.desc()).all()
    
    tasks_logger.info(f"Retrieved {len(tasks)} tasks for user {db_user.tg_id}")
    return {"tasks": tasks}

async def get_current_task_data(dialog_manager: DialogManager, **kwargs):
    """Get current task data for details window"""
    pprint(kwargs)
    db_session: Session = kwargs["db_session"]
    # Get task_id from dialog_data
    task_id = dialog_manager.dialog_data.get("selected_task_id")
    if not task_id:
        tasks_logger.warning("No selected_task_id in dialog_data")
        return {"current_task": None}
    
    task = db_session.query(Task).filter(Task.id == task_id).first()
    if not task:
        tasks_logger.warning(f"Task with id {task_id} not found")
        return {"current_task": None}
    
    tasks_logger.info(f"Retrieved task {task_id} for details window")
    return {"current_task": task}

# Main tasks list window
class TasksListWindow(Window):
    def __init__(self):
        super().__init__(
            Const("📋 Ваши задачи:"),
            ScrollingGroup(
                Select(
                    Format("🔹 {item.name} ({item.status.value})"),
                    id="task_select",
                    item_id_getter=lambda x: x.id,
                    items="tasks",
                    on_click=self.on_task_selected
                ),
                id="tasks_scroll",
                width=1,
                height=8
            ),
            Button(Const("➕ Добавить задачу"), id="add_task", on_click=self.on_add_task),
            Cancel(Const("🔙 Закрыть")),
            state=TasksStates.main,
            getter=get_tasks_data
        )
    
    async def on_task_selected(self, callback, widget, manager: DialogManager, item_id: int):
        tasks_logger.info(f"Task selected: {item_id}")
        manager.dialog_data["selected_task_id"] = item_id
        await manager.switch_to(TasksStates.task_details)
    
    async def on_add_task(self, callback, widget, manager: DialogManager):
        tasks_logger.info("Add task button clicked")
        await manager.switch_to(TasksStates.add_task)

# Task details window
class TaskDetailsWindow(Window):
    def __init__(self):
        super().__init__(
            Const("📝 Детали задачи"),
            Format("📝 Название: {current_task.name if current_task else 'Задача не найдена'}"),
            Format("📄 Описание: {current_task.description or 'Не указано' if current_task else 'Не указано'}"),
            Format("📊 Статус: {current_task.status.value if current_task else 'Не указан'}"),
            Format("⏰ Дедлайн: {current_task.deadline.strftime('%Y-%m-%d %H:%M') if current_task and current_task.deadline else 'Не указан'}"),
            Format("🏷️ Тег: {current_task.tag or 'Не указан' if current_task else 'Не указан'}"),
            Row(
                Button(Const("✏️ Изменить название"), id="edit_name", on_click=self.on_edit_name),
                Button(Const("📝 Изменить описание"), id="edit_description", on_click=self.on_edit_description)
            ),
            Row(
                Button(Const("📊 Изменить статус"), id="edit_status", on_click=self.on_edit_status),
                Button(Const("⏰ Изменить дедлайн"), id="edit_deadline", on_click=self.on_edit_deadline)
            ),
            Row(
                Button(Const("🏷️ Изменить тег"), id="edit_tag", on_click=self.on_edit_tag),
                Button(Const("🗑️ Удалить"), id="delete_task", on_click=self.on_delete_task)
            ),
            Back(Const("🔙 Назад к списку")),
            state=TasksStates.task_details,
            getter=get_current_task_data
        )
    
    async def on_edit_name(self, callback, widget, manager: DialogManager):
        await manager.switch_to(TasksStates.edit_name)
    
    async def on_edit_description(self, callback, widget, manager: DialogManager):
        await manager.switch_to(TasksStates.edit_description)
    
    async def on_edit_status(self, callback, widget, manager: DialogManager):
        await manager.switch_to(TasksStates.edit_status)
    
    async def on_edit_deadline(self, callback, widget, manager: DialogManager):
        await manager.switch_to(TasksStates.edit_deadline)
    
    async def on_edit_tag(self, callback, widget, manager: DialogManager):
        await manager.switch_to(TasksStates.edit_tag)
    
    async def on_delete_task(self, callback, widget, manager: DialogManager):
        await manager.switch_to(TasksStates.delete_task)

# Add task window
class AddTaskWindow(Window):
    def __init__(self):
        super().__init__(
            Const("➕ Создание новой задачи"),
            Const("Введите название задачи:"),
            MessageInput(self.on_name_input),
            Cancel(Const("🔙 Отмена")),
            state=TasksStates.add_task
        )
    
    async def on_name_input(self, message, dialog_manager: DialogManager):
        name = message.text
        if len(name) > 100:
            await message.answer("❌ Название слишком длинное (максимум 100 символов)")
            return
        
        # Create new task
        db_session: Session = dialog_manager.middleware_data["db_session"]
        db_user: User = dialog_manager.middleware_data["db_user"]
        
        new_task = Task(
            name=name,
            description="",
            status=TaskStatus.NEW,
            user_id=db_user.id
        )
        
        db_session.add(new_task)
        db_session.commit()
        
        tasks_logger.info(f"Created new task '{name}' for user {db_user.tg_id}")
        await message.answer(f"✅ Задача '{name}' создана!")
        await dialog_manager.done()

# Edit task name window
class EditTaskNameWindow(Window):
    def __init__(self):
        super().__init__(
            Const("✏️ Изменение названия задачи"),
            Const("Введите новое название:"),
            MessageInput(self.on_name_input),
            Cancel(Const("🔙 Отмена")),
            state=TasksStates.edit_name
        )
    
    async def on_name_input(self, message, dialog_manager: DialogManager):
        name = message.text
        if len(name) > 100:
            await message.answer("❌ Название слишком длинное (максимум 100 символов)")
            return
        
        # Update task name
        db_session: Session = dialog_manager.middleware_data["db_session"]
        task_id = dialog_manager.dialog_data["selected_task_id"]
        
        task = db_session.query(Task).filter(Task.id == task_id).first()
        if task:
            task.name = name
            task.updated = datetime.now()
            db_session.commit()
            tasks_logger.info(f"Updated task name to '{name}' for task {task_id}")
            await message.answer(f"✅ Название изменено на '{name}'!")
        
        await dialog_manager.switch_to(TasksStates.task_details)

# Edit task description window
class EditTaskDescriptionWindow(Window):
    def __init__(self):
        super().__init__(
            Const("📝 Изменение описания задачи"),
            Const("Введите новое описание:"),
            MessageInput(self.on_description_input),
            Cancel(Const("🔙 Отмена")),
            state=TasksStates.edit_description
        )
    
    async def on_description_input(self, message, dialog_manager: DialogManager):
        description = message.text
        
        # Update task description
        db_session: Session = dialog_manager.middleware_data["db_session"]
        task_id = dialog_manager.dialog_data["selected_task_id"]
        
        task = db_session.query(Task).filter(Task.id == task_id).first()
        if task:
            task.description = description
            task.updated = datetime.now()
            db_session.commit()
            tasks_logger.info(f"Updated task description for task {task_id}")
            await message.answer("✅ Описание обновлено!")
        
        await dialog_manager.switch_to(TasksStates.task_details)

# Edit task status window
class EditTaskStatusWindow(Window):
    def __init__(self):
        super().__init__(
            Const("📊 Изменение статуса задачи"),
            Const("Выберите новый статус:"),
            Column(
                Button(Const("🆕 Новый"), id="status_new", on_click=self.on_status_change),
                Button(Const("🔄 В работе"), id="status_in_progress", on_click=self.on_status_change),
                Button(Const("✅ Завершено"), id="status_completed", on_click=self.on_status_change)
            ),
            Cancel(Const("🔙 Отмена")),
            state=TasksStates.edit_status
        )
    
    async def on_status_change(self, callback, widget, manager: DialogManager):
        status_map = {
            "status_new": TaskStatus.NEW,
            "status_in_progress": TaskStatus.IN_PROGRESS,
            "status_completed": TaskStatus.COMPLETED
        }
        
        new_status = status_map[widget.widget_id]
        db_session: Session = manager.middleware_data["db_session"]
        task_id = manager.dialog_data["selected_task_id"]
        
        task = db_session.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = new_status
            task.updated = datetime.now()
            db_session.commit()
            tasks_logger.info(f"Updated task status to {new_status.value} for task {task_id}")
            await callback.message.answer(f"✅ Статус изменен на '{new_status.value}'!")
        
        await manager.switch_to(TasksStates.task_details)

# Edit task deadline window
class EditTaskDeadlineWindow(Window):
    def __init__(self):
        super().__init__(
            Const("⏰ Изменение дедлайна задачи"),
            Const("Введите дедлайн в формате YYYY-MM-DD HH:MM или 'отмена' для удаления:"),
            MessageInput(self.on_deadline_input),
            Cancel(Const("🔙 Отмена")),
            state=TasksStates.edit_deadline
        )
    
    async def on_deadline_input(self, message, dialog_manager: DialogManager):
        deadline_text = message.text.strip()
        
        if deadline_text.lower() == "отмена":
            # Remove deadline
            db_session: Session = dialog_manager.middleware_data["db_session"]
            task_id = dialog_manager.dialog_data["selected_task_id"]
            
            task = db_session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.deadline = None
                task.updated = datetime.now()
                db_session.commit()
                tasks_logger.info(f"Removed deadline for task {task_id}")
                await message.answer("✅ Дедлайн удален!")
        else:
            try:
                # Parse deadline
                deadline = datetime.strptime(deadline_text, "%Y-%m-%d %H:%M")
                
                db_session: Session = dialog_manager.middleware_data["db_session"]
                task_id = dialog_manager.dialog_data["selected_task_id"]
                
                task = db_session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.deadline = deadline
                    task.updated = datetime.now()
                    db_session.commit()
                    tasks_logger.info(f"Updated deadline to {deadline} for task {task_id}")
                    await message.answer(f"✅ Дедлайн установлен на {deadline.strftime('%Y-%m-%d %H:%M')}!")
            except ValueError:
                await message.answer("❌ Неверный формат даты. Используйте YYYY-MM-DD HH:MM")
                return
        
        await dialog_manager.switch_to(TasksStates.task_details)

# Edit task tag window
class EditTaskTagWindow(Window):
    def __init__(self):
        super().__init__(
            Const("🏷️ Изменение тега задачи"),
            Const("Введите новый тег или 'отмена' для удаления:"),
            MessageInput(self.on_tag_input),
            Cancel(Const("🔙 Отмена")),
            state=TasksStates.edit_tag
        )
    
    async def on_tag_input(self, message, dialog_manager: DialogManager):
        tag = message.text.strip()
        
        if tag.lower() == "отмена":
            # Remove tag
            db_session: Session = dialog_manager.middleware_data["db_session"]
            task_id = dialog_manager.dialog_data["selected_task_id"]
            
            task = db_session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.tag = None
                task.updated = datetime.now()
                db_session.commit()
                tasks_logger.info(f"Removed tag for task {task_id}")
                await message.answer("✅ Тег удален!")
        else:
            if len(tag) > 50:
                await message.answer("❌ Тег слишком длинный (максимум 50 символов)")
                return
            
            db_session: Session = dialog_manager.middleware_data["db_session"]
            task_id = dialog_manager.dialog_data["selected_task_id"]
            
            task = db_session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.tag = tag
                task.updated = datetime.now()
                db_session.commit()
                tasks_logger.info(f"Updated tag to '{tag}' for task {task_id}")
                await message.answer(f"✅ Тег изменен на '{tag}'!")
        
        await dialog_manager.switch_to(TasksStates.task_details)

# Delete task confirmation window
class DeleteTaskWindow(Window):
    def __init__(self):
        super().__init__(
            Const("🗑️ Удаление задачи"),
            Const("Вы уверены, что хотите удалить эту задачу?"),
            Row(
                Button(Const("✅ Да, удалить"), id="confirm_delete", on_click=self.on_confirm_delete),
                Button(Const("❌ Отмена"), id="cancel")
            ),
            state=TasksStates.delete_task
        )
    
    async def on_confirm_delete(self, callback, widget, manager: DialogManager):
        db_session: Session = manager.middleware_data["db_session"]
        task_id = manager.dialog_data["selected_task_id"]
        
        task = db_session.query(Task).filter(Task.id == task_id).first()
        if task:
            task.is_deleted = True
            task.updated = datetime.now()
            db_session.commit()
            tasks_logger.info(f"Deleted task {task_id}")
            await callback.message.answer("✅ Задача удалена!")
        
        await manager.switch_to(TasksStates.main)

# Dialog setup
class TasksDialog(Dialog):
    def __init__(self):
        super().__init__(
            TasksListWindow(),
            TaskDetailsWindow(),
            AddTaskWindow(),
            EditTaskNameWindow(),
            EditTaskDescriptionWindow(),
            EditTaskStatusWindow(),
            EditTaskDeadlineWindow(),
            EditTaskTagWindow(),
            DeleteTaskWindow()
        )

