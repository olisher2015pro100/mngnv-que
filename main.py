import os
import json
import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.client.session.aiohttp import AiohttpSession
import aiohttp
import base64

# 1. НАСТРОЙКИ
PROXY_URL = "http://proxy.server:3128"
BOT_TOKEN = '8515886958:AAHWLWjmGtFj9BsUleOSsqZCaoN7NxdBHf4'
MINI_APP_URL = 'https://olisher2015pro100.github.io/mngnv-que/'
ADMIN_ID = 1018181608

# ПУТЬ К БД
DB_PATH = os.path.join(os.path.dirname(__file__), 'orders.db')

# СДЭК API v2.0
CDEK_CLIENT_ID = '4I5vLAbLUPdMIOEhVD0osn4fS0fvTttj'
CDEK_CLIENT_SECRET = 'g1WXBI56G3ZAPrY0TleKblVIwsnMCm8J'
CDEK_SENDER_CITY_CODE = 541  # Улан-Удэ
CDEK_TARIFF_CODE = 136  # Посылка склад-склад
CDEK_DEFAULT_SHIPPING = 500  # Страховка при ошибке
CDEK_API_URL = "https://api.cdek.ru/v2"

# Параметры посылки
PACKAGE_WEIGHT = 800  # граммы
PACKAGE_LENGTH = 30  # см
PACKAGE_WIDTH = 25   # см
PACKAGE_HEIGHT = 10  # см

# 2. ИНИЦИАЛИЗАЦИЯ (сначала создаем объекты, потом используем!)
session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# 3. ФУНКЦИИ ДЛЯ РАБОТЫ С БД
def init_db():
    """Инициализирует БД и создает таблицу, если её нет"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            idx TEXT,
            item TEXT,
            size TEXT,
            total INTEGER,
            tg_user TEXT,
            chat_id TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_order(fio, phone, email, address, idx, item, size, total, tg_user, chat_id):
    """Сохраняет заказ в БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    try:
        cursor.execute('''
            INSERT INTO orders (fio, phone, email, address, idx, item, size, total, tg_user, chat_id, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fio, phone, email, address, idx, item, size, total, tg_user, chat_id, date))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Ошибка при сохранении заказа: {e}")
        return None
    finally:
        conn.close()

def get_all_orders():
    """Получает все заказы из БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, fio, phone, email, address, idx, item, size, total, tg_user, chat_id, date FROM orders ORDER BY id DESC')
        orders = cursor.fetchall()
        return orders
    except Exception as e:
        print(f"Ошибка при получении заказов: {e}")
        return []
    finally:
        conn.close()

def delete_order(order_id):
    """Удаляет заказ по ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Ошибка при удалении заказа: {e}")
        return False
    finally:
        conn.close()

def clear_all_orders():
    """Полностью очищает таблицу заказов и сбрасывает счетчик ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM orders')
        # Сбрасываем счетчик ID, чтобы новые заказы начинались с 1
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='orders'")
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при очистке таблицы: {e}")
        return False
    finally:
        conn.close()

# 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def get_val(data, *keys):
    for key in keys:
        val = data.get(key)
        if val and str(val).strip() and val != '—': 
            return val
    return "—"

def find_index(data):
    # Пробуем все возможные ключи для индекса
    keys = ['index', 'postcode', 'zip', 'zip_code', 'postal', 'postIndex', 'post_index', 'p_code']
    for k in keys:
        if data.get(k): return data.get(k)
    # Если не нашли по ключу, ищем любое значение из 6 цифр
    for v in data.values():
        if str(v).isdigit() and len(str(v)) == 6: return v
    return "—"

# 4.1 ФУНКЦИИ ДЛЯ РАБОТЫ С СДЭК API v2.0
async def get_cdek_token():
    """Получает временный токен доступа для СДЭК API v2.0"""
    try:
        auth_string = f"{CDEK_CLIENT_ID}:{CDEK_CLIENT_SECRET}"
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
        
        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{CDEK_API_URL}/auth/account", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get('access_token')
                    print(f"✅ [СДЭК] Токен получен")
                    return token
                else:
                    print(f"❌ [СДЭК] Ошибка авторизации: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ [СДЭК] Ошибка при получении токена: {e}")
        return None

async def get_city_code(postal_code):
    """Получает внутренний код города СДЭК по индексу"""
    try:
        token = await get_cdek_token()
        if not token:
            print(f"❌ [СДЭК] Не удалось получить токен для поиска города")
            return None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Параметры для поиска по индексу
        params = {
            "postal_code": postal_code,
            "country_code": "RU"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CDEK_API_URL}/location/cities", headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('items') and len(data['items']) > 0:
                        city_code = data['items'][0].get('code')
                        city_name = data['items'][0].get('city')
                        print(f"✅ [СДЭК] Код города найден: {city_name} (код: {city_code})")
                        return city_code
                    else:
                        print(f"❌ [СДЭК] Город с индексом {postal_code} не найден")
                        return None
                else:
                    print(f"❌ [СДЭК] Ошибка при поиске города: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ [СДЭК] Ошибка при получении кода города: {e}")
        return None

async def calculate_shipping(city_to_code):
    """Рассчитывает стоимость доставки до города"""
    try:
        if not city_to_code:
            print(f"⚠️ [СДЭК] Код города не указан")
            return CDEK_DEFAULT_SHIPPING
        
        token = await get_cdek_token()
        if not token:
            print(f"❌ [СДЭК] Не удалось получить токен для расчета")
            return CDEK_DEFAULT_SHIPPING
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Параметры расчета доставки
        payload = {
            "from_location": {
                "code": CDEK_SENDER_CITY_CODE
            },
            "to_location": {
                "code": city_to_code
            },
            "packages": [
                {
                    "weight": PACKAGE_WEIGHT,
                    "length": PACKAGE_LENGTH,
                    "width": PACKAGE_WIDTH,
                    "height": PACKAGE_HEIGHT
                }
            ],
            "tariff_code": CDEK_TARIFF_CODE
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{CDEK_API_URL}/calculator/tarifflist", 
                                   headers=headers, 
                                   json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('result') and len(data['result']) > 0:
                        delivery_cost = int(data['result'][0].get('price', CDEK_DEFAULT_SHIPPING))
                        print(f"✅ [СДЭК] Цена доставки: {delivery_cost}₽")
                        return delivery_cost
                    else:
                        print(f"⚠️ [СДЭК] Нет результатов расчета, используется страховка {CDEK_DEFAULT_SHIPPING}₽")
                        return CDEK_DEFAULT_SHIPPING
                else:
                    print(f"❌ [СДЭК] Ошибка при расчете доставки: {response.status}")
                    return CDEK_DEFAULT_SHIPPING
    except Exception as e:
        print(f"❌ [СДЭК] Ошибка при расчете доставки: {e}")
        return CDEK_DEFAULT_SHIPPING

# 5. ОБРАБОТЧИКИ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛍️ открыть каталог 🛍️", web_app=WebAppInfo(url=MINI_APP_URL))]],
        resize_keyboard=True
    )
    await message.answer("🔥 <b>Добро пожаловать в mngnv shop!</b>", parse_mode="HTML", reply_markup=markup)

@dp.message(Command("cmd"))
async def cmd_help(message: types.Message):
    """Команда /cmd - справка для админа"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа к этой команде!")
        return
    
    help_text = (
        "🤖 <b>Панель управления менеджера:</b>\n\n"
        "• /start — Перезапуск бота.\n"
        "• /base — Показать все заказы из базы.\n"
        "• /baseclear [номер] (например: /baseclear 2) — Удаление конкретного заказа.\n"
        "• /baseclearall — Полная очистка базы (внимание!).\n"
        "• /cmd — Вызов этого меню."
    )
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("base"))
async def cmd_base(message: types.Message):
    """Команда /base - выводит все заказы (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа к этой команде!")
        return
    
    orders = get_all_orders()
    if not orders:
        await message.answer("📦 Заказов в базе нет!")
        return
    
    text = "📊 <b>ВСЕ ЗАКАЗЫ:</b>\n\n"
    for idx, (order_id, fio, phone, email, address, postal_idx, item, size, total, tg_user, chat_id, date) in enumerate(orders, 1):
        text += f"<b>{idx}. Заказ #{order_id}</b>\n"
        text += f"└ 👤 ФИО: {fio}\n"
        text += f"└ 📞 Тел: {phone}\n"
        text += f"└ 📧 Почта: {email}\n"
        text += f"└ 📍 Адрес: {address}\n"
        text += f"└ 📮 Индекс: {postal_idx}\n"
        text += f"└ 👕 Товар: {item}\n"
        text += f"└ 📏 Размер: {size}\n"
        text += f"└ 💰 Итого к оплате: {total}₽\n"
        text += f"└ 🔗 Связь: @{tg_user.replace('@','')}\n"
        text += f"└ 🆔 Chat ID: {chat_id}\n"
        text += f"└ 🕓 Дата: {date}\n"
        text += "════════════════════════════\n\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("baseclear"))
async def cmd_baseclear(message: types.Message):
    """Команда /baseclear [номер] - удаляет заказ по ID"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа к этой команде!")
        return
    
    # Получаем аргументы команды
    args = message.text.split()
    
    # Проверяем, передан ли номер заказа
    if len(args) < 2:
        await message.answer("⚠️ Ошибка! Введи номер заказа, например: /baseclear 2")
        return
    
    # Пытаемся получить ID из второго аргумента
    try:
        order_id = int(args[1])
    except ValueError:
        await message.answer("⚠️ Ошибка! Номер заказа должен быть числом, например: /baseclear 2")
        return
    
    # Удаляем заказ
    if delete_order(order_id):
        await message.answer(f"✅ Заказ #{order_id} успешно удален!")
    else:
        await message.answer(f"❌ Заказ #{order_id} не найден!")

@dp.message(Command("baseclearall"))
async def cmd_baseclearall(message: types.Message):
    """Команда /baseclearall - полностью очищает таблицу"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа к этой команде!")
        return
    
    clear_all_orders()
    await message.answer("✅ Таблица заказов полностью очищена!")

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    """Обработчик для скриншотов оплаты от клиентов"""
    try:
        # Получаем информацию о пользователе
        user_id = message.from_user.id
        username = message.from_user.username or "не указано"
        
        # Получаем самое качественное фото (последнее в списке)
        photo = message.photo[-1]
        
        # Переслаем фото админу с сопроводительным текстом
        caption = f"💰 Получен скриншот оплаты от пользователя @{username} (ID: {user_id})"
        await bot.send_photo(ADMIN_ID, photo.file_id, caption=caption, parse_mode="HTML")
        
        # Ответим пользователю подтверждением
        await message.answer(
            "✅ Скриншот получен! Менеджер проверит оплату в ближайшее время и свяжется с тобой."
        )
        
        print(f"✅ Скриншот от пользователя @{username} (ID: {user_id}) переслан админу")
        
    except Exception as e:
        print(f"Ошибка при обработке скриншота: {e}")
        await message.answer("❌ Ошибка при обработке скриншота. Попробуй еще раз.")

@dp.message()
async def handle_order(message: types.Message):
    if message.web_app_data:
        try:
            d = json.loads(message.web_app_data.data)
            
            # ЛОГИ ДЛЯ ПРОВЕРКИ В БАШ
            print("\n--- ПРИШЛИ ДАННЫЕ ---")
            print(json.dumps(d, indent=2, ensure_ascii=False))
            print("----------------------\n")

            # Извлекаем всё
            fio = get_val(d, 'customer', 'fio', 'name', 'full_name')
            phone = get_val(d, 'phone', 'tel')
            email = get_val(d, 'email', 'mail', 'user_email', 'e-mail')
            addr = get_val(d, 'address', 'addr')
            idx = find_index(d)
            tg = get_val(d, 'tg_user', 'username', 'tg')
            item = get_val(d, 'item', 'product')
            size = get_val(d, 'size', 'variant')
            price = int(d.get('price', 0))
            
            # РАСЧЕТ ДОСТАВКИ ЧЕРЕЗ СДЭК
            print(f"\n📍 [ДОСТАВКА] Начинаю расчет для индекса: {idx}")
            
            # Получаем код города СДЭК по индексу
            if idx and idx != "—":
                city_code = await get_city_code(idx)
                if city_code:
                    # Рассчитываем стоимость доставки
                    ship = await calculate_shipping(city_code)
                else:
                    print(f"⚠️ [ДОСТАВКА] Город не найден по индексу {idx}, используется страховка {CDEK_DEFAULT_SHIPPING}₽")
                    ship = CDEK_DEFAULT_SHIPPING
            else:
                print(f"⚠️ [ДОСТАВКА] Индекс не указан, используется страховка {CDEK_DEFAULT_SHIPPING}₽")
                ship = CDEK_DEFAULT_SHIPPING
            
            total = price + ship
            print(f"💰 [ИТОГО] Цена товара: {price}₽ + Доставка: {ship}₽ = {total}₽\n")

            # СОХРАНЯЕМ ЗАКАЗ В БД
            chat_id = str(message.from_user.id)
            order_id = save_order(fio, phone, email, addr, idx, item, size, total, tg, chat_id)
            if order_id:
                print(f"✅ Заказ #{order_id} сохранен в БД")

            receipt = (
                f"✅ <b>Заказ получен!</b>\n\n"
                f"📦 <b>Товар:</b> {item}\n"
                f"📏 <b>Размер:</b> {size}\n"
                f"💰 <b>Цена товара:</b> {price:,} руб\n"
                f"🚚 <b>Доставка:</b> {ship:,} руб\n"
                f"<b>Итого к оплате:</b> {total:,} руб\n\n"
                f"👤 <b>твои данные:</b>\n"
                f"• ФИО: {fio}\n"
                f"• Телефон: {phone}\n"
                f"• Почта: {email}\n"
                f"• Адрес: {addr}\n"
                f"• Индекс: {idx}\n"
                f"• TG: @{tg.replace('@','')}\n\n"
                f"📍 <b>Реквизиты для оплаты:</b>\n"
                f"<code>2204 3211 2754 4542</code> (Ozon Банк)\n\n"
                f"🙏 Пришли скрин чека в ответ на это сообщение!"
            )
            await message.answer(receipt, parse_mode="HTML")

            admin_alert = (
                f"🚀 <b>НОВЫЙ ЗАКАЗ!</b> (#{order_id})\n\n"
                f"👤 ФИО: {fio}\n📱 тел: {phone}\n📧 почта: {email}\n"
                f"📍 адрес: {addr}\n📮 индекс: {idx}\n👕 товар: {item}\n"
                f"📏 размер: {size}\n💰 итого: {total:,}\n🔗 связь: @{tg.replace('@','')}"
            )
            await bot.send_message(ADMIN_ID, admin_alert, parse_mode="HTML")

        except Exception as e:
            print(f"Ошибка в handle_order: {e}")

# 6. ЗАПУСК
async def main():
    init_db()  # Инициализируем БД при запуске
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
