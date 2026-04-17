@echo off
title MNGNV SHOP BOT
echo 🚀 Запускаю твой сервер...

:: Переходим в папку с ботом
cd /d "%~dp0"

:: Активируем виртуальное окружение
call .venv\Scripts\activate

:: Запускаем самого бота
python main.py

:: Если бот упадет, окно не закроется сразу, чтобы ты видел ошибку
pause