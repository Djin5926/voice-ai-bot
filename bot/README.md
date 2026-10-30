# Telegram-бот TTS/STT

Учебный проект: бот принимает текст и присылает голосовое сообщение
(синтез через [edge-tts](https://github.com/rany2/edge-tts)), а голосовые
сообщения расшифровывает в текст ([faster-whisper](https://github.com/SYSTRAN/faster-whisper)).

## Требования

- Python 3.11+
- **ffmpeg** в PATH — нужен для конвертации mp3 → ogg/opus
  (варианты установки на Windows: `winget install Gyan.FFmpeg`;
  на Linux: `apt install ffmpeg`).
  Запасной вариант: распаковать сборку в `tools/ffmpeg/` в корне проекта,
  чтобы файл лежал по пути `tools/ffmpeg/bin/ffmpeg.exe` — бот найдёт его сам.
- Токен бота от [@BotFather](https://t.me/BotFather)

## Установка и запуск

Из папки `bot/`:

```bash
# 1. Виртуальное окружение (если ещё нет, из корня проекта)
python -m venv ../venv

# 2. Активация
../venv/Scripts/activate        # Windows
# source ../venv/bin/activate   # Linux

# 3. Зависимости
pip install -r requirements.txt

# 4. Токен
cp .env.example .env            # Windows: copy .env.example .env
# затем впишите в .env свой токен: BOT_TOKEN=123456:ABC-...

# 5. Запуск
python main.py
```

В логе должна появиться строка `Bot started`.

## Команды бота

| Команда | Что делает |
|---|---|
| `/start`, `/help` | Приветствие и краткая справка |
| `/voice` | Выбор голоса синтеза (inline-клавиатура) |
| любое текстовое сообщение | Бот присылает его голосом (TTS) |
| голосовое сообщение | Бот присылает распознанный текст (STT) |

Голоса: Dmitry и Svetlana (русские), Aria (английский). Выбор запоминается
на время работы процесса (в памяти, без БД). Текст длиннее 1000 символов
обрезается с предупреждением; аудио длиннее 60 секунд не принимается.

## Smoke-тест

```bash
python test_smoke.py    # из папки bot/ — проверяет, что все модули импортируются
```

## Заметки

- **.env** с токеном в git не попадает (он в `.gitignore`). В репозитории лежит
  только `.env.example` с плейсхолдером.
- Модель faster-whisper (`small`, int8) скачивается при первом голосовом
  сообщении — первый ответ займёт 10–20 секунд, дальше быстро.
- edge-tts должен быть версии **7.3+**: старые версии Microsoft блокирует
  (ошибка 403).

## Структура

```
bot/
  main.py            # точка входа, хендлеры Telegram
  tts.py             # edge-tts -> mp3 -> ffmpeg -> ogg/opus
  stt.py             # faster-whisper (small, int8, CPU)
  config.py          # чтение .env, голоса, лимиты
  requirements.txt
  .env.example
  test_smoke.py      # smoke-тест на импорт модулей
  README.md
```
