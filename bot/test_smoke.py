"""Smoke-тест: все модули бота импортируются без ошибок.

Запуск из папки bot:
    python test_smoke.py
или через pytest:
    pytest test_smoke.py
"""

import importlib

MODULES = ("config", "tts", "stt", "main")


def test_imports():
    for name in MODULES:
        importlib.import_module(name)
        print(f"import ok: {name}")


if __name__ == "__main__":
    test_imports()
    print("smoke test passed")
