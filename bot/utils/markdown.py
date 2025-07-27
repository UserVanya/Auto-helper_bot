def escape_md(text: str) -> str:
    """
    Экранирует специальные символы Markdown для Telegram.
    """
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text) 