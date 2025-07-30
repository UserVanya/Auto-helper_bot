from sqlalchemy.orm import Session
from database import models as db_models
from maps.answers_info import answer_to_db
from models.answers import ResponseModel 
from models.answers import ToAddModel, ToEditModel, ToDeleteModel

def execute(session: Session, resp: ResponseModel, user_id: int) -> tuple[list, list, list]:
    """
    Выполняет команды добавления, изменения и удаления объектов в базе данных.
    Возвращает словарь с результатами: added, updated, deleted.
    """
    added_items = []
    updated_items = []
    deleted_items = []
    
    if not resp:
        return added_items, updated_items, deleted_items
        
    if getattr(resp, "to_add", None):
        added_items = execute_add(session, resp.to_add, user_id)
        
    if getattr(resp, "to_edit", None):
        updated_items = execute_edit(session, resp.to_edit)
        
    if getattr(resp, "to_delete", None):
        deleted_items = execute_delete(session, resp.to_delete)
        
    session.commit()
    return added_items, updated_items, deleted_items

def execute_add(session: Session, to_add: ToAddModel, user_id: int) -> list:
    """
    Выполняет добавление объектов в базу данных с привязкой к пользователю.
    Возвращает список добавленных объектов.
    """
    added_items = []
    
    if getattr(to_add, "tasks", None):
        added_items.extend(_add_tasks_with_subtasks(session, to_add.tasks, user_id))
        
    if getattr(to_add, "subtasks", None):
        added_items.extend(_add_subtasks_for_existing_tasks(session, to_add.subtasks, user_id))
        
    for key in ["events", "goals", "ideas", "notes", "tags"]:
        items = getattr(to_add, key, None)
        if items:
            added_items.extend(_add_simple_items(session, key, items, user_id))
            
    return added_items

def _add_tasks_with_subtasks(session: Session, tasks, user_id: int) -> list:
    """
    Добавляет задачи с подзадачами, привязывая их к пользователю.
    """
    added_items = []
    
    for task in tasks:
        db_task = db_models.DbTask(
            name=task.name,
        description=getattr(task, "description", None),
        status=getattr(task, "status", None).value if getattr(task, "status", None) else None,
        deadline=getattr(task, "deadline", None),
        user_id=user_id  # Привязка к пользователю
        )
        session.add(db_task)
        session.flush()  # Получаем id задачи для подзадач
        
        added_items.append({
            'type': 'Task',
            'name': db_task.name,
            'id': db_task.id
        })
        
        # Добавляем подзадачи для этой задачи
        if getattr(task, "subtasks", None):
            for subtask in getattr(task, "subtasks", []):
                db_subtask = db_models.DbSubtask(
                    name=subtask.name,
                    deadline=getattr(subtask, "deadline", None),
                    task_id=db_task.id,
                )
                session.add(db_subtask)
                added_items.append({
                    'type': 'Subtask',
                    'name': db_subtask.name,
                    'id': db_subtask.id
                })
            
    return added_items

def _add_subtasks_for_existing_tasks(session: Session, subtasks, user_id: int) -> list:
    """
    Добавляет подзадачи к существующим задачам.
    """
    added_items = []
    
    for subtask in subtasks:
        db_subtask = db_models.DbSubtask(
            name=subtask.name,
            deadline=getattr(subtask, "deadline", None),
            task_id=subtask.id,  # id существующей задачи
            user_id=user_id  # Привязка к пользователю
        )
        session.add(db_subtask)
        added_items.append({
            'type': 'Subtask',
            'name': db_subtask.name,
            'id': db_subtask.id
        })
        
    return added_items

def _add_simple_items(session: Session, key: str, items, user_id: int) -> list:
    """
    Добавляет простые объекты (events, goals, ideas, notes, tags) с привязкой к пользователю.
    """
    added_items = []
    db_model = answer_to_db[key]["db"]
    
    for item in items:
        data = item.model_dump()
        # Преобразуем Enum в строку для status, если есть
        if "status" in data and hasattr(data["status"], "value"):
            data["status"] = data["status"].value
            
        # Добавляем user_id, если модель его поддерживает
        if hasattr(db_model, 'user_id'):
            data["user_id"] = user_id
            
        db_obj = db_model(**data)
        session.add(db_obj)
        session.flush()  # Получаем id объекта
        
        added_items.append({
            'type': db_model.__name__,
            'name': getattr(db_obj, 'name', str(db_obj.id)),
            'id': db_obj.id
        })
        
    return added_items

def execute_edit(session: Session, to_edit: ToEditModel) -> list:
    """
    Выполняет изменение существующих объектов в базе данных.
    Возвращает список изменённых объектов.
    """
    updated_items = []
    
    # Обновляем только те поля, которые присутствуют в запросе (не None)
    for key, info in answer_to_db.items():
        items = getattr(to_edit, key, None)
        if not items:
            continue
            
        db_model = info["db"]
        for item in items:
            db_obj = session.get(db_model, item.id)
            if not db_obj:
                continue
                
            # Обновляем только переданные поля
            for field, value in item.model_dump().items():
                if field == "id":
                    continue
                if value is not None:  # Обновляем только не-None значения
                    # Enum to str for status
                    if field == "status" and hasattr(value, "value"):
                        value = value.value
                    setattr(db_obj, field, value)
                    
            updated_items.append({
                'type': db_model.__name__,
                'name': getattr(db_obj, 'name', str(db_obj.id)),
                'id': db_obj.id
            })
            
    return updated_items

def execute_delete(session: Session, to_delete: ToDeleteModel) -> list:
    """
    Выполняет удаление объектов из базы данных (устанавливает is_deleted=True).
    Возвращает список удалённых объектов.
    """
    deleted_items = []
    
    for key, info in answer_to_db.items():
        items = getattr(to_delete, key, None)
        if not items:
            continue
            
        db_model = info["db"]
        for item in items:
            db_obj = session.get(db_model, item.id)
            if db_obj:
                if hasattr(db_obj, "is_deleted"):
                    db_obj.is_deleted = True
                else:
                    # Если модель не поддерживает soft delete, удаляем физически
                    session.delete(db_obj)
                    
                deleted_items.append({
                    'type': db_model.__name__,
                    'name': getattr(db_obj, 'name', str(db_obj.id)),
                    'id': db_obj.id
                })
                
    return deleted_items
