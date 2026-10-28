"""Распознавание речи через faster-whisper (модель small, int8, CPU)."""

import logging
from pathlib import Path

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    """Ленивая загрузка модели: первый вызов скачивает и грузит её (10-20 сек)."""
    global _model
    if _model is None:
        logger.info("Загружаю модель faster-whisper 'small' (int8), первый запуск может занять 10-20 сек...")
        _model = WhisperModel("small", device="cpu", compute_type="int8")
        logger.info("Модель faster-whisper загружена")
    return _model


def transcribe(audio_path: Path) -> str:
    """Аудио (ogg/opus) -> текст на русском.

    Блокирующий вызов: из async-кода запускать через asyncio.to_thread.
    """
    model = get_model()
    segments, _ = model.transcribe(str(audio_path), language="ru")
    return " ".join(segment.text.strip() for segment in segments).strip()
