"""Конфигурация: чтение .env и общие константы бота."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

MAX_TEXT_LEN = 1000
MAX_VOICE_SECONDS = 60

# key -> (надпись на кнопке, имя голоса Silero TTS)
VOICES: dict[str, tuple[str, str]] = {
    "aidar": ("Aidar (мужской)", "aidar"),
    "baya": ("Baya (женский)", "baya"),
    "eugene": ("Eugene (мужской)", "eugene"),
    "kseniya": ("Kseniya (женский)", "kseniya"),
    "xenia": ("Xenia (женский)", "xenia"),
}
DEFAULT_VOICE = VOICES["aidar"][1]


def get_bot_token() -> str:
    """Возвращает BOT_TOKEN из .env. Кидает понятную ошибку, если токена нет."""
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "your_token_here":
        raise RuntimeError(
            "BOT_TOKEN не задан. Скопируйте bot/.env.example в bot/.env "
            "и впишите токен, полученный у @BotFather."
        )
    return token
