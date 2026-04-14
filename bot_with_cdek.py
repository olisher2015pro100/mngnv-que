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

# ====== AIOGRAM ======
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import asyncio

# ====== FASTAPI ======
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# ====== CDEK ======
from cdek_integration import calculate_shipping, validate_phone, get_cdek_oauth_token

# ====== КОНФИГУРАЦИЯ ======
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN', '8515886958:AAHWLWjmGtFj9BsUleOSsqZCaoN7NxdBHf4')
ADMINS = [int(id) for id in os.getenv('ADMINS', '1018181608').split(',')]
ADMIN_ID = ADMINS[0] if ADMINS else None

# Mini App URL - ОБНОВИ НА СВОЙ URL!
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://yourdomain.com/index.html')

# CDEK API ключи - ОБЯЗАТЕЛЬНО ЗАПОЛНИ!
CDEK_CLIENT_ID = os.getenv('CDEK_CLIENT_ID', '')
CDEK_CLIENT_SECRET = os.getenv('CDEK_CLIENT_SECRET', '')

# ================================================
# ⚠️ ИНИЦИАЛИЗАЦИЯ CDEK ПЕРЕМЕННЫХ
# ================================================
# Импортируем модуль CDEK и устанавливаем ключи
import cdek_integration
cdek_integration.CDEK_CLIENT_ID = CDEK_CLIENT_ID
cdek_integration.CDEK_CLIENT_SECRET = CDEK_CLIENT_SECRET

if not CDEK_CLIENT_ID or not CDEK_CLIENT_SECRET:
    logger.warning("⚠️ CDEK_CLIENT_ID или CDEK_CLIENT_SECRET не установлены!")
    logger.warning("   Доставка будет рассчитываться как 500 ₽ по умолчанию")

# ================================================
# AIOGRAM BOT
# ================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
    
    try:
        data = await request.json()
        city = data.get('city', '').strip()
        
        if not city:
            logger.warning("⚠️ Пустое имя города в запросе доставки")
            return {
                "cost": 500,
                "description": "Ошибка: не указан город",
                "city": ""
            }
        
        logger.info(f"📍 Расчет доставки для города: {city}")
        
        # Вызываем асинхронную функцию из cdek_integration
        cost, description = await calculate_shipping(city)
        
        return {
            "cost": cost,
            "description": description,
            "city": city
        }
        
    except json.JSONDecodeError:
        logger.error("❌ Ошибка парсинга JSON в запросе доставки")
        return {
            "cost": 500,
            "description": "Ошибка: некорректный JSON",
            "city": ""
        }
    except Exception as e:
        logger.error(f"💥 Ошибка в endpoint доставки: {e}")
        return {
            "cost": 500,
            "description": f"Ошибка сервера: {str(e)[:50]}",
            "city": ""
        }


@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    token = await get_cdek_oauth_token()
    return {
        "status": "ok",
        "cdek_connected": token is not None,
        "bot_initialized": bot.token is not None
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
    logger.info("🤖 Запускаю Telegram бота...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка в боте: {e}")


def main():
    """Главная точка входа"""
    
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК mngnv SHOP BOT")
    logger.info("=" * 60)
    logger.info(f"Bot Token: {BOT_TOKEN[:20]}...")
    logger.info(f"CDEK Client: {'✅' if CDEK_CLIENT_ID else '❌'} Установлен")
    logger.info(f"Mini App URL: {MINI_APP_URL}")
    logger.info("=" * 60)
    
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
        loop.run_until_complete(asyncio.gather(
            server.serve(),
            run_bot()
        ))
    except KeyboardInterrupt:
        logger.info("⏹️ Завершение работы...")


if __name__ == "__main__":
    main()
