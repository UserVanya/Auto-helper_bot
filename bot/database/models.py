from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Table,
    Text,
    func,
    BigInteger,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.types import Enum as SqlEnum
import enum

Base = declarative_base()

# Enum for task status
class TaskStatus(enum.Enum):
    NEW = "🆕"
    IN_PROGRESS = "🟠"
    COMPLETED = "✅"

    def next(self):
        if self == TaskStatus.NEW:
            return TaskStatus.IN_PROGRESS
        elif self == TaskStatus.IN_PROGRESS:
            return TaskStatus.COMPLETED
        else:
            return TaskStatus.NEW
    
    def prev(self):
        if self == TaskStatus.IN_PROGRESS:
            return TaskStatus.NEW
        elif self == TaskStatus.COMPLETED:
            return TaskStatus.IN_PROGRESS
        else:
            return TaskStatus.COMPLETED
# Association tables for many-to-many relationships

task_event = Table(
    'task_event',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('event_id', Integer, ForeignKey('events.id'), primary_key=True),
)

task_goal = Table(
    'task_goal',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('goal_id', Integer, ForeignKey('goals.id'), primary_key=True),
)

task_idea = Table(
    'task_idea',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('idea_id', Integer, ForeignKey('ideas.id'), primary_key=True),
)

task_note = Table(
    'task_note',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('notes.id'), primary_key=True),
)

event_goal = Table(
    'event_goal',
    Base.metadata,
    Column('event_id', Integer, ForeignKey('events.id'), primary_key=True),
    Column('goal_id', Integer, ForeignKey('goals.id'), primary_key=True),
)

event_idea = Table(
    'event_idea',
    Base.metadata,
    Column('event_id', Integer, ForeignKey('events.id'), primary_key=True),
    Column('idea_id', Integer, ForeignKey('ideas.id'), primary_key=True),
)

event_note = Table(
    'event_note',
    Base.metadata,
    Column('event_id', Integer, ForeignKey('events.id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('notes.id'), primary_key=True),
)

goal_idea = Table(
    'goal_idea',
    Base.metadata,
    Column('goal_id', Integer, ForeignKey('goals.id'), primary_key=True),
    Column('idea_id', Integer, ForeignKey('ideas.id'), primary_key=True),
)

goal_note = Table(
    'goal_note',
    Base.metadata,
    Column('goal_id', Integer, ForeignKey('goals.id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('notes.id'), primary_key=True),
)

idea_note = Table(
    'idea_note',
    Base.metadata,
    Column('idea_id', Integer, ForeignKey('ideas.id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('notes.id'), primary_key=True),
)

task_tag = Table(
    'task_tag',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
)

event_tag = Table(
    'event_tag',
    Base.metadata,
    Column('event_id', Integer, ForeignKey('events.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
)

goal_tag = Table(
    'goal_tag',
    Base.metadata,
    Column('goal_id', Integer, ForeignKey('goals.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
)

idea_tag = Table(
    'idea_tag',
    Base.metadata,
    Column('idea_id', Integer, ForeignKey('ideas.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
)

note_tag = Table(
    'note_tag',
    Base.metadata,
    Column('note_id', Integer, ForeignKey('notes.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
)


# Tag model
class DbTag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('DbUser', back_populates='tags')

    tasks = relationship('DbTask', secondary=task_tag, back_populates='tags')
    events = relationship('DbEvent', secondary=event_tag, back_populates='tags')
    goals = relationship('DbGoal', secondary=goal_tag, back_populates='tags')
    ideas = relationship('DbIdea', secondary=idea_tag, back_populates='tags')
    notes = relationship('DbNote', secondary=note_tag, back_populates='tags')

# Task model
class DbTask(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(SqlEnum(TaskStatus, name="task_status"), default=TaskStatus.NEW, nullable=False)
    deadline = Column(DateTime)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('DbUser', back_populates='tasks')

    subtasks = relationship('DbSubtask', back_populates='task', cascade='all, delete-orphan')
    events = relationship('DbEvent', secondary=task_event, back_populates='tasks')
    goals = relationship('DbGoal', secondary=task_goal, back_populates='tasks')
    ideas = relationship('DbIdea', secondary=task_idea, back_populates='tasks')
    notes = relationship('DbNote', secondary=task_note, back_populates='tasks')
    tags = relationship('DbTag', secondary=task_tag, back_populates='tasks')

# Subtask model
class DbSubtask(Base):
    __tablename__ = 'subtasks'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    deadline = Column(DateTime)
    is_done = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    task = relationship('DbTask', back_populates='subtasks')

# Event model
class DbEvent(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    tag = Column(String)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('DbUser', back_populates='events')

    tasks = relationship('DbTask', secondary=task_event, back_populates='events')
    goals = relationship('DbGoal', secondary=event_goal, back_populates='events')
    ideas = relationship('DbIdea', secondary=event_idea, back_populates='events')
    notes = relationship('DbNote', secondary=event_note, back_populates='events')
    tags = relationship('DbTag', secondary=event_tag, back_populates='events')
# Goal model
class DbGoal(Base):
    __tablename__ = 'goals'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    deadline = Column(DateTime)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    tag = Column(String)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('DbUser', back_populates='goals')

    tasks = relationship('DbTask', secondary=task_goal, back_populates='goals')
    events = relationship('DbEvent', secondary=event_goal, back_populates='goals')
    ideas = relationship('DbIdea', secondary=goal_idea, back_populates='goals')
    notes = relationship('DbNote', secondary=goal_note, back_populates='goals')
    tags = relationship('DbTag', secondary=goal_tag, back_populates='goals')
# Idea model
class DbIdea(Base):
    __tablename__ = 'ideas'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    tag = Column(String)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('DbUser', back_populates='ideas')

    tasks = relationship('DbTask', secondary=task_idea, back_populates='ideas')
    events = relationship('DbEvent', secondary=event_idea, back_populates='ideas')
    goals = relationship('DbGoal', secondary=goal_idea, back_populates='ideas')
    notes = relationship('DbNote', secondary=idea_note, back_populates='ideas')
    tags = relationship('DbTag', secondary=idea_tag, back_populates='ideas')
# Note model
class DbNote(Base):
    __tablename__ = 'notes'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    is_deleted = Column(Boolean, default=False, nullable=False)
    tag = Column(String)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('DbUser', back_populates='notes')

    tasks = relationship('DbTask', secondary=task_note, back_populates='notes')
    events = relationship('DbEvent', secondary=event_note, back_populates='notes')
    goals = relationship('DbGoal', secondary=goal_note, back_populates='notes')
    ideas = relationship('DbIdea', secondary=idea_note, back_populates='notes')
    tags = relationship('DbTag', secondary=note_tag, back_populates='notes')
    
class DbUser(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    tg_id = Column(BigInteger, nullable=False, unique=True)

    tags = relationship('DbTag', back_populates='user')
    tasks = relationship('DbTask', back_populates='user')
    events = relationship('DbEvent', back_populates='user')
    goals = relationship('DbGoal', back_populates='user')
    ideas = relationship('DbIdea', back_populates='user')
    notes = relationship('DbNote', back_populates='user')

    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)