import os
import subprocess
import whisper
from typing import Optional
from environs import Env
from aiogram.types import Message



env = Env()
env.read_env()

whisper_dir = env("WHISPER_CACHE_DIR")
whisper_model_path = f"{whisper_dir}/small-v3.pt"

def load_whisper_model(model_path: str, fallback_size: str = 'small'):
    """
    Загружает модель Whisper с диска, если есть, иначе скачивает стандартную.
    """
    if os.path.exists(model_path):
        return whisper.load_model(model_path)
    return whisper.load_model(fallback_size)

# Загружаем модель Whisper (один раз на старте)
model = load_whisper_model(whisper_model_path)

async def transcribe_audio_message(message: Message, language: Optional[str] = "ru") -> str:
    """
    Скачивает голосовое сообщение, конвертирует ogg в mp3, распознаёт текст и удаляет временные файлы.
    Возвращает распознанный текст.
    """
    voice = message.voice
    voice_path = f"voice_{message.from_user.id}.ogg"
    mp3_path = os.path.join(os.getcwd(), f"voice_{message.from_user.id}.mp3")
    with open(voice_path, "wb") as f:
        await message.bot.download(voice.file_id, f)
    convert_ogg_to_mp3(voice_path, mp3_path)
    text = transcribe_audio(model, mp3_path, language=language)
    cleanup_files(mp3_path, voice_path)
    return text

def convert_ogg_to_mp3(ogg_path: str, mp3_path: str):
    """
    Конвертирует ogg-файл в mp3 с помощью ffmpeg.
    """
    subprocess.run([
        "ffmpeg", "-i", ogg_path, "-acodec", "libmp3lame", "-y", mp3_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def transcribe_audio(model, mp3_path: str, language: Optional[str] = None) -> str:
    """
    Распознаёт речь из mp3-файла с помощью Whisper.
    """
    result = model.transcribe(mp3_path, language=language)
    return result['text'].strip()

def cleanup_files(*paths):
    """
    Удаляет указанные файлы, если они существуют.
    """
    for path in paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
