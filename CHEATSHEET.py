"""
КРАТКИЙ СПРАВОЧНИК: Интеграция CDEK в твой Mini App на aiogram 3.x

Все что нужно знать на одной странице!
"""

# ════════════════════════════════════════════════════════════════════════════
# 1️⃣ УСТАНОВКА И КОНФИГУРАЦИЯ (5 минут)
# ════════════════════════════════════════════════════════════════════════════

"""
Шаг 1: Установи зависимости
    pip install -r requirements.txt

Шаг 2: Создай .env файл
    cp .env.example .env
    
    Заполни:
    BOT_TOKEN=твой_токен_от_BotFather
    CDEK_CLIENT_ID=4I5vLAbLUPdMIOEhVD0osn4fS0fvTttj
    CDEK_CLIENT_SECRET=g1WXBI56G3ZAPrY0TleKblVIwsnMCm8J

Шаг 3: Запусти бота
    python bot_with_cdek.py
    
    Результат:
    🤖 Запускаю Telegram бота...
    ✅ API запущена на http://127.0.0.1:8000
"""


# ════════════════════════════════════════════════════════════════════════════
# 2️⃣ ОСНОВНЫЕ ФУНКЦИИ (Копируй в свой код)
# ════════════════════════════════════════════════════════════════════════════

from cdek_integration import calculate_shipping, validate_phone, validate_city

# ✅ РАСЧЕТ ДОСТАВКИ
async def example_shipping():
    cost, description = await calculate_shipping("Москва")
    print(f"Доставка: {cost} ₽ - {description}")
    # Output: Доставка: 450 ₽ - Доставка: Стандартная доставка до 5 дней


# ✅ ВАЛИДАЦИЯ ТЕЛЕФОНА
async def example_validation():
    is_valid = await validate_phone("+7 999 123 45 67")
    # Returns: True
    
    is_valid = await validate_phone("123")
    # Returns: False


# ✅ ПРОВЕРКА ГОРОДА
async def example_city_check():
    exists = await validate_city("Москва")
    # Returns: True
    
    exists = await validate_city("Несуществующий город")
    # Returns: False


# ════════════════════════════════════════════════════════════════════════════
# 3️⃣ ИНТЕГРАЦИЯ В TELEGRAM BOT
# ════════════════════════════════════════════════════════════════════════════

from aiogram import Router, types, F
from aiogram.filters import Command

router = Router()

# 🟢 БАЗОВАЯ ИНТЕГРАЦИЯ
@router.message(Command("shipping"))
async def cmd_shipping(message: types.Message):
    """Команда: /shipping Москва"""
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Используй: /shipping <город>")
        return
    
    city = args[1]
    cost, description = await calculate_shipping(city)
    
    await message.answer(
        f"🚚 <b>{description}</b>\n"
        f"📍 {city}: {cost} ₽",
        parse_mode="HTML"
    )

# 🟢 ОБРАБОТКА WEB APP ДАННЫХ
@router.message(F.web_app_data)
async def handle_web_app_order(message: types.Message):
    """Получить заказ из Mini App с доставкой"""
    
    import json
    order = json.loads(message.web_app_data.data)
    
    # Данные уже содержат shipping_cost и shipping_city!
    await message.answer(
        f"✅ Заказ получен!\n"
        f"📦 {order['item']}\n"
        f"🚚 Доставка в {order.get('shipping_city')}: {order.get('shipping_cost')} ₽\n"
        f"💵 Итого: {order['price'] + order.get('shipping_cost', 500)} ₽"
    )


# ════════════════════════════════════════════════════════════════════════════
# 4️⃣ ОБРАБОТКА ОШИБОК (Что делать при проблеме)
# ════════════════════════════════════════════════════════════════════════════

"""
❌ ПРОБЛЕМА: "CDEK_CLIENT_ID или CDEK_CLIENT_SECRET не установлены"
✅ РЕШЕНИЕ: 
   1. Проверь .env файл
   2. Убедись что оба ключа заполнены (не пусто)
   3. Перезагрузи бота: python bot_with_cdek.py

❌ ПРОБЛЕМА: "Timeout при расчете доставки"
✅ РЕШЕНИЕ:
   1. Проверь интернет
   2. Проверь статус CDEK API: curl https://api.cdek.ru/
   3. Попробуй другой город
   4. Код все равно вернет 500 ₽ и не сломает заказ

❌ ПРОБЛЕМА: "Город не найден"
✅ РЕШЕНИЕ:
   1. Проверь написание города (Москва, не москва)
   2. Используй популярные города из списка
   3. Доставка все равно будет 500 ₽

❌ ПРОБЛЕМА: "API не запускается"
✅ РЕШЕНИЕ:
   python -m pip install -r requirements.txt
   python bot_with_cdek.py
"""


# ════════════════════════════════════════════════════════════════════════════
# 5️⃣ НАСТРОЙКА ПАРАМЕТРОВ ПОСЫЛКИ
# ════════════════════════════════════════════════════════════════════════════

"""
Открой cdek_integration.py и отредактируй:

    SENDER_CITY_CODE = 442  # Город отправления (Улан-Удэ)
    PACKAGE_WEIGHT = 0.9    # Вес в кг
    PACKAGE_LENGTH = 30     # Длина в см
    PACKAGE_WIDTH = 25      # Ширина в см
    PACKAGE_HEIGHT = 10     # Высота в см

Популярные коды городов CDEK:
    1 - Москва
    2 - Санкт-Петербург
    3 - Екатеринбург
    442 - Улан-Удэ
    ...и еще много

Больше кодов: https://partner.cdek.ru/geography
"""


# ════════════════════════════════════════════════════════════════════════════
# 6️⃣ API ENDPOINTS (Для Mini App)
# ════════════════════════════════════════════════════════════════════════════

"""
📍 ГЛАВНЫЙ ENDPOINT: POST /api/calculate-shipping

Запрос:
    POST http://localhost:8000/api/calculate-shipping
    Content-Type: application/json
    
    {
        "city": "Москва"
    }

Ответ (успех):
    {
        "cost": 450,
        "description": "Доставка: Стандартная доставка до 5 дней",
        "city": "Москва"
    }

Ответ (ошибка):
    {
        "cost": 500,
        "description": "Доставка (город не найден, дефолтная стоимость)",
        "city": "Москва"
    }

---

📍 ДРУГИЕ ENDPOINTS:

GET /api/health
    Проверка статуса бота и CDEK
    Response: {"status": "ok", "cdek_connected": true, "bot_initialized": true}

GET /
    Информация об API
    Response: {"name": "mngnv Bot API", "version": "1.0.0", ...}
"""


# ════════════════════════════════════════════════════════════════════════════
# 7️⃣ ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ В JAVASCRIPT (FRONTEND)
# ════════════════════════════════════════════════════════════════════════════

"""
// ПРОСМОТРИ index_updated.html ДЛЯ ПОЛНОГО ПРИМЕРА

// Быстрый пример:

async function calculateShipping(city) {
    try {
        const response = await fetch('/api/calculate-shipping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ city: city })
        });
        
        const data = await response.json();
        console.log(`Доставка: ${data.cost} ₽`);
        return data.cost;
        
    } catch (error) {
        console.error('Ошибка:', error);
        return 500; // Дефолт при ошибке
    }
}

// Использование:
const shippingCost = await calculateShipping('Москва');
document.getElementById('total').innerText = `${productPrice + shippingCost} ₽`;
"""


# ════════════════════════════════════════════════════════════════════════════
# 8️⃣ ЛОГИРОВАНИЕ И ДЕБАГ
# ════════════════════════════════════════════════════════════════════════════

"""
Включи логирование для отладки:

1. Логи в консоль (уже включено по умолчанию)
2. Логи в файл:
   
   Отредактируй bot_with_cdek.py и добавь:
   
   logging.basicConfig(
       level=logging.DEBUG,  # Детальное логирование
       handlers=[
           logging.FileHandler('bot.log'),
           logging.StreamHandler()
       ]
   )

3. Посмотри логи:
   
   tail -f bot.log
   
   Ищи ошибки:
   - ❌ Красные сообщения об ошибках
   - ✅ Зеленые сообщения об успехе
   - ⚠️ Желтые предупреждения

Примеры логов:

    ✅ Получен новый CDEK OAuth токен (истечет через 3600с)
    ✅ Найден код города 'Москва': 1
    ✅ Стоимость доставки в 'Москва': 450 руб
    ⚠️ Город 'Неизвестный' не найден
    ❌ Ошибка получения токена CDEK
"""


# ════════════════════════════════════════════════════════════════════════════
# 9️⃣ PERFORMANCE И ОПТИМИЗАЦИЯ
# ════════════════════════════════════════════════════════════════════════════

"""
⚡ ЧТО УЖЕ ОПТИМИЗИРОВАНО:

1. ✅ Кэширование OAuth токена (55 минут) 
   → 1 запрос на CDEK вместо каждого раза

2. ✅ Асинхронность (async/await)
   → Бот обрабатывает много заказов одновременно

3. ✅ Таймауты (10-15 секунд)
   → Не зависает если CDEK медленный

4. ✅ Дефолтные стоимости
   → Заказ не сломается при ошибке

⚙️ КАК ДОПОЛНИТЕЛЬНО ОПТИМИЗИРОВАТЬ:

1. Добавить кэш результатов в Redis (города часто повторяются)
2. Батч запросы нескольких городов одновременно
3. Preload популярных городов при старте

Смотри QUICK_START_EXAMPLES.py для примеров
"""


# ════════════════════════════════════════════════════════════════════════════
# 🔟 SECURITY (БЕЗОПАСНОСТЬ)
# ════════════════════════════════════════════════════════════════════════════

"""
🔐 КАК ЗАЩИТИТЬ КЛЮЧИ:

1. ✅ .env НЕ КОММИТИШЬ В GIT
   
   Добавь в .gitignore:
   echo ".env" >> .gitignore

2. ✅ ИСПОЛЬЗУЙ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ НА ПРОДАКШЕНЕ
   
   export BOT_TOKEN="твой_токен"
   export CDEK_CLIENT_ID="твой_id"
   export CDEK_CLIENT_SECRET="твой_secret"
   
   python bot_with_cdek.py

3. ✅ ВАЛИДАЦИЯ ВСЕХ ВХОДНЫХ ДАННЫХ
   
   - Проверяем город перед запросом
   - Проверяем телефон перед сохранением
   - Фильтруем Long SQL injection и XSS

4. ✅ ЛОГИРОВАНИЕ БЕЗ КЛЮЧЕЙ
   
   Не логируем CDEK_CLIENT_ID/SECRET
   Логируем только операции

5. ✅ RATELIMIT на API
   
   Добавь максимум 10 запросов в минуту на IP:
   
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/api/calculate-shipping")
   @limiter.limit("10/minute")
   async def ...
"""


# ════════════════════════════════════════════════════════════════════════════
# ИТОГОВЫЙ ЧЕКЛИСТ 📋
# ════════════════════════════════════════════════════════════════════════════

"""
ПЕРЕД ЗАПУСКОМ:

☐ Установил зависимости: pip install -r requirements.txt
☐ Создал .env с BOT_TOKEN
☐ Заполнил CDEK_CLIENT_ID и CDEK_CLIENT_SECRET
☐ Обновил MINI_APP_URL в .env
☐ Заменил index.html на index_updated.html
☐ Запустил тест: python cdek_integration.py

ПРИ ЗАПУСКЕ:

☐ Бот запустился без ошибок
☐ API слушает на 127.0.0.1:8000
☐ CDEK токен получен (✅ в логах)
☐ Mini App открывается в боте
☐ Поле города работает с подсказками
☐ Телефон форматируется правильно

ПОСЛЕ ЗАПУСКА:

☐ Выбрал город → рассчитана доставка
☐ Виден расчет доставки в UI
☐ Заказ отправляется с shipping_cost
☐ Админ получает уведомление
☐ Покупатель видит подтверждение

В ЛОГАХ:

☐ Нет ошибок ❌
☐ Все операции логируются ✅
☐ CDEK токен кэшируется 🔑
☐ Доставка рассчитывается верно 💰
"""


if __name__ == "__main__":
    print(__doc__)
    print("\n" + "="*80)
    print("📖 Для подробной информации смотри CDEK_INTEGRATION_README.md")
    print("💡 Для примеров кода смотри QUICK_START_EXAMPLES.py")
    print("="*80)
