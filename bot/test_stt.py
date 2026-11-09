import stt
from pathlib import Path
import time

# Имя файла, который мы будем тестировать (он должен лежать в этой же папке)
AUDIO_FILE = Path("test.ogg")

if not AUDIO_FILE.exists():
    print(f"ОШИБКА: Файл {AUDIO_FILE} не найден в папке! Положите его сюда.")
    exit(1)

print("Начинаю распознавание (первый запуск может занять до 20 секунд, пока скачивается модель)...")
start_time = time.time()

try:
    text = stt.transcribe(AUDIO_FILE)
    print("\n--- УСПЕХ! ---")
    print("Распознанный текст:")
    print(text)
except Exception as e:
    print("\n--- ОШИБКА ---")
    print(f"Произошла ошибка при распознавании: {e}")

print(f"\nЗатраченное время: {time.time() - start_time:.2f} сек.")
