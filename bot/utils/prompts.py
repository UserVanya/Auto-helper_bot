from datetime import datetime
from database.models import DbTask, DbEvent, DbGoal, DbIdea, DbNote, DbTag, DbSubtask

def build_system_prompt(session, user_id: int) -> str:
    """
    Возвращает system-промпт для LLM, чтобы она отвечала строго в формате YAML по answer_template.yaml,
    а также добавляет в промпт по каждой основной таблице (Task, Event, Goal, Idea, Note, Tag) список id и name.
    """
    # Читаем YAML-шаблон
    with open("answer_template.yaml", "r") as file:
        template = file.read()

    # Собираем справочники из БД
    def get_items(model, user_id: int):
        # Только не удалённые
        q = session.query(model.id, model.name).filter(model.user_id == user_id)
        if hasattr(model, "is_deleted"):
            q = q.filter(model.is_deleted == False)
        return [dict(id=row.id, name=row.name) for row in q.all()]

    tasks = get_items(DbTask, user_id)
    events = get_items(DbEvent, user_id)
    goals = get_items(DbGoal, user_id)
    ideas = get_items(DbIdea, user_id)
    notes = get_items(DbNote, user_id)
    tags = get_items(DbTag, user_id)
    subtasks = session.query(DbSubtask.id, DbSubtask.name).filter(DbSubtask.task_id.in_([x["id"] for x in tasks])).all()

    # Формируем YAML-справочники
    dicts_yaml = (
        f"tasks_existing:\n" + '\n'.join([f"  - id: {x['id']}, name: '{x['name']}'" for x in tasks]) + '\n' +
        f"subtasks_existing:\n" + '\n'.join([f"  - id: {x['id']}, name: '{x['name']}', task_id: {x['task_id']}" for x in subtasks]) + '\n' +
        f"events_existing:\n" + '\n'.join([f"  - id: {x['id']}, name: '{x['name']}'" for x in events]) + '\n' +
        f"goals_existing:\n" + '\n'.join([f"  - id: {x['id']}, name: '{x['name']}'" for x in goals]) + '\n' +
        f"ideas_existing:\n" + '\n'.join([f"  - id: {x['id']}, name: '{x['name']}'" for x in ideas]) + '\n' +
        f"notes_existing:\n" + '\n'.join([f"  - id: {x['id']}, name: '{x['name']}'" for x in notes]) + '\n' +
        f"tags_existing:\n" + '\n'.join([f"  - id: {x['id']}, name: '{x['name']}'" for x in tags])
    )

    prompt = (
        "Ты — интеллектуальный ассистент-органайзер. "
        f"Твой ответ должен быть строго валидным JSON и соответствать следующему YAML шаблону:\n"
        f"{template}\n"
        f"\nВот справочники существующих объектов (используй их id и name при необходимости):\n"
        f"{dicts_yaml}\n"
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