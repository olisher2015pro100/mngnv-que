"""
🤖 TELEGRAM BOT ДЛЯ ИНТЕРНЕТ-МАГАЗИНА
Обработка заказов с интеграцией CDEK API v2.0
"""

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

# ==========================================
# 1️⃣ КОНФИГУРАЦИЯ
# ==========================================

# 🔧 ИСПОЛЬЗОВАТЬ ПРОКСИ? (для локального тестирования = False)
USE_PROXY = False
PROXY_URL = None if not USE_PROXY else os.getenv("PROXY_URL", "http://proxy.server:3128")

if PROXY_URL:
    print(f"✅ Прокси включен: {PROXY_URL}")
else:
    print("✅ Прокси ОТКЛЮЧЕН (прямое подключение)")

BOT_TOKEN = '8515886958:AAHoWf1mbESKzB03Vd6Aw3oGZrUY3SVb6dA'
MINI_APP_URL = 'https://olisher2015pro100.github.io/mngnv-que/'
ADMIN_ID = 1018181608

# ПУТЬ К БД
DB_PATH = os.path.join(os.path.dirname(__file__), 'orders.db')

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. ИНИЦИАЛИЗАЦИЯ
session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else AiohttpSession()
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# ==========================================
# 2️⃣ ФУНКЦИИ ДЛЯ РАБОТЫ С БД
# ==========================================

def init_db():
    """Инициализирует БД с полной схемой и миграцией"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Создаем таблицу с полной структурой
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT,
            email TEXT,
            phone TEXT,
            username TEXT,
            address TEXT,
            postal_code TEXT,
            city TEXT,
            item TEXT,
            size TEXT,
            price INTEGER,
            shipping_cost INTEGER,
            total INTEGER,
            chat_id TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    
    # 🔧 АВТОМАТИЧЕСКАЯ МИГРАЦИЯ: Добавляем новые колонки если их нет
    migration_columns = [
        ('email', 'TEXT'),
        ('postal_code', 'TEXT'),
        ('username', 'TEXT'),
        ('city', 'TEXT'),
        ('price', 'INTEGER'),
        ('shipping_cost', 'INTEGER'),
        ('size', 'TEXT'),
        ('address', 'TEXT'),
        ('total', 'INTEGER'),
        ('chat_id', 'TEXT'),
        ('date', 'TEXT')
    ]
    
    for col_name, col_type in migration_columns:
        try:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"✅ Колонка '{col_name}' добавлена в БД")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                pass  # Уже существует
            else:
                logger.warning(f"⚠️ {col_name}: {e}")
    
    conn.close()
    print("✅ БД инициализирована с полной схемой")


def save_order(fio, email, phone, username, address, postal_code, city, item, size, price, shipping_cost, total, chat_id):
    """Сохраняет заказ в БД со всеми полями"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    try:
        cursor.execute('''
            INSERT INTO orders 
            (fio, email, phone, username, address, postal_code, city, item, size, price, shipping_cost, total, chat_id, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fio, email, phone, username, address, postal_code, city, item, size, price, shipping_cost, total, chat_id, date))
        conn.commit()
        order_id = cursor.lastrowid
        logger.info(f"✅ Заказ #{order_id} сохранен в БД")
        return order_id
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении: {e}")
        return None
    finally:
        conn.close()


def get_all_orders():
    """Получает все заказы из БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, fio, email, phone, username, address, postal_code, city, item, size, price, shipping_cost, total, chat_id, date 
            FROM orders ORDER BY id DESC
        ''')
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Ошибка при получении заказов: {e}")
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
        success = cursor.rowcount > 0
        if success:
            logger.info(f"✅ Заказ #{order_id} удален")
        return success
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении: {e}")
        return False
    finally:
        conn.close()


def clear_all_orders():
    """Полностью очищает БД и сбрасывает счетчик ID до 1"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM orders')
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='orders'")
        conn.commit()
        logger.info("✅ БД очищена, счетчик ID сброшен на 1")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при очистке БД: {e}")
        return False
    finally:
        conn.close()


# ==========================================
# 3️⃣ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================

def get_val(data, *keys):
    """Получает значение из словаря по приоритету ключей"""
    for key in keys:
        val = data.get(key)
        if val and str(val).strip() and val != '—': 
            return str(val)
    return "—"


def format_order_tree(order_id, fio, email, phone, username, address, postal_code, city, item, size, price, shipping_cost, total, date):
    """Форматирует заказ в красивом древовидном формате"""
    tree = (
        f"<b>【 ЗАКАЗ #{order_id} 】</b>\n"
        f"└ 📱 <b>Модель:</b> {item}\n"
        f"└ 👤 <b>Клиент:</b> {fio}\n"
        f"└ 📧 <b>Почта:</b> {email}\n"
        f"└ 📞 <b>Тел:</b> {phone}\n"
        f"└ 🔗 <b>Связь:</b> @{username.replace('@', '')}\n"
        f"└ 📮 <b>Индекс:</b> {postal_code}\n"
        f"└ 📍 <b>Город:</b> {city}\n"
        f"└ 📏 <b>Размер:</b> {size}\n"
        f"└ 💵 <b>Товар:</b> {price}₽\n"
        f"└ 🚚 <b>Доставка:</b> {shipping_cost}₽\n"
        f"└ 💰 <b>ИТОГО:</b> <code>{total}₽</code>\n"
        f"└ 🕓 <b>Создано:</b> {date}\n"
        f"═══════════════════════════════"
    )
    return tree


# ==========================================
# 4️⃣ КОМАНДЫ БОТА
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start - приветствие"""
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛍️ открыть каталог 🛍️", web_app=WebAppInfo(url=MINI_APP_URL))]],
        resize_keyboard=True
    )
    await message.answer(
        "🔥 <b>Добро пожаловать в mngnv shop!</b>\n\n"
        "Выбери товар и оформи заказ через каталог 👇",
        parse_mode="HTML", 
        reply_markup=markup
    )


@dp.message(Command("cmd"))
async def cmd_help(message: types.Message):
    """Команда /cmd - справка для администратора"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа!")
        return
    
    help_text = (
        "🤖 <b>ПАНЕЛЬ АДМИНИСТРАТОРА:</b>\n\n"
        "📋 <b>Просмотр заказов:</b>\n"
        "• /base — Все заказы\n"
        "• /base [число] — Последние N заказов (например: /base 5)\n\n"
        "🗑️ <b>Управление:</b>\n"
        "• /delete [номер] — Удалить заказ (например: /delete 3)\n"
        "• /baseclearall — ПОЛНАЯ очистка БД (счетчик → 1)\n\n"
        "ℹ️ /cmd — Это меню"
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("base"))
async def cmd_base(message: types.Message):
    """Команда /base - показывает все заказы"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен!")
        return
    
    # Параметр для количества последних заказов
    args = message.text.split()
    limit = int(args[1]) if len(args) > 1 else 0
    
    orders = get_all_orders()
    if limit > 0:
        orders = orders[:limit]
    
    if not orders:
        await message.answer("📦 Заказов в базе нет!")
        return
    
    text = f"📊 <b>ЗАКАЗЫ ({len(orders)} шт):</b>\n\n"
    
    for order in orders:
        (order_id, fio, email, phone, username, address, postal_code, city,
         item, size, price, shipping_cost, total, chat_id, date) = order
        
        tree = format_order_tree(
            order_id, fio, email, phone, username, 
            address, postal_code, city, item, size,
            price or 0, shipping_cost or 0, total, date
        )
        text += tree + "\n\n"
    
    # Если текст слишком большой, разбиваем на части
    if len(text) > 4000:
        messages = text.split("═══════════════════════════════\n\n")
        for msg in messages:
            if msg.strip():
                try:
                    await message.answer(msg[:4000], parse_mode="HTML")
                    await asyncio.sleep(0.5)
                except:
                    pass
    else:
        await message.answer(text, parse_mode="HTML")


@dp.message(Command("delete"))
async def cmd_delete(message: types.Message):
    """Команда /delete [номер] - удаляет заказ по ID"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Формат: /delete [номер]\nПример: /delete 5")
        return
    
    try:
        order_id = int(args[1])
        if delete_order(order_id):
            await message.answer(f"✅ Заказ #{order_id} удален!")
        else:
            await message.answer(f"❌ Заказ #{order_id} не найден!")
    except ValueError:
        await message.answer("❌ Номер должен быть числом!")


@dp.message(Command("baseclearall"))
async def cmd_baseclearall(message: types.Message):
    """Команда /baseclearall - ПОЛНАЯ очистка БД"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен!")
        return
    
    if clear_all_orders():
        await message.answer("✅ БД полностью очищена!\nСчетчик ID сброшен на 1")
    else:
        await message.answer("❌ Ошибка при очистке БД!")


# ==========================================
# 5️⃣ ОБРАБОТЧИК СКРИНШОТОВ
# ==========================================

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    """Обработчик скриншотов оплаты"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "не указано"
        photo = message.photo[-1]
        
        caption = f"💰 Скриншот оплаты от @{username} (ID: {user_id})"
        await bot.send_photo(ADMIN_ID, photo.file_id, caption=caption, parse_mode="HTML")
        
        await message.answer("✅ Скриншот получен! Менеджер проверит и свяжется с тобой.")
        logger.info(f"📸 Скриншот от @{username}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка скриншота: {e}")
        await message.answer("❌ Ошибка обработки. Попробуй еще раз.")


# ==========================================
# 6️⃣ ОБРАБОТЧИК WEB APP (ГЛАВНЫЙ)
# ==========================================

@dp.message()
async def handle_order(message: types.Message):
    """Обработчик заказов из Web App"""
    if not message.web_app_data:
        return
    
    try:
        data = json.loads(message.web_app_data.data)
        
        # ПОДРОБНЫЕ ЛОГИ
        print("\n" + "="*80)
        print("📥 ДАННЫЕ ИЗ WEB APP:")
        print("="*80)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("="*80 + "\n")
        
        # Извлекаем данные с fallback на разные ключи
        fio = get_val(data, 'customer', 'fio', 'name', 'full_name')
        email = get_val(data, 'email', 'mail', 'user_email')
        phone = get_val(data, 'phone', 'tel')
        username = get_val(data, 'tg_user', 'username', 'tg')
        address = get_val(data, 'address', 'addr')
        postal_code = get_val(data, 'postal_code', 'index', 'idx')
        item = get_val(data, 'item', 'product', 'title')
        size = get_val(data, 'size', 'variant')
        price = int(data.get('price', 0))
        
        # Получаем город для расчета доставки
        city = get_val(data, 'shipping_city', 'city')
        print(f"🏙️ Город заказа: '{city}'")
        
        # 🚚 РАССЧИТЫВАЕМ ДОСТАВКУ СДЭК
        shipping_cost = 500  # Дефолт
        
        if city and city != "—":
            try:
                from cdek_integration import calculate_shipping
                
                print("\n" + "="*80)
                print("🚚 РАСЧЕТ ДОСТАВКИ СДЭК")
                print("="*80)
                print(f"   🏙️  Город: '{city}'")
                print(f"   📞 Вызов: calculate_shipping()")
                
                shipping_cost, ship_desc = await calculate_shipping(city)
                
                print(f"   ✅ РЕЗУЛЬТАТ: {shipping_cost}₽")
                print(f"   📝 Описание: {ship_desc}")
                print("="*80 + "\n")
                
            except Exception as e:
                logger.error(f"⚠️ ОШИБКА СДЭК: {e}")
                print(f"⚠️ Ошибка при расчете, используем дефолт 500₽\n")
                shipping_cost = 500
        
        total = price + shipping_cost
        
        # СОХРАНЯЕМ ЗАКАЗ В БД
        chat_id = str(message.from_user.id)
        order_id = save_order(
            fio, email, phone, username, address, postal_code, city,
            item, size, price, shipping_cost, total, chat_id
        )
        
        if not order_id:
            await message.answer("❌ Ошибка при сохранении. Попробуй позже.")
            return
        
        # ЧЕК ДЛЯ КЛИЕНТА в формате "дерева"
        receipt = (
            f"✅ <b>Заказ принят!</b>\n\n"
            f"<b>【 ЗАКАЗ #{order_id} 】</b>\n"
            f"└ 📱 <b>Модель:</b> {item}\n"
            f"└ 📏 <b>Размер:</b> {size}\n"
            f"└ 💵 <b>Товар:</b> {price}₽\n"
            f"└ 🚚 <b>Доставка:</b> {shipping_cost}₽\n"
            f"└ 💰 <b>ИТОГО:</b> <code>{total}₽</code>\n"
            f"═══════════════════════════════\n\n"
            f"👤 <b>Твои данные:</b>\n"
            f"• ФИО: {fio}\n"
            f"• Почта: {email}\n"
            f"• Тел: {phone}\n"
            f"• Адрес: {address}\n"
            f"• Индекс: {postal_code}\n"
            f"• Город: {city}\n\n"
            f"💳 <b>Оплата:</b>\n"
            f"<code>2204 3211 2754 4542</code>\n"
            f"Сбербанк (Ozon)\n\n"
            f"🙏 <b>Отправь скриншот чека!</b>"
        )
        await message.answer(receipt, parse_mode="HTML")
        
        # УВЕДОМЛЕНИЕ АДМИНУ в формате "дерева"
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        admin_tree = format_order_tree(
            order_id, fio, email, phone, username, address,
            postal_code, city, item, size, price, shipping_cost, total, now
        )
        
        admin_alert = (
            f"🚀 <b>✨ НОВЫЙ ЗАКАЗ! ✨</b>\n\n{admin_tree}\n\n"
            f"⏳ <b>Статус:</b> Ожидание оплаты"
        )
        
        await bot.send_message(ADMIN_ID, admin_alert, parse_mode="HTML")
        logger.info(f"📦 Заказ #{order_id} создан от {fio}")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга JSON: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка обработки заказа: {e}")
        import traceback
        traceback.print_exc()


# ==========================================
# 7️⃣ ЗАПУСК
# ==========================================

async def main():
    """Главная функция запуска"""
    init_db()
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  🤖 БОТ MNGNV SHOP ЗАПУСКАЕТСЯ".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    print(f"✅ Admin ID: {ADMIN_ID}")
    print(f"✅ Mini App URL: {MINI_APP_URL}")
    print(f"✅ Прокси: {'🟢 ВКЛЮЧЕН' if USE_PROXY else '🔴 ОТКЛЮЧЕН (прямое подключение)'}")
    print(f"✅ БД: {DB_PATH}")
    print("█"*80)
    print()
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
