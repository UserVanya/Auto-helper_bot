from models import answers as answer_models
from database import models as db_models

# Маппинг для add/edit/delete моделей
answer_to_db = {
    "tasks": {"add": answer_models.TaskAddModel, "edit": answer_models.TaskEditModel, "db": db_models.DbTask},
    "subtasks": {"add": answer_models.SubtaskAddToExistingTaskModel, "edit": answer_models.SubtaskEditModel, "db": db_models.DbSubtask},
    "events": {"add": answer_models.EventAddModel, "edit": answer_models.EventEditModel, "db": db_models.DbEvent},
    "goals": {"add": answer_models.GoalAddModel, "edit": answer_models.GoalEditModel, "db": db_models.DbGoal},
    "ideas": {"add": answer_models.IdeaAddModel, "edit": answer_models.IdeaEditModel, "db": db_models.DbIdea},
    "notes": {"add": answer_models.NoteAddModel, "edit": answer_models.NoteEditModel, "db": db_models.DbNote},
    "tags": {"add": answer_models.TagAddModel, "edit": answer_models.TagEditModel, "db": db_models.DbTag},
}

delete_model_map = {
    "tasks": answer_models.DeleteIdModel,
    "subtasks": answer_models.DeleteIdModel,
    "events": answer_models.DeleteIdModel,
    "goals": answer_models.DeleteIdModel,
    "ideas": answer_models.DeleteIdModel,
    "notes": answer_models.DeleteIdModel,
    "tags": answer_models.DeleteIdModel,
}

# Enum maps
result_enum_values = [e.value for e in answer_models.ResultEnum]
status_enum_values = [e.value for e in answer_models.StatusEnum]

# Для быстрого поиска по типу
db_to_answer_add = {v["db"]: v["add"] for k, v in answer_to_db.items()}
db_to_answer_edit = {v["db"]: v["edit"] for k, v in answer_to_db.items()}
answer_add_to_db = {v["add"]: v["db"] for k, v in answer_to_db.items()}
answer_edit_to_db = {v["edit"]: v["db"] for k, v in answer_to_db.items()}
