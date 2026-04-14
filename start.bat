REM 🚀 Скрипт запуска для Windows

@echo off
chcp 65001 > nul
echo.
echo 🛍️ mngnv Shop Bot - Скрипт запуска для Windows
echo =============================================
echo.

REM Проверка .env
if not exist .env (
    echo ❌ Файл .env не найден!
    echo 📝 Создаю .env из .env.example...
    copy .env.example .env
    echo.
    echo ✅ Файл .env создан.
    echo Отредактируй его и запусти скрипт снова:
    echo    Открой .env и заполни: CDEK_CLIENT_ID и CDEK_CLIENT_SECRET
    echo.
    pause
    exit /b 1
)

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не установлен!
    echo.
    echo Установи Python с https://www.python.org/
    echo Убедись что выбрал "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

REM Проверка зависимостей
echo.
echo 📦 Проверяю зависимости...

python -m pip list | findstr aiogram >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Зависимости не установлены. Устанавливаю...
    pip install -r requirements.txt
)

echo ✅ Зависимости установлены

REM Запуск диагностики
echo.
echo 🔧 Запускаю диагностику...
python diagnostic_tool.py

echo.
echo 🚀 Запускаю бота...
python bot_with_cdek.py

pause
