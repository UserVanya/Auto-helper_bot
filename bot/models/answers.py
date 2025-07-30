from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum

class ResultEnum(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"

class StatusEnum(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

# --- Add Models ---

class SubtaskAddToFutureTaskModel(BaseModel):
    name: str = Field(...)
    order: int = Field(...)
    deadline: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class SubtaskAddToExistingTaskModel(BaseModel):
    task_id: int = Field(...)
    name: str = Field(...)
    order: int = Field(...)
    deadline: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class TaskAddModel(BaseModel):
    name: str = Field(...)
    description: Optional[str] = Field(default=None)
    status: Optional[StatusEnum] = Field(default=None)
    deadline: Optional[str] = Field(default=None)
    subtasks: Optional[List[SubtaskAddToFutureTaskModel]] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class EventAddModel(BaseModel):
    name: str = Field(...)
    description: Optional[str] = Field(default=None)
    start_time: Optional[str] = Field(default=None)
    end_time: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class GoalAddModel(BaseModel):
    name: str = Field(...)
    description: Optional[str] = Field(default=None)
    deadline: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class IdeaAddModel(BaseModel):
    name: str = Field(...)
    description: Optional[str] = Field(default=None)
    is_confirmed: Optional[bool] = Field(default=None)
    is_deleted: Optional[bool] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class NoteAddModel(BaseModel):
    name: str = Field(...)
    description: Optional[str] = Field(default=None)
    is_deleted: Optional[bool] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class TagAddModel(BaseModel):
    name: str = Field(...)
    model_config = ConfigDict(extra="forbid")

class ToAddModel(BaseModel):
    tasks: Optional[List[TaskAddModel]] = Field(default=None)
    subtasks: Optional[List[SubtaskAddToExistingTaskModel]] = Field(default=None)
    events: Optional[List[EventAddModel]] = Field(default=None)
    goals: Optional[List[GoalAddModel]] = Field(default=None)
    ideas: Optional[List[IdeaAddModel]] = Field(default=None)
    notes: Optional[List[NoteAddModel]] = Field(default=None)
    tags: Optional[List[TagAddModel]] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

# --- Edit Models ---

class TaskEditModel(BaseModel):
    id: int = Field(...)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    status: Optional[StatusEnum] = Field(default=None)
    deadline: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class SubtaskEditModel(BaseModel):
    id: int = Field(...)
    name: Optional[str] = Field(default=None)
    order: Optional[int] = Field(default=None)
    deadline: Optional[str] = Field(default=None)
    is_done: Optional[bool] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class EventEditModel(BaseModel):
    id: int = Field(...)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    start_time: Optional[str] = Field(default=None)
    end_time: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class GoalEditModel(BaseModel):
    id: int = Field(...)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    deadline: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class IdeaEditModel(BaseModel):
    id: int = Field(...)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    is_confirmed: Optional[bool] = Field(default=None)
    is_deleted: Optional[bool] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class NoteEditModel(BaseModel):
    id: int = Field(...)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    is_deleted: Optional[bool] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class TagEditModel(BaseModel):
    id: int = Field(...)
    name: Optional[str] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class ToEditModel(BaseModel):
    tasks: Optional[List[TaskEditModel]] = Field(default=None)
    subtasks: Optional[List[SubtaskEditModel]] = Field(default=None)
    events: Optional[List[EventEditModel]] = Field(default=None)
    goals: Optional[List[GoalEditModel]] = Field(default=None)
    ideas: Optional[List[IdeaEditModel]] = Field(default=None)
    notes: Optional[List[NoteEditModel]] = Field(default=None)
    tags: Optional[List[TagEditModel]] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

# --- Delete Model ---

class DeleteIdModel(BaseModel):
    id: int = Field(...)
    model_config = ConfigDict(extra="forbid")

class ToDeleteModel(BaseModel):
    tasks: Optional[List[DeleteIdModel]] = Field(default=None)
    events: Optional[List[DeleteIdModel]] = Field(default=None)
    goals: Optional[List[DeleteIdModel]] = Field(default=None)
    ideas: Optional[List[DeleteIdModel]] = Field(default=None)
    notes: Optional[List[DeleteIdModel]] = Field(default=None)
    tags: Optional[List[DeleteIdModel]] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

# --- Response/Answer ---

class ResponseModel(BaseModel):
    to_add: Optional[ToAddModel] = Field(default=None)
    to_edit: Optional[ToEditModel] = Field(default=None)
    to_delete: Optional[ToDeleteModel] = Field(default=None)
    model_config = ConfigDict(extra="forbid")

class AnswerModel(BaseModel):
    result: ResultEnum = Field(...)
    error: Optional[str] = Field(default=None)
    response: Optional[ResponseModel] = Field(default=None)
    model_config = ConfigDict(extra="forbid")
