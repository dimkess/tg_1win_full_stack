@echo off
:loop
cls
python main.py
echo.
echo --- Перезапуск через 3 секунды ---
timeout /t 3
goto loop