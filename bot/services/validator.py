from typing import List, Optional, Tuple
from models.answers import (
    AnswerModel,
    ToEditModel,
    ToDeleteModel,
    TaskEditModel,
    SubtaskEditModel,
    EventEditModel,
    GoalEditModel,
    IdeaEditModel,
    NoteEditModel,
    TagEditModel,
    DeleteIdModel,
    ResponseModel,
    StatusEnum,
    ResultEnum,
)
from database import models as db_models
from sqlalchemy.orm import Session
from maps.answers_info import answer_to_db

# Определяем updateable и deleteable объекты на основе моделей из answers.py
updateable_objects: List[str] = list(ToEditModel.model_fields.keys())
deleteable_objects: List[str] = list(ToDeleteModel.model_fields.keys())

# Типы для edit-объектов
EditModelType = TaskEditModel | SubtaskEditModel | EventEditModel | GoalEditModel | IdeaEditModel | NoteEditModel | TagEditModel
DeleteModelType = DeleteIdModel

def validate_edit(
    resp: ResponseModel,
    session: Session,
    errors: List[str]
) -> None:
    """
    Валидирует изменение объектов.
    """
    for attr in updateable_objects:
        items: Optional[List[EditModelType]] = getattr(resp.to_edit, attr, None)
        if not items:
            continue
        db_model: type = answer_to_db[attr]["db"]
        for item in items:
            db_obj = session.get(db_model, item.id)
            if not db_obj:
                errors.append(f"{attr[:-1].capitalize()} with id={item.id} does not exist")

def validate_delete(
    resp: ResponseModel,
    session: Session,
    errors: List[str]
) -> None:
    """
    Валидирует удаление объектов.
    """
    for attr in deleteable_objects:
        items: Optional[List[DeleteModelType]] = getattr(resp.to_delete, attr, None)
        if not items:
            continue
        db_model: type = answer_to_db[attr]["db"]
        for item in items:
            db_obj = session.get(db_model, item.id)
            if not db_obj:
                errors.append(f"{attr[:-1].capitalize()} with id={item.id} does not exist")

def validate_subtasks(
    resp: ResponseModel,
    session: Session,
    errors: List[str]
) -> None:
    """
    Валидирует подзадачи.
    """
    for item in resp.to_add.subtasks:
        db_obj = session.get(db_models.Task, item.task_id)
        if not db_obj:
            errors.append(f"Can't add subtask to non-existent task with id={item.task_id}")


def validate(
    answer: str,
    session: Session
) -> Tuple[bool, List[str], Optional[AnswerModel]]:
    """
    Валидирует ответ LLM. Использует валидатор pydantic и проверяет на наличие id объектов в базе данных.
    
    Возвращает tuple(is_valid: bool, errors: List[str], answer_model: Optional[AnswerModel])
    """
    errors: List[str] = []
    answer_model: Optional[AnswerModel] = None
    try:
        # strict mode
        answer_model = AnswerModel.model_validate_json(answer.strip("```json\n").strip("```"))
    except Exception as e:
        errors.append(f"JSON validation error: {e}")
        return False, errors, None

    resp: Optional[ResponseModel] = getattr(answer_model, "response", None)
    if not resp:
        return True, [answer_model.error], answer_model

    if getattr(resp, "to_add", None) and getattr(resp.to_add, "subtasks", None):
        validate_subtasks(resp, session, errors)

    if getattr(resp, "to_edit", None):
        validate_edit(resp, session, errors)

    if getattr(resp, "to_delete", None):
        validate_delete(resp, session, errors)

    is_valid: bool = not errors
    return is_valid, errors, answer_model