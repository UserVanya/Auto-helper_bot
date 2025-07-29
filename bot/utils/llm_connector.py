from openai import OpenAI
from utils.prompts import build_system_prompt
from environs import Env
from sqlalchemy.orm import Session
from utils.logger import llm_logger
import json

# Инициализация клиента OpenAI (openrouter)
env = Env()
env.read_env()
openrouter_api_key = env("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key,
)

MODEL = env("MODEL")

def send_prompt_to_llm(prompt: str, session: Session, user_id: int) -> str:
    """
    Отправляет текстовый prompt в LLM (openrouter) с system-промптом и возвращает ответ.
    """
    llm_logger.info(f"Sending prompt to LLM (model: {MODEL})")
    llm_logger.debug(f"Prompt: {prompt[:200]}...")
    
    try:
        completion = client.chat.completions.create(
            extra_headers={},
            extra_body={},
            model=MODEL,
            messages=[
                #{"role": "system", "content": build_system_prompt(session)},
                {
                    "role": "user", 
                    "content": build_system_prompt(session, user_id) + "\n\n" + prompt
                }
            ],
            temperature=1
        )
        
        llm_logger.debug(f"LLM response: {completion}")
        
        if getattr(completion, "error", None):
            llm_logger.error(f"LLM error: {completion.error}")
            to_return = {
                "result": "ERROR",
                "error": completion.error.__str__()
            }
            return f"```json\n{json.dumps(to_return, indent=2)}\n```"
        
        response_content = completion.choices[0].message.content
        llm_logger.info(f"LLM response received, length: {len(response_content)}")
        llm_logger.debug(f"Response preview: {response_content[:200]}...")
        
        return response_content
        
    except Exception as e:
        llm_logger.error(f"Exception during LLM request: {e}")
        to_return = {
            "result": "ERROR",
            "error": str(e)
        }
        return f"```json\n{json.dumps(to_return, indent=2)}\n```" 