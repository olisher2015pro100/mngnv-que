#!/bin/bash
# 🚀 Скрипт запуска для Linux/Mac

echo "🛍️ Telegram Shop Template - Скрипт запуска"
echo "===================================="
echo ""

# Проверка .env
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создаю .env из .env.example..."
    cp .env.example .env
    echo "✅ Файл .env создан. Отредактируй его и запусти скрипт снова:"
    echo "   Открой .env и заполни: TOKEN и ADMIN_ID"
    exit 1
fi

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python не установлен!"
    exit 1
fi

# Проверка зависимостей
echo ""
echo "📦 Проверяю зависимости..."

if ! python3 -m pip list | grep -q aiogram; then
    echo "⚠️ Зависимости не установлены. Устанавливаю..."
    pip install -r requirements.txt
fi

echo "✅ Зависимости установлены"

# Запуск диагностики
echo ""
echo "🔧 Запускаю диагностику..."
python3 diagnostic_tool.py

echo ""
echo "🚀 Запускаю бота..."
python3 bot_with_cdek.py
