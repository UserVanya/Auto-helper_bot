from ctypes import Union
from datetime import datetime
from database.models import DbTask, DbEvent, DbGoal, DbIdea, DbNote, DbTag, DbSubtask
from sqlalchemy.orm import Session

def build_system_prompt(session: Session, user_id: int) -> str:
    """
    Возвращает system-промпт для LLM, чтобы она отвечала строго в формате YAML по answer_template.yaml,
    а также добавляет в промпт по каждой основной таблице (Task, Event, Goal, Idea, Note, Tag) список id и name.
    """
    # Читаем YAML-шаблон
    with open("answer_template.yaml", "r") as file:
        template = file.read()
    
    # Справочники по объектам
    tasks = session.query(DbTask.id, DbTask.name).filter(DbTask.user_id == user_id, DbTask.is_deleted == False).all()
    events = session.query(DbEvent.id, DbEvent.name).filter(DbEvent.user_id == user_id, DbEvent.is_deleted == False).all()
    goals = session.query(DbGoal.id, DbGoal.name).filter(DbGoal.user_id == user_id, DbGoal.is_deleted == False).all()
    ideas = session.query(DbIdea.id, DbIdea.name).filter(DbIdea.user_id == user_id, DbIdea.is_deleted == False).all()
    notes = session.query(DbNote.id, DbNote.name).filter(DbNote.user_id == user_id, DbNote.is_deleted == False).all()
    tags = session.query(DbTag.id, DbTag.name).filter(DbTag.user_id == user_id, DbTag.is_deleted == False).all()
    subtasks = session.query(DbSubtask.id, DbSubtask.name, DbSubtask.task_id).filter(DbSubtask.is_deleted == False).all()

    # Связи между объектами (many-to-many)
    def get_links(table, col1, col2):
        return session.execute(table.select()).fetchall()

    # Импортируем таблицы связей из models.py
    from database.models import (
        task_event, task_goal, task_idea, task_note, task_tag,
        event_goal, event_idea, event_note, event_tag,
        goal_idea, goal_note, goal_tag,
        idea_note, idea_tag,
        note_tag
    )

    links = {
        "task_event": get_links(task_event, "task_id", "event_id"),
        "task_goal": get_links(task_goal, "task_id", "goal_id"),
        "task_idea": get_links(task_idea, "task_id", "idea_id"),
        "task_note": get_links(task_note, "task_id", "note_id"),
        "task_tag": get_links(task_tag, "task_id", "tag_id"),
        "event_goal": get_links(event_goal, "event_id", "goal_id"),
        "event_idea": get_links(event_idea, "event_id", "idea_id"),
        "event_note": get_links(event_note, "event_id", "note_id"),
        "event_tag": get_links(event_tag, "event_id", "tag_id"),
        "goal_idea": get_links(goal_idea, "goal_id", "idea_id"),
        "goal_note": get_links(goal_note, "goal_id", "note_id"),
        "goal_tag": get_links(goal_tag, "goal_id", "tag_id"),
        "idea_note": get_links(idea_note, "idea_id", "note_id"),
        "idea_tag": get_links(idea_tag, "idea_id", "tag_id"),
        "note_tag": get_links(note_tag, "note_id", "tag_id"),
    }

    def format_list(lst, fields):
        return "\n".join(" ".join(str(getattr(row, f, row[idx])) for idx, f in enumerate(fields)) for row in lst)

    dicts_txt = (
        "tasks(task_id, task_name):\n" + format_list(tasks, ["id", "name"]) + "\n"
        "events(event_id, event_name):\n" + format_list(events, ["id", "name"]) + "\n"
        "goals(goal_id, goal_name):\n" + format_list(goals, ["id", "name"]) + "\n"
        "ideas(idea_id, idea_name):\n" + format_list(ideas, ["id", "name"]) + "\n"
        "notes(note_id, note_name):\n" + format_list(notes, ["id", "name"]) + "\n"
        "tags(tag_id, tag_name):\n" + format_list(tags, ["id", "name"]) + "\n"
        "subtasks(subtask_id, subtask_name, task_id):\n" + format_list(subtasks, ["id", "name", "task_id"]) + "\n"
    )
    for link_name, link_rows in links.items():
        # Имя связи и поля
        table = eval(link_name)
        cols = [c.name for c in table.columns]
        dicts_txt += f"{link_name}({', '.join(cols)}):\n"
        dicts_txt += format_list(link_rows, cols) + "\n"

    prompt = (
        "Ты — интеллектуальный ассистент-органайзер. "
        f"Твой ответ должен быть строго валидным JSON и соответствать следующему YAML шаблону:\n"
        f"{template}\n"
        f"\nВот справочники существующих объектов (используй их id и name при необходимости):\n"
        f"{dicts_txt}\n"
        "- Всегда возвращай только YAML, без пояснений, markdown или лишнего текста.\n"
        "- Структура и типы должны строго соответствовать шаблону.\n"
        "- Не добавляй поля deadline, start_time или end_time, если пользователь их явно не указал.\n"
        "- Если ты не можешь однозначно распознать команду пользователя или не можешь корректно сформировать YAML по шаблону, заполни result: ERROR и в error укажи причину, почему не удалось выдать корректный ответ.\n"
        "- Не добавляй никаких комментариев или лишних полей.\n"
        f"- Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "Будь то просто дата или время, всегда возвращай в формате YYYY-MM-DD HH:MM:SS\n"
        "Твой ответ должен начинаться с ```json и заканчиваться ```\n"
    ) 
    print(prompt)
    return prompt