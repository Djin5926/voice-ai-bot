"""Точка входа: регистрация хендлеров и запуск бота (long polling)."""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import stt
import tts
from config import DEFAULT_VOICE, MAX_TEXT_LEN, MAX_VOICE_SECONDS, VOICES, get_bot_token

logger = logging.getLogger(__name__)

# Выбранный голос по user_id. Только в памяти процесса, без БД.
user_voices: dict[int, str] = {}

HELP_TEXT = (
    "Привет! Я бот «текст <-> голос».\n\n"
    "• Пришли любой текст — озвучу его голосом (по умолчанию Dmitry, русский мужской).\n"
    "• Пришли голосовое сообщение — распознаю и пришлю текст.\n\n"
    "Команды:\n"
    "/voice — выбрать голос синтеза\n"
    "/help — эта справка"
)

FFMPEG_MISSING = (
    "ОШИБКА: ffmpeg не найден ни в PATH, ни в tools/ffmpeg/.\n"
    "Он нужен для конвертации mp3 -> ogg/opus.\n"
    "Установите его (например, `apt install ffmpeg`) или распакуйте\n"
    "сборку в tools/ffmpeg/ так, чтобы был tools/ffmpeg/bin/ffmpeg."
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start и /help — приветствие и краткая справка."""
    await update.message.reply_text(HELP_TEXT)


async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/voice — inline-клавиатура с выбором голоса синтеза."""
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"voice:{key}")]
        for key, (label, _) in VOICES.items()
    ]
    await update.message.reply_text(
        "Выберите голос синтеза:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def on_voice_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Нажатие кнопки выбора голоса: запомнить и подтвердить."""
    query = update.callback_query
    await query.answer()
    key = query.data.split(":", 1)[1]
    label, voice_id = VOICES[key]
    user_voices[query.from_user.id] = voice_id
    await query.edit_message_text(f"Голос синтеза: {label}")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Текст -> голосовое сообщение."""
    message = update.message
    text = message.text or ""
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN]
        await message.reply_text(f"Текст обрезан до {MAX_TEXT_LEN} символов")
    voice = user_voices.get(message.from_user.id, DEFAULT_VOICE)
    audio: Path | None = None
    try:
        audio = await tts.synthesize(text, voice)
        await message.reply_voice(voice=audio)
    except Exception:
        logger.exception("TTS не удалось (user_id=%s)", message.from_user.id)
        await message.reply_text("Не удалось синтезировать речь. Попробуйте ещё раз позже.")
    finally:
        if audio is not None:
            audio.unlink(missing_ok=True)


async def on_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Голосовое сообщение -> текст."""
    message = update.message
    if message.voice.duration > MAX_VOICE_SECONDS:
        await message.reply_text(f"Слишком длинное аудио, максимум {MAX_VOICE_SECONDS} секунд")
        return
    await message.reply_text("Распознаю...")
    audio: Path | None = None
    try:
        ogg_file = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        ogg_file.close()
        audio = Path(ogg_file.name)
        tg_file = await message.voice.get_file()
        await tg_file.download_to_drive(audio)
        text = await asyncio.to_thread(stt.transcribe, audio)
        await message.reply_text(text if text else "Не удалось распознать речь.")
    except Exception:
        logger.exception("STT не удалось (user_id=%s)", message.from_user.id)
        await message.reply_text("Не удалось распознать аудио. Попробуйте ещё раз.")
    finally:
        if audio is not None:
            audio.unlink(missing_ok=True)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Страховка: любая непойманная ошибка логируется, процесс не падает."""
    logger.error("Необработанная ошибка (update=%s): %s", update, context.error)


async def post_init(application: Application) -> None:
    logger.info("Bot started")


def main() -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if tts.ffmpeg_path() is None:
        sys.exit(FFMPEG_MISSING)

    try:
        token = get_bot_token()
    except RuntimeError as exc:
        sys.exit(f"ОШИБКА: {exc}")

    # ПРОКСИ УДАЛЕН (сервер в Нидерландах, Telegram доступен напрямую)

    application = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    application.add_handler(CommandHandler(["start", "help"], cmd_start))
    application.add_handler(CommandHandler("voice", cmd_voice))
    application.add_handler(CallbackQueryHandler(on_voice_chosen, pattern=r"^voice:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    application.add_handler(MessageHandler(filters.VOICE, on_voice_message))
    application.add_error_handler(on_error)

    application.run_polling()


if __name__ == "__main__":
    main()
