#!/bin/bash
# macOS / Linux: двойной клик (или `bash run.command` в Терминале)
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python не найден. Установите его с https://www.python.org/downloads/ и запустите снова."
  read -r -p "Нажмите Enter, чтобы закрыть..."
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Первый запуск: устанавливаю библиотеки (1-2 минуты)..."
  python3 -m venv .venv && .venv/bin/python -m pip install -q --upgrade pip \
    && .venv/bin/python -m pip install -q telethon pandas openpyxl \
    || { echo "Не удалось установить библиотеки."; rm -rf .venv; read -r -p "Enter..."; exit 1; }
fi

.venv/bin/python add_from_excel.py
read -r -p "Нажмите Enter, чтобы закрыть..."
