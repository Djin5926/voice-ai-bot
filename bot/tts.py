"""Синтез речи: локальная модель Silero TTS и ffmpeg (wav -> ogg/opus)."""

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

import torch
import soundfile as sf

logger = logging.getLogger(__name__)

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


# --- Загрузка модели Silero TTS (делается один раз при старте) ---
# Модель скачается при первом запуске (около 150 МБ) и будет работать офлайн.
logger.info("Загружаю модель Silero TTS (v4_ru)...")
try:
    # Загружаем модель
    model, example_text = torch.hub.load(
        repo_or_dir='snakers4/silero-models',
        model='silero_tts',
        language='ru',
        speaker='v4_ru'
    )
    logger.info("Модель Silero TTS успешно загружена.")
except Exception as e:
    logger.error(f"Ошибка загрузки модели Silero TTS: {e}")
    model = None


def _synthesize_wav(text: str, voice: str) -> Path:
    """Текст -> wav через локальную модель Silero TTS."""
    if model is None:
        raise RuntimeError("Модель Silero TTS не загружена")
        
    # Silero использует свои имена голосов: aidar (муж), baya (жен), kseniya, xenia, eugene.
    # Мы пока используем 'aidar' по умолчанию.
    speaker = 'aidar'
    
    audio = model.apply_tts(
        text=text,
        speaker=speaker,
        sample_rate=48000
    )
    
    wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_file.close()
    wav_path = Path(wav_file.name)
    
    sf.write(wav_path, audio.numpy(), 48000)
    return wav_path


async def _convert_to_ogg(wav_path: Path) -> Path:
    """wav -> ogg/opus (формат voice-сообщений Telegram) через ffmpeg."""
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise RuntimeError("ffmpeg не найден: см. README, раздел «Требования»")
    ogg_file = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    ogg_file.close()
    ogg_path = Path(ogg_file.name)
    proc = await asyncio.create_subprocess_exec(
        str(ffmpeg), "-y", "-i", str(wav_path),
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
    """Текст -> ogg/opus выбранным голосом."""
    # Синтез в отдельном потоке, чтобы не блокировать event loop
    wav_path = await asyncio.to_thread(_synthesize_wav, text, voice)
    try:
        return await _convert_to_ogg(wav_path)
    finally:
        wav_path.unlink(missing_ok=True)
