"""Конфигурация: чтение .env и общие константы бота."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

MAX_TEXT_LEN = 1000
MAX_VOICE_SECONDS = 60

# key -> (надпись на кнопке, имя голоса edge-tts)
VOICES: dict[str, tuple[str, str]] = {
    "dmitry": ("Dmitry (мужской, ru)", "ru-RU-DmitryNeural"),
    "svetlana": ("Svetlana (женский, ru)", "ru-RU-SvetlanaNeural"),
    "aria": ("Aria (женский, en)", "en-US-AriaNeural"),
}
DEFAULT_VOICE = VOICES["dmitry"][1]


def get_bot_token() -> str:
    """Возвращает BOT_TOKEN из .env. Кидает понятную ошибку, если токена нет."""
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "your_token_here":
        raise RuntimeError(
            "BOT_TOKEN не задан. Скопируйте bot/.env.example в bot/.env "
            "и впишите токен, полученный у @BotFather."
        )
    return token
