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
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

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

# Tag model
class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

# Task model
class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(SqlEnum(TaskStatus, name="task_status"), default=TaskStatus.NEW, nullable=False)
    deadline = Column(DateTime)
    is_deleted = Column(Boolean, default=False, nullable=False)
    tag = Column(String)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('User', back_populates='tasks')

    subtasks = relationship('Subtask', back_populates='task', cascade='all, delete-orphan')
    events = relationship('Event', secondary=task_event, back_populates='tasks')
    goals = relationship('Goal', secondary=task_goal, back_populates='tasks')
    ideas = relationship('Idea', secondary=task_idea, back_populates='tasks')
    notes = relationship('Note', secondary=task_note, back_populates='tasks')

# Subtask model
class Subtask(Base):
    __tablename__ = 'subtasks'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    deadline = Column(DateTime)
    is_done = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    task = relationship('Task', back_populates='subtasks')

# Event model
class Event(Base):
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
    user = relationship('User', back_populates='events')

    tasks = relationship('Task', secondary=task_event, back_populates='events')
    goals = relationship('Goal', secondary=event_goal, back_populates='events')
    ideas = relationship('Idea', secondary=event_idea, back_populates='events')
    notes = relationship('Note', secondary=event_note, back_populates='events')

# Goal model
class Goal(Base):
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
    user = relationship('User', back_populates='goals')

    tasks = relationship('Task', secondary=task_goal, back_populates='goals')
    events = relationship('Event', secondary=event_goal, back_populates='goals')
    ideas = relationship('Idea', secondary=goal_idea, back_populates='goals')
    notes = relationship('Note', secondary=goal_note, back_populates='goals')

# Idea model
class Idea(Base):
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
    user = relationship('User', back_populates='ideas')

    tasks = relationship('Task', secondary=task_idea, back_populates='ideas')
    events = relationship('Event', secondary=event_idea, back_populates='ideas')
    goals = relationship('Goal', secondary=goal_idea, back_populates='ideas')
    notes = relationship('Note', secondary=idea_note, back_populates='ideas')

# Note model
class Note(Base):
    __tablename__ = 'notes'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    is_deleted = Column(Boolean, default=False, nullable=False)
    tag = Column(String)
    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('User', back_populates='notes')

    tasks = relationship('Task', secondary=task_note, back_populates='notes')
    events = relationship('Event', secondary=event_note, back_populates='notes')
    goals = relationship('Goal', secondary=goal_note, back_populates='notes')
    ideas = relationship('Idea', secondary=idea_note, back_populates='notes')

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    tg_id = Column(BigInteger, nullable=False, unique=True)

    tasks = relationship('Task', back_populates='user')
    events = relationship('Event', back_populates='user')
    goals = relationship('Goal', back_populates='user')
    ideas = relationship('Idea', back_populates='user')
    notes = relationship('Note', back_populates='user')

    created = Column(DateTime, server_default=func.now(), nullable=False)
    updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)