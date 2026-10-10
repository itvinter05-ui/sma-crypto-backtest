@echo off
rem Windows: двойной клик по этому файлу
chcp 65001 >nul
cd /d "%~dp0"

set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo Python не найден. Пробую установить через winget...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo Если установка прошла, закройте это окно и запустите run.bat ещё раз.
  echo Если нет - скачайте Python с https://www.python.org/downloads/
  echo ^(при установке поставьте галочку "Add python.exe to PATH"^).
  pause
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Первый запуск: устанавливаю библиотеки ^(1-2 минуты^)...
  %PY% -m venv .venv || goto :fail
  .venv\Scripts\python -m pip install -q --upgrade pip || goto :fail
  .venv\Scripts\python -m pip install -q telethon pandas openpyxl || goto :fail
)

.venv\Scripts\python add_from_excel.py
pause
exit /b 0

:fail
echo Не удалось установить библиотеки.
rmdir /s /q .venv 2>nul
pause
exit /b 1
