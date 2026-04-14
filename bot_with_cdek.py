"""
EXAMPLE: Интеграция CDEK API в aiogram 3.x Mini App бот
Пример подключения cdek_integration.py с FastAPI для расчета доставки

Требования:
    pip install aiogram==3.x aiohttp python-dotenv fastapi uvicorn
"""

import os
import json
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

# ====== БАЗОВЫЙ ИМПОРТ ======
import asyncio

# ====== AIOGRAM (С ПРОВЕРКОЙ) ======
try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import Command
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
    AIOGRAM_AVAILABLE = True
    print("✅ aiogram импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта aiogram: {e}")
    AIOGRAM_AVAILABLE = False

# ====== FASTAPI (С ПРОВЕРКОЙ) ======
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
    print("✅ FastAPI импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта FastAPI: {e}")
    FASTAPI_AVAILABLE = False

# ====== CDEK (С ПРОВЕРКОЙ) ======
try:
    from cdek_integration import calculate_shipping, validate_phone, get_cdek_oauth_token
    CDEK_AVAILABLE = True
    print("✅ cdek_integration импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта cdek_integration: {e}")
    CDEK_AVAILABLE = False

# ====== КОНФИГУРАЦИЯ ======
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🔍 ДИАГНОСТИКА ИМПОРТОВ:")
print(f"   aiogram: {'✅' if AIOGRAM_AVAILABLE else '❌'}")
print(f"   FastAPI: {'✅' if FASTAPI_AVAILABLE else '❌'}")
print(f"   cdek_integration: {'✅' if CDEK_AVAILABLE else '❌'}")
print("=" * 60)

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN', '8515886958:AAHWLWjmGtFj9BsUleOSsqZCaoN7NxdBHf4')
ADMINS = [int(id) for id in os.getenv('ADMINS', '1018181608').split(',')]
ADMIN_ID = ADMINS[0] if ADMINS else None

# Mini App URL - ОБНОВИ НА СВОЙ URL!
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://yourdomain.com/index.html')

# CDEK API ключи - ОБНОВЛЕНО!
CDEK_CLIENT_ID = os.getenv('CDEK_CLIENT_ID', '4I5vLAbLUPdMIOEhVD0osn4fS0fvTttj')
CDEK_CLIENT_SECRET = os.getenv('CDEK_CLIENT_SECRET', 'g1WXBI56G3ZAPrY0TleKblVIwsnMCm8J')

# ================================================
# ⚠️ ИНИЦИАЛИЗАЦИЯ CDEK ПЕРЕМЕННЫХ
# ================================================
if CDEK_AVAILABLE:
    try:
        import cdek_integration
        cdek_integration.CDEK_CLIENT_ID = CDEK_CLIENT_ID
        cdek_integration.CDEK_CLIENT_SECRET = CDEK_CLIENT_SECRET
        print(f"✅ CDEK ключи установлены в cdek_integration:")
        print(f"   ID: {CDEK_CLIENT_ID[:15]}..." if CDEK_CLIENT_ID else "   ID: ❌ Пусто")
        print(f"   Secret: {'✅ Установлен' if CDEK_CLIENT_SECRET else '❌ Пусто'}")
    except Exception as e:
        print(f"❌ Ошибка инициализации CDEK: {e}")
        CDEK_AVAILABLE = False
else:
    print("⚠️ cdek_integration не найден, доставка будет 500₽ по умолчанию")

if not CDEK_CLIENT_ID or not CDEK_CLIENT_SECRET:
    logger.warning("⚠️ CDEK_CLIENT_ID или CDEK_CLIENT_SECRET не установлены!")
    logger.warning("   Доставка будет рассчитываться как 500 ₽ по умолчанию")
    print("⚠️ CDEK ключи НЕ установлены! Будет использоваться фиксированная стоимость 500₽")

# ================================================
# AIOGRAM BOT
# ================================================

if AIOGRAM_AVAILABLE:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    print(f"✅ Telegram Bot инициализирован: {BOT_TOKEN[:20]}...")
else:
    bot = None
    dp = None
    print("❌ Telegram Bot не может быть инициализирован (aiogram недоступен)")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start - показываем Mini App"""
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Кнопка для открытия Mini App
    web_link = MINI_APP_URL
    markup.add(KeyboardButton(
        "🛍️ Открыть магазин", 
        web_app=WebAppInfo(url=web_link)
    ))
    
    welcome_text = (
        "🔥 <b>Добро пожаловать в mngnv shop!</b>\n\n"
        "Здесь ты можешь купить вещи или поговорить с менеджером.\n"
        "Нажми кнопку ниже, чтобы открыть каталог.\n\n"
        "❓ <b>Как это работает?</b>\n"
        "1️⃣ Выбери товар и размер\n"
        "2️⃣ Укажи город - автоматически рассчитается доставка СДЭК 🚚\n"
        "3️⃣ Заполни свои данные\n"
        "4️⃣ Получи реквизиты для оплаты\n"
    )
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=markup)

@dp.message(types.Message)
async def handle_web_app_data(message: types.Message):
    """Обработка данных из Mini App"""
    
    # Проверяем, содержит ли сообщение данные из web app
    if message.web_app_data:
        try:
            order_data = json.loads(message.web_app_data.data)
            
            # Логируем заказ
            logger.info(f"📦 Новый заказ от {message.chat.id}:")
            logger.info(json.dumps(order_data, indent=2, ensure_ascii=False))
            
            # Отправляем подтверждение пользователю
            customer_message = format_customer_confirmation(order_data, message.chat.id)
            await message.answer(customer_message, parse_mode="HTML")
            
            # Отправляем уведомление админам
            if order_data.get('shipping_city'):
                admin_message = format_admin_notification(order_data, message.from_user)
                for admin_id in ADMINS:
                    try:
                        await bot.send_message(admin_id, admin_message, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Ошибка отправки админу {admin_id}: {e}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга данных Mini App: {e}")
            await message.answer("❌ Ошибка обработки заказа. Попробуй еще раз.")
    else:
        await message.answer(
            "👋 Используй кнопку '🛍️ Открыть магазин' для оформления заказа!"
        )


def format_customer_confirmation(order_data: Dict, chat_id: int) -> str:
    """Форматирует сообщение подтверждения для покупателя"""
    
    item = order_data.get('item', '—')
    price = order_data.get('price', 0)
    shipping_cost = order_data.get('shipping_cost', 500)
    shipping_city = order_data.get('shipping_city', '—')
    total = price + shipping_cost
    size = order_data.get('size', '—')
    fio = order_data.get('customer', '—')
    phone = order_data.get('phone', '—')
    email = order_data.get('email', '—')
    address = order_data.get('address', '—')
    index = order_data.get('index', '—')
    tg_user = order_data.get('tg_user', '—')
    
    message = (
        f"✅ <b>Заказ получен!</b>\n\n"
        f"<b>📦 Товар:</b> {item}\n"
        f"<b>📏 Размер:</b> {size}\n"
        f"<b>💰 Цена товара:</b> {price:,} ₽\n"
        f"<b>🚚 Доставка в {shipping_city}:</b> {shipping_cost:,} ₽\n"
        f"<b>━━━━━━━━━━━━━━━━</b>\n"
        f"<b>💵 Итого к оплате:</b> {total:,} ₽\n\n"
        f"<b>👤 Твои данные:</b>\n"
        f"• ФИО: {fio}\n"
        f"• Телефон: {phone}\n"
        f"• Email: {email}\n"
        f"• Адрес: {address}\n"
        f"• Индекс: {index}\n"
        f"• TG: {tg_user}\n\n"
        f"📍 <b>Реквизиты для оплаты:</b>\n"
        f"<code>2200 7020 9556 5789</code> (Т-Банк / Минганов И.А)\n\n"
        f"🙏 Пожалуйста, пришли скриншот чека, ответив на это сообщение.\n"
        f"Как только получим платёж, подтвердим заказ!"
    )
    
    return message


def format_admin_notification(order_data: Dict, user: types.User) -> str:
    """Форматирует уведомление для администратора"""
    
    message = (
        f"🔔 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        f"<b>👤 Покупатель:</b> {user.first_name} (ID: {user.id})\n"
        f"<b>📱 Telegram:</b> @{user.username or 'нет'}\n\n"
        f"<b>📦 Товар:</b> {order_data.get('item', '—')}\n"
        f"<b>📏 Размер:</b> {order_data.get('size', '—')}\n"
        f"<b>💰 Сумма:</b> {order_data.get('price', 0):,} ₽\n"
        f"<b>🚚 Доставка:</b> {order_data.get('shipping_city', '—')} - {order_data.get('shipping_cost', 500):,} ₽\n"
        f"<b>💵 Итого:</b> {order_data.get('price', 0) + order_data.get('shipping_cost', 500):,} ₽\n\n"
        f"<b>📋 Контакты:</b>\n"
        f"• ФИО: {order_data.get('customer', '—')}\n"
        f"• Телефон: {order_data.get('phone', '—')}\n"
        f"• Email: {order_data.get('email', '—')}\n"
        f"• Адрес: {order_data.get('address', '—')}\n"
        f"• Индекс: {order_data.get('index', '—')}"
    )
    
    return message


# ================================================
# FASTAPI - РАСЧЕТ ДОСТАВКИ
# ================================================

app = FastAPI(title="mngnv Bot API")

@app.post("/api/calculate-shipping")
async def calculate_shipping_endpoint(request: Request) -> Dict:
    """
    POST /api/calculate-shipping
    
    Принимает город из DaData и возвращает цену доставки от СДЭК
    
    Body:
        {
            "city": "Москва"
        }
    
    Response:
        {
            "cost": 500,
            "description": "Доставка: Стандартная доставка до 5 дней",
            "city": "Москва"
        }
    """
    
    print("\n" + "="*60)
    print("📍 ЭНДПОИНТ /api/calculate-shipping")
    print("="*60)
    print(f"🔑 CDEK Client ID: {CDEK_CLIENT_ID[:10]}..." if CDEK_CLIENT_ID else "❌ CDEK Client ID не установлен")
    print(f"🔐 CDEK Client Secret: {'✅ Установлен' if CDEK_CLIENT_SECRET else '❌ Не установлен'}")
    print("="*60)
    
    try:
        data = await request.json()
        city = data.get('city', '').strip()
        
        print(f"📥 Получены данные: {data}")
        print(f"🏙️ Город из запроса: '{city}'")
        
        if not city:
            print("⚠️ ОШИБКА: Пустое имя города!")
            logger.warning("⚠️ Пустое имя города в запросе доставки")
            return {
                "cost": 500,
                "description": "Ошибка: не указан город",
                "city": ""
            }
        
        print(f"✅ Город валидный, начинаю расчет...")
        logger.info(f"📍 Расчет доставки для города: {city}")
        
        # Проверяем наличие ключей
        if not CDEK_CLIENT_ID or not CDEK_CLIENT_SECRET:
            print("❌ ОШИБКА: Ключи CDEK не установлены!")
            print(f"   CDEK_CLIENT_ID: {'❌' if not CDEK_CLIENT_ID else '✅'}")
            print(f"   CDEK_CLIENT_SECRET: {'❌' if not CDEK_CLIENT_SECRET else '✅'}")
            return {
                "cost": 500,
                "description": "❌ КРИТИЧЕСКАЯ ОШИБКА: Ключи CDEK не установлены",
                "city": city
            }
        
        # Проверяем, доступна ли функция расчета
        if not CDEK_AVAILABLE:
            print("⚠️ CDEK недоступен, использую значение по умолчанию: 500₽")
            return {
                "cost": 500,
                "description": "⚠️ Стандартная доставка (CDEK недоступен)",
                "city": city
            }
        
        # Вызываем асинхронную функцию из cdek_integration
        print(f"🔄 Вызываю calculate_shipping('{city}')...")
        cost, description = await calculate_shipping(city)
        
        print(f"✅ ОТВЕТ ОТ СДЭК:")
        print(f"   Стоимость: {cost} ₽")
        print(f"   Описание: {description}")
        logger.info(f"✅ Результат: стоимость={cost}, описание={description}")
        
        response_data = {
            "cost": cost,
            "description": description,
            "city": city
        }
        
        print(f"📤 Отправляю ответ: {response_data}")
        print("="*60 + "\n")
        
        return response_data
        
    except json.JSONDecodeError as e:
        print(f"❌ ОШИБКА: Некорректный JSON в запросе")
        print(f"   Ошибка: {e}")
        logger.error(f"❌ Ошибка парсинга JSON в запросе доставки: {e}")
        print("="*60 + "\n")
        return {
            "cost": 500,
            "description": "Ошибка: некорректный JSON",
            "city": ""
        }
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в эндпоинте:")
        print(f"   Тип: {type(e).__name__}")
        print(f"   Сообщение: {str(e)}")
        logger.error(f"💥 Ошибка в endpoint доставки: {e}")
        print("="*60 + "\n")
        return {
            "cost": 500,
            "description": f"Ошибка сервера: {str(e)[:50]}",
            "city": ""
        }


@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    print("\n📊 Проверка здоровья API...")
    
    token = None
    try:
        if CDEK_AVAILABLE and CDEK_CLIENT_ID and CDEK_CLIENT_SECRET:
            token = await get_cdek_oauth_token()
            print(f"   CDEK токен: {'✅ Получен' if token else '❌ Не получен'}")
        else:
            print("   CDEK недоступен или ключи не установлены")
    except Exception as e:
        print(f"   CDEK ошибка: {e}")
    
    bot_ok = bot.token is not None if AIOGRAM_AVAILABLE and bot else False
    print(f"   Telegram Bot: {'✅' if bot_ok else '❌'}")
    print(f"   CDEK Client ID: {'✅' if CDEK_CLIENT_ID else '❌'}")
    print(f"   Ключи установлены: {'✅ ДА' if (CDEK_CLIENT_ID and CDEK_CLIENT_SECRET) else '❌ НЕТ'}\n")
    
    return {
        "status": "ok",
        "cdek_connected": token is not None,
        "cdek_keys_present": bool(CDEK_CLIENT_ID and CDEK_CLIENT_SECRET),
        "bot_initialized": bot_ok
    }


@app.get("/")
async def root():
    """Главная страница API"""
    return {
        "name": "mngnv Bot API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "calculate_shipping": "/api/calculate-shipping (POST)"
        }
    }


# ================================================
# ЗАПУСК БОТА И API
# ================================================

async def run_bot():
    """Запуск бота в фоне"""
    if not AIOGRAM_AVAILABLE or bot is None or dp is None:
        print("❌ Telegram бот недоступен (aiogram не установлен)")
        logger.error("❌ Telegram бот недоступен (aiogram не установлен)")
        return
    
    logger.info("🤖 Запускаю Telegram бота...")
    print("🤖 Запускаю Telegram бота...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка в боте: {e}")
        print(f"❌ Ошибка в боте: {e}")


def main():
    """Главная точка входа"""
    
    print("\n" + "=" * 70)
    print("🚀 ЗАПУСК mngnv SHOP BOT")
    print("=" * 70)
    
    print("\n📋 КОНФИГУРАЦИЯ:")
    print(f"   Bot Token: {BOT_TOKEN[:20]}..." if BOT_TOKEN else "   Bot Token: ❌ НЕ УСТАНОВЛЕН")
    print(f"   CDEK Client ID: {CDEK_CLIENT_ID[:15]}..." if CDEK_CLIENT_ID else "   CDEK Client ID: ❌ НЕ УСТАНОВЛЕН")
    print(f"   CDEK Client Secret: {'✅ Установлен' if CDEK_CLIENT_SECRET else '❌ НЕ УСТАНОВЛЕН'}")
    print(f"   Mini App URL: {MINI_APP_URL}")
    
    print("\n🔍 СТАТУС КОМПОНЕНТОВ:")
    print(f"   aiogram: {'✅ Готов' if AIOGRAM_AVAILABLE else '❌ Недоступен'}")
    print(f"   FastAPI: {'✅ Готов' if FASTAPI_AVAILABLE else '❌ Недоступен'}")
    print(f"   CDEK: {'✅ Готов' if CDEK_AVAILABLE else '❌ Недоступен (будет 500₽ по умолчанию)'}")
    
    print("\n📱 API ЭНДПОИНТЫ:")
    print("   POST /api/calculate-shipping - расчет доставки")
    print("   GET  /api/health             - проверка здоровья")
    print("   GET  /                       - информация об API")
    
    print("\n" + "=" * 70)
    print("⏳ Запуск сервера...\n")
    
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК mngnv SHOP BOT")
    logger.info("=" * 60)
    logger.info(f"Bot Token: {BOT_TOKEN[:20]}...")
    logger.info(f"CDEK Client: {'✅' if CDEK_CLIENT_ID else '❌'} Установлен")
    logger.info(f"Mini App URL: {MINI_APP_URL}")
    logger.info("=" * 60)
    
    # Проверяем доступность FastAPI перед запуском
    if not FASTAPI_AVAILABLE:
        print("❌ FastAPI не установлен! Установите: pip install fastapi uvicorn")
        logger.error("❌ FastAPI не установлен!")
        return
    
    # Параметры запуска FastAPI сервера
    uvicorn_config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
    
    server = uvicorn.Server(uvicorn_config)
    
    # Запускаем оба в asyncio loop
    loop = asyncio.get_event_loop()
    
    try:
        if AIOGRAM_AVAILABLE:
            # Запускаем и FastAPI сервер, и Telegram бота
            print("🔄 Запускаю FastAPI и Telegram бота в asyncio...")
            loop.run_until_complete(asyncio.gather(
                server.serve(),
                run_bot()
            ))
        else:
            # Запускаем только FastAPI
            print("⚠️ Telegram бот недоступен (aiogram не установлен)")
            print("🔄 Запускаю только FastAPI сервер...")
            loop.run_until_complete(server.serve())
    except KeyboardInterrupt:
        print("\n⏹️ Завершение работы...")
        logger.info("⏹️ Завершение работы...")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main()
