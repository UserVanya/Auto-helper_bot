
from aiogram import types, Router
from aiogram.types import ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram import F
from sqlalchemy.orm import Session
from utils.voice_transcriber import transcribe_audio_message
from utils.llm_connector import send_prompt_to_llm
from aiogram.utils.text_decorations import html_decoration
import html
from services import executor, validator
from database.models import DbUser
from models.answers import AnswerModel
from utils.logger import voice_logger

voice_router = Router(name="VoiceCommandsHandler")

def get_action_result_text(is_valid: bool, errors: list, answer: AnswerModel, added_items: list, updated_items: list, deleted_items: list) -> str:
    """
    Формирует текст ответа на основе результатов выполнения команд. 
    """
    if is_valid and answer.response:
        reply_parts = []
        if added_items:
            reply_parts.append(f"✅ Добавлено ({len(added_items)} объектов):")
            for item in added_items:
                reply_parts.append(f"  • {item['type']}: {item['name']}")
        if updated_items:
            reply_parts.append(f"📝 Изменено ({len(updated_items)} объектов):")
            for item in updated_items:
                reply_parts.append(f"  • {item['type']}: {item['name']}")
        if deleted_items:
            reply_parts.append(f"🗑️ Удалено ({len(deleted_items)} объектов):")
            for item in deleted_items:
                reply_parts.append(f"  • {item['type']}: {item['name']}")
        
        if reply_parts:
            return f"🤖 Команды выполнены:\n\n{chr(10).join(reply_parts)}"
    else:
        # Если валидация не прошла, показываем ошибки
        error_text = "🤖 Возникли ошибки при обработке команды:\n\n"
        if errors:
            error_text += '\n'.join(errors)
        if answer and answer.error:
            error_text += f"\n\nОшибка LLM: {answer.error}"
        return error_text
    
    

@voice_router.message(F.voice)
async def handle_voice_message(message: types.Message, db_session: Session, db_user: DbUser):
    """
    Обрабатывает голосовое сообщение: проверяет наличие пользователя, распознаёт текст, 
    отправляет в LLM, выполняет команды и возвращает результат.
    """
    voice_logger.info(f"Received voice message from user {db_user.tg_id} ({db_user.name})")
    
    # Распознаём голосовое сообщение
    voice_logger.debug("Starting voice transcription...")
    text = await transcribe_audio_message(message)
    voice_logger.info(f"Transcribed text: {text[:100]}...")
    
    # Отправляем расшифровку пользователю
    await message.reply(f"🤖 Расшифровка:\n\n{text}")
    
    # Отправляем в LLM и валидируем ответ
    voice_logger.debug("Sending to LLM...")
    text_answer = send_prompt_to_llm(text, db_session, db_user.tg_id)
    
    # Валидируем ответ от LLM, чтобы формат ответа соответствовал модели AnswerModel и ссылки на элементы БД были валидными
    voice_logger.debug("Validating LLM response...")
    is_valid, errors, answer = validator.validate(text_answer, db_session)

    # Выполняем команды, если валидация прошла успешно и ответ от LLM не пустой
    if is_valid:
        voice_logger.info("LLM response is valid, executing commands...")
        added_items, updated_items, deleted_items = executor.execute(db_session, answer.response, db_user.id)
        voice_logger.info(f"Executed commands: added={len(added_items) if added_items else 0}, updated={len(updated_items) if updated_items else 0}, deleted={len(deleted_items) if deleted_items else 0}")
    else:
        voice_logger.warning(f"LLM response validation failed: {errors}")
        added_items, updated_items, deleted_items = None, None, None
    
    reply_text = get_action_result_text(is_valid, errors, answer, added_items, updated_items, deleted_items)
    
    voice_logger.info("Sending response to user")
    await message.reply(html.escape(reply_text))