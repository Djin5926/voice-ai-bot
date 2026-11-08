"""Синтез речи: edge-tts (текст -> mp3) и ffmpeg (mp3 -> ogg/opus)."""

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path

import edge_tts
import edge_tts.communicate
import edge_tts.constants

logger = logging.getLogger(__name__)

# =====================================================================
# 👇 ПАТЧ ДЛЯ MICROSOFT: Принудительно переключаем на новый сервер
# =====================================================================
NEW_HOST = "api.msedgeservices.com"
try:
    # Формируем новый URL с обязательным токеном
    new_wss_url = (
        f"wss://{NEW_HOST}/tts/cognitiveservices/websocket/v1"
        f"?Ocp-Apim-Subscription-Key={edge_tts.constants.TRUSTED_CLIENT_TOKEN}"
    )
    # Подменяем адреса в библиотеке
    edge_tts.constants.WSS_URL = new_wss_url
    edge_tts.communicate.WSS_URL = new_wss_url
    logger.info("Применен патч сервера Microsoft TTS (api.msedgeservices.com)")
except Exception as e:
    logger.warning(f"Не удалось применить патч сервера: {e}")
# =====================================================================

ATTEMPTS = 2
RETRY_PAUSE_SEC = 1

# Запасной путь: локальная сборка ffmpeg внутри проекта (tools/ffmpeg/bin).
LOCAL_FFMPEG = Path(__file__).resolve().parent.parent / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"


def ffmpeg_path() -> Path | None:
    """Путь до ffmpeg: из PATH или из tools/ внутри проекта. None — если нет нигде."""
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)
    if LOCAL_FFMPEG.exists():
        return LOCAL_FFMPEG
    return None


async def _synthesize_mp3(text: str, voice: str) -> Path:
    """Текст -> mp3 через edge-tts. Сетевые ошибки: 2 попытки с паузой 1 сек."""
    
    # Получаем адрес прокси из переменных окружения (из .env)
    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    
    last_exc: Exception | None = None
    for attempt in range(1, ATTEMPTS + 1):
        mp3_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        mp3_file.close()
        mp3_path = Path(mp3_file.name)
        try:
            # Передаем прокси в Communicate, если он задан
            if proxy_url:
                communicator = edge_tts.Communicate(text, voice, proxy=proxy_url)
            else:
                communicator = edge_tts.Communicate(text, voice)
                
            await communicator.save(str(mp3_path))
            return mp3_path
        except Exception as exc:
            mp3_path.unlink(missing_ok=True)
            last_exc = exc
            logger.warning("edge-tts попытка %s/%s не удалась: %s", attempt, ATTEMPTS, exc)
        if attempt < ATTEMPTS:
            await asyncio.sleep(RETRY_PAUSE_SEC)
    raise RuntimeError(f"edge-tts не ответил после {ATTEMPTS} попыток") from last_exc


async def _convert_to_ogg(mp3_path: Path) -> Path:
    """mp3 -> ogg/opus (формат voice-сообщений Telegram) через ffmpeg."""
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise RuntimeError("ffmpeg не найден: см. README, раздел «Требования»")
    ogg_file = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    ogg_file.close()
    ogg_path = Path(ogg_file.name)
    proc = await asyncio.create_subprocess_exec(
        str(ffmpeg), "-y", "-i", str(mp3_path),
        "-c:a", "libopus", "-b:a", "48k", "-ar", "48000", "-ac", "1",
        str(ogg_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        ogg_path.unlink(missing_ok=True)
        tail = stderr.decode(errors="ignore")[-500:] if stderr else ""
        raise RuntimeError(f"ffmpeg завершился с кодом {proc.returncode}: {tail}")
    return ogg_path


async def synthesize(text: str, voice: str) -> Path:
    """Текст -> ogg/opus выбранным голосом.

    Возвращает путь к временному файлу; вызывающий обязан удалить его
    в блоке finally после отправки.
    """
    mp3_path = await _synthesize_mp3(text, voice)
    try:
        return await _convert_to_ogg(mp3_path)
    finally:
        mp3_path.unlink(missing_ok=True)
