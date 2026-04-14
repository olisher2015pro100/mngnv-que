"""
БЫСТРЫЙ СТАРТ: Интеграция CDEK в твой существующий бот

Минимальный пример для интеграции расчета доставки в aiogram 3.x бот
"""

# ============ ВАРИАНТ 1: Простая интеграция в существующий бот ============

from aiogram import Dispatcher, types, Router
from cdek_integration import calculate_shipping, validate_phone
import asyncio

router = Router()

@router.message(lambda msg: "доставка" in msg.text.lower())
async def shipping_handler(message: types.Message):
    """
    Обработчик для расчета доставки
    
    Пользователь напишет: "доставка Москва"
    Бот ответит с расчитанной стоимостью
    """
    
    text = message.text.lower()
    
    # Извлекаем город (простой способ)
    parts = text.split()
    if len(parts) > 1:
        city_name = " ".join(parts[1:])
        
        # Показываем индикатор загрузки
        await message.answer("⏳ Рассчитываю доставку...")
        
        # Вызываем функцию CDEK
        cost, description = await calculate_shipping(city_name)
        
        # Отправляем результат
        response = (
            f"🚚 <b>{description}</b>\n\n"
            f"📍 Город: {city_name}\n"
            f"💰 Стоимость: <b>{cost} ₽</b>"
        )
        
        await message.edit_text(response, parse_mode="HTML")
    else:
        await message.answer("Укажи город: /shipping Москва")


# ============ ВАРИАНТ 2: Использование в middleware ============

from aiogram import BaseMiddleware

class ShippingMiddleware(BaseMiddleware):
    """Middleware для автоматического подсчета доставки"""
    
    async def __call__(self, handler, event, data):
        # Выполняем основной handler
        result = await handler(event, data)
        
        # Если это заказ - рассчитываем доставку
        if isinstance(event, types.Message) and event.web_app_data:
            import json
            order = json.loads(event.web_app_data.data)
            city = order.get('city')
            
            if city:
                cost, desc = await calculate_shipping(city)
                order['shipping_cost'] = cost
                order['shipping_description'] = desc
        
        return result


# ============ ВАРИАНТ 3: Асинхронный кэш для популярных городов ============

from functools import lru_cache
from typing import Dict

class ShippingCache:
    """Кэш для часто запрашиваемых городов"""
    
    def __init__(self, ttl_seconds=3600):
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl_seconds
        self.timestamps = {}
    
    async def get_cost(self, city: str):
        """Получить стоимость с кэшем"""
        import time
        
        # Проверяем кэш
        if city in self.cache:
            if time.time() - self.timestamps[city] < self.ttl:
                return self.cache[city]
        
        # Запрашиваем свежие данные
        cost, description = await calculate_shipping(city)
        
        # Сохраняем в кэш
        self.cache[city] = (cost, description)
        self.timestamps[city] = time.time()
        
        return cost, description


shipping_cache = ShippingCache(ttl_seconds=1800)  # 30 минут


@router.message()
async def cached_shipping_handler(message: types.Message):
    """Обработчик с кэшем"""
    
    city = "Москва"
    cost, description = await shipping_cache.get_cost(city)
    
    await message.answer(f"Доставка: {cost} ₽")


# ============ ВАРИАНТ 4: Валидация телефона перед отправкой ============

@router.message()
async def validate_phone_handler(message: types.Message):
    """Проверяем номер телефона перед обработкой заказа"""
    
    phone = message.text
    
    if not await validate_phone(phone):
        await message.answer(
            "❌ Некорректный номер телефона!\n"
            "Примеры правильных:\n"
            "+7 999 123 45 67\n"
            "8 999 123 45 67\n"
            "99912345678"
        )
        return
    
    await message.answer("✅ Номер корректен!")


# ============ ВАРИАНТ 5: Полный пример Mini App интеграции ============

from fastapi import FastAPI, Request
import json

app = FastAPI()

@app.post("/api/shipping")
async def api_shipping_endpoint(request: Request):
    """
    API endpoint для Mini App
    
    POST /api/shipping
    {
        "city": "Москва",
        "user_id": 123456789
    }
    """
    
    try:
        data = await request.json()
        city = data.get("city", "").strip()
        user_id = data.get("user_id")
        
        if not city:
            return {"error": "Не указан город", "cost": 500}
        
        # Рассчитываем доставку
        cost, description = await calculate_shipping(city)
        
        # Логируем (опционально - сохраняем в БД)
        print(f"[SHIPPING] User {user_id} - City: {city} - Cost: {cost}")
        
        return {
            "success": True,
            "cost": cost,
            "description": description,
            "city": city
        }
        
    except Exception as e:
        print(f"[ERROR] Shipping endpoint: {e}")
        return {"error": str(e), "cost": 500}


# ============ ВАРИАНТ 6: Расширенное логирование ============

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shipping.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def calculate_shipping_with_logging(city: str):
    """Обертка для логирования"""
    
    logger.info(f"📍 Запрос доставки для города: {city}")
    
    try:
        cost, description = await calculate_shipping(city)
        logger.info(f"✅ Доставка рассчитана: {city} -> {cost} ₽")
        return cost, description
        
    except Exception as e:
        logger.error(f"❌ Ошибка при расчете доставки для {city}: {e}")
        return 500, "Доставка (ошибка при расчете)"


# ============ ВАРИАНТ 7: Батч запросы (расчет для нескольких городов) ============

async def calculate_shipping_batch(cities: list) -> Dict[str, tuple]:
    """
    Рассчитать доставку для нескольких городов одновременно
    
    Usage:
        results = await calculate_shipping_batch(['Москва', 'Питер', 'Казань'])
        # {'Москва': (450, '...'), 'Питер': (500, '...'), ...}
    """
    
    tasks = {city: calculate_shipping(city) for city in cities}
    results = {}
    
    for city, task in tasks.items():
        cost, description = await task
        results[city] = (cost, description)
    
    return results


# ============ ВАРИАНТ 8: Уведомления в Telegram при ошибке доставки ============

async def notify_admin_shipping_error(error_message: str, city: str, user_id: int):
    """Отправить алерт администратору"""
    
    from aiogram import Bot
    
    admin_id = 1018181608  # Твой ID
    bot = Bot(token="YOUR_BOT_TOKEN")
    
    alert = (
        f"⚠️ <b>ОШИБКА РАСЧЕТА ДОСТАВКИ</b>\n\n"
        f"👤 User ID: {user_id}\n"
        f"🏙️ Город: {city}\n"
        f"📝 Ошибка: {error_message}\n\n"
        f"💡 Автоматически использована стоимость 500 ₽"
    )
    
    await bot.send_message(admin_id, alert, parse_mode="HTML")


# ============ УДОБНАЯ ФУНКЦИЯ ДЛЯ ТВОЕГО КОДА ============

async def get_shipping_cost_safe(city: str, default_cost: int = 500) -> int:
    """
    'Безопасная' функция для получения стоимости доставки
    
    - Всегда возвращает стоимость (не ломает заказ при ошибке)
    - Логирует все ошибки
    - Использует дефолт при проблеме
    
    Usage:
        cost = await get_shipping_cost_safe("Москва")
        print(f"Доставка: {cost} ₽")  # Всегда выведет число
    """
    
    try:
        cost, _ = await calculate_shipping(city)
        return cost
    except Exception as e:
        logger.error(f"Ошибка доставки для {city}: {e}")
        return default_cost


# ============ ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ============

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Пример 1: Простой расчет
        print("1️⃣ Простой расчет:")
        cost, desc = await calculate_shipping("Москва")
        print(f"  Москва: {cost} ₽ ({desc})\n")
        
        # Пример 2: Батч запрос
        print("2️⃣ Батч расчет:")
        results = await calculate_shipping_batch(["Москва", "Казань", "Екатеринбург"])
        for city, (cost, desc) in results.items():
            print(f"  {city}: {cost} ₽")
        
        # Пример 3: Безопасная функция
        print("\n3️⃣ Безопасный расчет:")
        cost = await get_shipping_cost_safe("Несуществующий город")
        print(f"  Стоимость: {cost} ₽ (дефолт, т.к. город не найден)")
    
    asyncio.run(main())
