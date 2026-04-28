"""
🤖 TELEGRAM BOT ДЛЯ ИНТЕРНЕТ-МАГАЗИНА
Обработка заказов с интеграцией CDEK API v2.0
"""

import os
import json
import html
import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    BotCommand,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from colorama import init, Fore, Style

# ==== CONFIGURATION ====
DELIVERY_PRICE = 500
SHOP_NAME = "mngnv shop"

# Эта строка "включает" поддержку цветов в Windows
init(autoreset=True)

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
MANAGER_TELEGRAM_URL = "tg://resolve?domain=mngnv"

# ПУТЬ К БД
DB_PATH = os.path.join(os.path.dirname(__file__), 'orders.db')

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. ИНИЦИАЛИЗАЦИЯ
session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else AiohttpSession()
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())


# ==========================================
# FSM (трек-номер для админа)
# ==========================================


class AdminStates(StatesGroup):
    waiting_track = State()


def status_label_ru(status: str | None) -> str:
    """Короткая подпись статуса (алерты, подписи вне дерева чека)."""
    s = (status or "new").lower()
    return {
        "new": "⏳ Ожидает подтверждения",
        "confirmed": "✅ Подтвержден",
        "sent": "📦 Отправлен",
        "cancelled": "❌ Отменен",
    }.get(s, s)


def order_status_tree_lines(status: str | None, tracking_number: str | None = None) -> str:
    """Строки статуса (и трека для sent) в стиле дерева format_order_tree."""
    if status is None:
        return ""
    s = (status or "new").lower()
    lines_map = {
        "new": "└ 📋 <b>Статус:</b> ⏳ Ожидает подтверждения\n",
        "confirmed": "└ 📋 <b>Статус:</b> ✅ Подтвержден\n",
        "cancelled": "└ 📋 <b>Статус:</b> ❌ Отменен\n",
        "sent": "└ 📋 <b>Статус:</b> 📦 Отправлен\n",
    }
    out = lines_map.get(s, f"└ 📋 <b>Статус:</b> {html.escape(str(status))}\n")
    if s == "sent" and tracking_number and str(tracking_number).strip():
        out += (
            "└ 🔢 <b>Трек-номер:</b> "
            f"<code>{html.escape(str(tracking_number).strip())}</code>\n"
        )
    return out

# ==========================================
# 2️⃣ ФУНКЦИИ ДЛЯ РАБОТЫ С БД
# ==========================================

def init_db():
    """Инициализирует БД с полной схемой и миграцией"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
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
            date TEXT,
            status TEXT DEFAULT 'new',
            is_visible INTEGER DEFAULT 1,
            tracking_number TEXT
        )
        """
    )
    conn.commit()

    migration_columns = [
        ("email", "TEXT"),
        ("postal_code", "TEXT"),
        ("username", "TEXT"),
        ("city", "TEXT"),
        ("price", "INTEGER"),
        ("shipping_cost", "INTEGER"),
        ("size", "TEXT"),
        ("address", "TEXT"),
        ("total", "INTEGER"),
        ("chat_id", "TEXT"),
        ("date", "TEXT"),
        ("status", "TEXT DEFAULT 'new'"),
        ("is_visible", "INTEGER DEFAULT 1"),
        ("tracking_number", "TEXT"),
    ]

    for col_name, col_def in migration_columns:
        try:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}")
            conn.commit()
            print(Fore.GREEN + f"✅ Колонка '{col_name}' добавлена в БД" + Style.RESET_ALL)
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                logger.warning(f"⚠️ {col_name}: {e}")

    # На случай старых строк без статуса / видимости
    try:
        cursor.execute("UPDATE orders SET status = 'new' WHERE status IS NULL OR TRIM(status) = ''")
        cursor.execute("UPDATE orders SET is_visible = 1 WHERE is_visible IS NULL")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.close()
    print(Fore.CYAN + "✅ БД инициализирована с полной схемой" + Style.RESET_ALL)


def save_order(fio, email, phone, username, address, postal_code, city, item, size, price, shipping_cost, total, chat_id):
    """Сохраняет заказ в БД со всеми полями"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    try:
        cursor.execute(
            """
            INSERT INTO orders
            (fio, email, phone, username, address, postal_code, city, item, size, price, shipping_cost, total, chat_id, date, status, is_visible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', 1)
            """,
            (
                fio,
                email,
                phone,
                username,
                address,
                postal_code,
                city,
                item,
                size,
                price,
                shipping_cost,
                total,
                chat_id,
                date,
            ),
        )
        conn.commit()
        order_id = cursor.lastrowid
        logger.info(f"✅ Заказ #{order_id} сохранен в БД")
        return order_id
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении: {e}")
        return None
    finally:
        conn.close()


_ORDER_SELECT = """
    SELECT id, fio, email, phone, username, address, postal_code, city, item, size,
           price, shipping_cost, total, chat_id, date, status, is_visible, tracking_number
    FROM orders
"""


def get_all_orders(ascending: bool = True):
    """Все заказы из БД. По умолчанию от старых к новым (ASC)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    order = "ASC" if ascending else "DESC"
    try:
        cursor.execute(_ORDER_SELECT + f" ORDER BY id {order}")
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Ошибка при получении заказов: {e}")
        return []
    finally:
        conn.close()


def get_orders_paginated(page: int, per_page: int = 5):
    """Вернуть страницу заказов для админа (LIMIT/OFFSET)."""
    if page < 1:
        page = 1
    offset = (page - 1) * per_page
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            _ORDER_SELECT + " ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        )
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Ошибка пагинации заказов: {e}")
        return []
    finally:
        conn.close()


def get_total_orders_count() -> int:
    """Общее количество заказов в БД."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM orders")
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    except Exception as e:
        logger.error(f"❌ Ошибка подсчета заказов: {e}")
        return 0
    finally:
        conn.close()


def get_admin_base_list_orders(ascending: bool = True):
    """
    Список для /base без аргументов: все заказы, кроме завершённых
    (sent / cancelled не показываем — для админа «исчезают» из общего списка).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    order = "ASC" if ascending else "DESC"
    # В админской очереди показываем только "в работе".
    # Поддерживаем и англ. статусы в БД, и русские (если где-то были записаны вручную).
    where = """
    WHERE lower(coalesce(nullif(trim(status), ''), 'new')) NOT IN ('sent', 'cancelled', 'отправлен', 'отменен', 'отменён')
    """
    try:
        cursor.execute(_ORDER_SELECT + where + f" ORDER BY id {order}")
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка /base: {e}")
        return []
    finally:
        conn.close()


def get_order_by_id(order_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(_ORDER_SELECT + " WHERE id = ?", (order_id,))
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"❌ Ошибка при получении заказа #{order_id}: {e}")
        return None
    finally:
        conn.close()


def get_user_visible_orders(chat_id: str):
    """Заказы пользователя с is_visible=1 (включая sent); старые сверху, новые внизу."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            _ORDER_SELECT + " WHERE chat_id = ? AND is_visible = 1 ORDER BY id ASC",
            (str(chat_id),),
        )
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Ошибка при получении заказов пользователя: {e}")
        return []
    finally:
        conn.close()


def set_user_orders_visibility(chat_id: str, visible: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE orders SET is_visible = ? WHERE chat_id = ?",
            (visible, str(chat_id)),
        )
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении видимости заказов: {e}")
        return 0
    finally:
        conn.close()


def update_order_status(order_id: int, status: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        conn.commit()
        ok = cursor.rowcount > 0
        if ok:
            logger.info(f"✅ Заказ #{order_id} → статус '{status}'")
        return ok
    except Exception as e:
        logger.error(f"❌ Ошибка статуса заказа #{order_id}: {e}")
        return False
    finally:
        conn.close()


def set_order_sent_with_tracking(order_id: int, tracking: str) -> bool:
    """Статус sent + сохранение трек-номера в БД."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE orders SET status = 'sent', tracking_number = ? WHERE id = ?",
            (tracking.strip(), order_id),
        )
        conn.commit()
        ok = cursor.rowcount > 0
        if ok:
            logger.info(f"✅ Заказ #{order_id} → sent, трек сохранён")
        return ok
    except Exception as e:
        logger.error(f"❌ Ошибка sent/трек для заказа #{order_id}: {e}")
        return False
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


def format_order_tree(
    order_id,
    fio,
    email,
    phone,
    username,
    address,
    postal_code,
    city,
    item,
    size,
    price,
    shipping_cost,
    total,
    date,
    status=None,
    tracking_number=None,
):
    """Форматирует заказ в красивом древовидном формате"""
    uname = username.replace("@", "") if username and str(username).strip() not in ("", "—") else "—"
    status_line = order_status_tree_lines(status, tracking_number)
    tree = (
        f"<b>【 ЗАКАЗ #{order_id} 】</b>\n"
        f"└ 👕 <b>Товар:</b> {item}\n"
        f"└ 👤 <b>Клиент:</b> {fio}\n"
        f"└ 📧 <b>Почта:</b> {email}\n"
        f"└ 📞 <b>Тел:</b> {phone}\n"
        f"└ 🔗 <b>Связь:</b> @{uname}\n"
        f"└ 📮 <b>Индекс:</b> {postal_code}\n"
        f"└ 📍 <b>Город:</b> {city}\n"
        f"└ 📏 <b>Размер:</b> {size}\n"
        f"└ 💵 <b>Стоимость товара:</b> {price}₽\n"
        f"└ 🚚 <b>Доставка:</b> {shipping_cost}₽\n"
        f"└ 💰 <b>ИТОГО:</b> <code>{total}₽</code>\n"
        f"{status_line}"
        f"└ 🕓 <b>Создано:</b> {date}\n"
        f"═══════════════════════════════"
    )
    return tree


def build_admin_order_keyboard(order_id: int, status: str | None) -> InlineKeyboardMarkup | None:
    s = (status or "new").lower()
    if s == "new":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_cf:{order_id}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data=f"adm_cn:{order_id}"),
                ],
            ]
        )
    if s == "confirmed":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📦 Отправить", callback_data=f"adm_sd:{order_id}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data=f"adm_cn:{order_id}"),
                ],
            ]
        )
    return None


async def send_long_html(message: types.Message, text: str):
    """Дробит длинный HTML на части ≤ 4000 символов."""
    max_len = 4000
    if len(text) <= max_len:
        await message.answer(text, parse_mode="HTML")
        return
    chunk = ""
    for line in text.split("\n"):
        line = line + "\n"
        if len(chunk) + len(line) > max_len:
            if chunk.strip():
                await message.answer(chunk[:max_len], parse_mode="HTML")
                await asyncio.sleep(0.35)
            chunk = line
        else:
            chunk += line
    if chunk.strip():
        await message.answer(chunk[:max_len], parse_mode="HTML")


def get_orders_text(page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    per_page = 8
    # В общем списке админа показываем только активные (new/confirmed).
    # Завершённые (sent/cancelled) не удаляем из БД — они остаются в истории клиента.
    all_orders = get_admin_base_list_orders(ascending=True)
    total_orders = len(all_orders)
    if total_orders == 0:
        return "📋 Заказы:\n\n📭 Заказов больше нет.", None

    total_pages = max(1, (total_orders + per_page - 1) // per_page)

    page = max(0, min(page, total_pages - 1))

    # Если после изменения статуса текущая страница "опустела" — откатываемся назад.
    while page > 0:
        start_index = page * per_page
        end_index = start_index + per_page
        if all_orders[start_index:end_index]:
            break
        page -= 1

    start_index = page * per_page
    end_index = start_index + per_page
    orders_slice = all_orders[start_index:end_index]

    message_text = f"📋 Заказы (Страница {page + 1} из {total_pages}):\n\n"
    if not orders_slice:
        message_text += "📭 Заказов больше нет."
    else:
        separator = "_________________________"
        for row in orders_slice:
            (
                oid,
                fio,
                email,
                phone,
                username,
                address,
                postal_code,
                city,
                item,
                size,
                price,
                shipping_cost,
                total,
                _chat_id,
                date,
                status,
                _vis,
                _track,
            ) = row
            uname = (
                str(username).replace("@", "").strip()
                if username and str(username).strip() not in ("", "—")
                else "—"
            )
            message_text += (
                f"【 <b>ЗАКАЗ #{oid}</b> 】\n"
                f"└ 👕 <b>Товар:</b> {item}\n"
                f"└ 👤 <b>Клиент:</b> {fio}\n"
                f"└ 📧 <b>Почта:</b> {email}\n"
                f"└ 📞 <b>Тел:</b> {phone}\n"
                f"└ 🔗 <b>Связь:</b> @{uname}\n"
                f"└ 📮 <b>Индекс:</b> {postal_code}\n"
                f"└ 📍 <b>Город:</b> {city}\n"
                f"└ 📏 <b>Размер:</b> {size}\n"
                f"└ 💵 <b>Стоимость товара:</b> {int(price or 0)}₽\n"
                f"└ 🚚 <b>Доставка:</b> {int(shipping_cost or 0)}₽\n"
                f"└ 💰 <b>ИТОГО:</b> <code>{int(total or 0)}₽</code>\n"
                f"└ 📋 <b>Статус:</b> {status_label_ru(status)}\n"
                f"└ 🕓 <b>Создано:</b> {date}\n"
                f"{separator}\n\n"
            )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_view:{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_view:{page + 1}"))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[nav_buttons]) if nav_buttons else None

    return message_text.strip(), keyboard


def _extract_page_from_admin_list(text: str | None) -> int:
    """
    Достаём текущую страницу из текста '📋 Заказы (Страница X из Y):'
    Возвращаем 0-based page. Если не нашли — 0.
    """
    if not text:
        return 0
    try:
        # пример: "📋 Заказы (Страница 2 из 6):"
        if "Страница" not in text:
            return 0
        chunk = text.split("Страница", 1)[1]
        x = chunk.strip().split()[0]
        return max(0, int(x) - 1)
    except Exception:
        return 0


async def _refresh_admin_queue_message(message: types.Message, preferred_page: int | None = None):
    """
    Обновить текущее сообщение админа на актуальную очередь (/base) без спама.
    """
    page = preferred_page if preferred_page is not None else _extract_page_from_admin_list(getattr(message, "text", None))
    text, kb = get_orders_text(page)
    await message.edit_text(text, parse_mode="HTML", reply_markup=kb)


# ==========================================
# 4️⃣ КОМАНДЫ БОТА
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start — главное меню"""
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍️ Каталог", web_app=WebAppInfo(url=MINI_APP_URL))],
            [KeyboardButton(text="👤 Личный кабинет")],
            [KeyboardButton(text="🆘 Поддержка / Менеджер")],
        ],
        resize_keyboard=True,
    )
    await message.answer(
        f"🔥 <b>{SHOP_NAME}</b>\n\n"
        "• <b>Каталог</b> — выбери товар и оформи заказ в Mini App\n"
        "• <b>Личный кабинет</b> — твои заказы и история\n"
        "• <b>Поддержка / Менеджер</b> — связь с менеджером",
        parse_mode="HTML",
        reply_markup=markup,
    )


@dp.message(F.text == "👤 Личный кабинет")
async def cmd_cabinet(message: types.Message):
    """Список заказов пользователя (видимые), старые сверху — свежие внизу."""
    if message.from_user.id == ADMIN_ID:
        admin_markup = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🛍️ Каталог", web_app=WebAppInfo(url=MINI_APP_URL))],
                [KeyboardButton(text="🆘 Поддержка / Менеджер")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            "👤 <b>Личный кабинет администратора</b>\n"
            "Для админки используй команду <b>/base</b>.",
            parse_mode="HTML",
            reply_markup=admin_markup,
        )
        return

    chat_id = str(message.from_user.id)
    orders = get_user_visible_orders(chat_id)
    if not orders:
        await message.answer("📭 <b>тут будут ваши заказы.</b>", parse_mode="HTML")
        return

    lines = [
        "<b>👤 Личный кабинет</b>",
        f"<i>Показано заказов: {len(orders)}</i>\n",
    ]
    for row in orders:
        (
            oid,
            fio,
            email,
            phone,
            username,
            address,
            postal_code,
            city,
            item,
            size,
            price,
            shipping_cost,
            total,
            _cid,
            date,
            status,
            _vis,
            track,
        ) = row
        tree = format_order_tree(
            oid,
            fio,
            email,
            phone,
            username,
            address,
            postal_code,
            city,
            item,
            size,
            price or 0,
            shipping_cost or 0,
            total,
            date,
            status=status,
            tracking_number=track,
        )
        lines.append(tree + "\n")

    body = "\n".join(lines).strip()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="cab_cl:ask")],
        ]
    )
    await send_long_html(message, body)
    await message.answer("Управление историей:", reply_markup=kb)


@dp.message(F.text == "🆘 Поддержка / Менеджер")
async def cmd_support_manager(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆘 Написать менеджеру",
                    url=MANAGER_TELEGRAM_URL,
                )
            ]
        ]
    )
    await message.answer("Поддержка / Менеджер:", reply_markup=kb)


@dp.callback_query(F.data.startswith("page_view:"))
async def admin_orders_page_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    try:
        page = int((callback.data or "").split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректная страница", show_alert=True)
        return

    text, kb = get_orders_text(page=page)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"❌ Ошибка пагинации page_view:{page}: {e}")
        await callback.answer("Не удалось обновить страницу заказов", show_alert=True)
        return
    await callback.answer()


@dp.callback_query(F.data == "cab_cl:ask")
async def cb_cabinet_clear_ask(query: CallbackQuery):
    await query.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="cab_cl:yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="cab_cl:no"),
            ],
        ]
    )
    await query.message.answer(
        "🗑️ <b>Скрыть всю историю заказов в боте?</b>\n"
        "(для админа заказы останутся, не волнуйся)",
        parse_mode="HTML",
        reply_markup=kb,
    )


@dp.callback_query(F.data == "cab_cl:no")
async def cb_cabinet_clear_no(query: CallbackQuery):
    await query.answer("Отменено")
    try:
        await query.message.delete()
    except Exception:
        pass


@dp.callback_query(F.data == "cab_cl:yes")
async def cb_cabinet_clear_yes(query: CallbackQuery):
    await query.answer()
    uid = str(query.from_user.id)
    n = set_user_orders_visibility(uid, 0)
    print(Fore.YELLOW + f"🗑️ История скрыта пользователем chat_id={uid}, строк: {n}" + Style.RESET_ALL)
    await query.message.answer(
        f"✅ История скрыта ({n} записей). В каталоге всё как прежде.",
        parse_mode="HTML",
    )
    try:
        await query.message.delete()
    except Exception:
        pass


@dp.message(Command("cmd"))
async def cmd_help(message: types.Message):
    """Команда /cmd - справка для администратора"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет доступа!")
        return

    help_text = (
        "🤖 ПАНЕЛЬ АДМИНИСТРАТОРА:\n\n"
        "📋 Просмотр заказов:\n"
        "• /base — постраничный просмотр всех заказов (по 8 на страницу, с начала → в конец)\n"
        "• Листание кнопками: ⬅️ Назад / Вперед ➡️\n"
        "• /base [ID] — один заказ по номеру, например /base 3\n"
        "└ под чеком — кнопки по статусу:\n"
        "• new → [✅ Подтвердить] [❌ Отмена]\n"
        "• confirmed → [📦 Отправить] [❌ Отмена]\n"
        "└ [📦 Отправить]: бот попросит трек-номер сообщением — он уйдёт клиенту, статус станет sent.\n\n"
        "🗑️ Управление:\n"
        "• /delete [номер] — удалить заказ из БД\n"
        "• /baseclearall — полная очистка БД (с подтверждением)\n"
        "• /test [N] — создать N тестовых заказов (по умолчанию 1)\n\n"
        "ℹ️ /cmd — это меню"
    )
    await message.answer(help_text)


@dp.message(Command("test"))
async def cmd_test_orders(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен!")
        return

    count = 1
    if command.args:
        try:
            count = int(command.args.strip())
            if count < 1:
                await message.answer("❌ Формат: /test [количество], количество должно быть > 0.")
                return
        except ValueError:
            await message.answer("❌ Формат: /test [количество]\nПример: /test 5")
            return

    created = 0
    for i in range(1, count + 1):
        order_id = save_order(
            fio=f"⚠️ ТЕСТОВЫЙ ЗАКАЗ TEST_USER_{i}",
            email="test@example.com",
            phone="+70000000000",
            username="TEST_USER",
            address=f"⚠️ ТЕСТОВЫЙ ЗАКАЗ TEST_ADDRESS_{i}",
            postal_code="000000",
            city="TEST_CITY",
            item=f"⚠️ ТЕСТОВЫЙ ЗАКАЗ TEST_ITEM_{i}",
            size="TEST_SIZE",
            price=1000,
            shipping_cost=DELIVERY_PRICE,
            total=1000 + DELIVERY_PRICE,
            chat_id=str(ADMIN_ID),
        )
        if order_id:
            created += 1

    await message.answer(f"✅ Создано тестовых заказов: {created}/{count}")


@dp.message(Command("base"))
async def cmd_base(message: types.Message):
    """/base — постраничный список заказов; /base [ID] — один заказ по ID."""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен!")
        return

    args = message.text.split()
    if len(args) == 1:
        text, kb = get_orders_text(page=0)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    try:
        order_id = int(args[1])
    except (IndexError, ValueError):
        await message.answer(
            "❌ Формат: <code>/base [ID]</code>\nПример: <code>/base 3</code>",
            parse_mode="HTML",
        )
        return

    row = get_order_by_id(order_id)
    if not row:
        await message.answer(f"❌ Заказ #{order_id} не найден!")
        return
    (
        oid,
        fio,
        email,
        phone,
        username,
        address,
        postal_code,
        city,
        item,
        size,
        price,
        shipping_cost,
        total,
        chat_id,
        date,
        status,
        _vis,
        track,
    ) = row
    tree = format_order_tree(
        oid,
        fio,
        email,
        phone,
        username,
        address,
        postal_code,
        city,
        item,
        size,
        price or 0,
        shipping_cost or 0,
        total,
        date,
        status=status,
        tracking_number=track,
    )
    kb = build_admin_order_keyboard(oid, status)
    await message.answer(
        f"📌 <b>Заказ по ID</b> <code>#{oid}</code>\n\n{tree}",
        parse_mode="HTML",
        reply_markup=kb,
    )


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
    """Команда /baseclearall - очистка БД с подтверждением."""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен!")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить всё", callback_data="confirm_clear_all")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_clear")],
        ]
    )
    await message.answer(
        "⚠️ Вы ТОЧНО уверены, что хотите удалить всю историю заказов? Вернуть её не получится.",
        reply_markup=kb,
    )


@dp.callback_query(F.data == "confirm_clear_all")
async def cb_confirm_clear_all(query: CallbackQuery):
    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return
    if clear_all_orders():
        await query.message.edit_text("✅ БД полностью очищена!\nСчетчик ID сброшен на 1")
    else:
        await query.message.edit_text("❌ Ошибка при очистке БД!")
    await query.answer()


@dp.callback_query(F.data == "cancel_clear")
async def cb_cancel_clear(query: CallbackQuery):
    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return
    await query.message.delete()
    await query.answer("Отменено")


async def _notify_client_order(chat_id_str: str, text: str):
    try:
        await bot.send_message(int(chat_id_str), text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ Не удалось уведомить клиента {chat_id_str}: {e}")


def _format_order_row_message(row) -> str:
    (
        oid,
        fio,
        email,
        phone,
        username,
        address,
        postal_code,
        city,
        item,
        size,
        price,
        shipping_cost,
        total,
        _cid,
        date,
        status,
        _vis,
        track,
    ) = row
    return format_order_tree(
        oid,
        fio,
        email,
        phone,
        username,
        address,
        postal_code,
        city,
        item,
        size,
        price or 0,
        shipping_cost or 0,
        total,
        date,
        status=status,
        tracking_number=track,
    )


@dp.callback_query(F.data.startswith("adm_cf:"))
async def cb_admin_confirm(query: CallbackQuery):
    if query.from_user.id != ADMIN_ID:
        await query.answer("Нет доступа", show_alert=True)
        return
    order_id = int(query.data.split(":")[1])
    row = get_order_by_id(order_id)
    if not row:
        await query.answer("Заказ не найден", show_alert=True)
        return
    st = (row[15] or "new").lower()
    if st != "new":
        await query.answer(f"Статус уже: {status_label_ru(st)}", show_alert=True)
        return
    if not update_order_status(order_id, "confirmed"):
        await query.answer("Ошибка БД", show_alert=True)
        return
    chat_id = row[13]
    await _notify_client_order(
        chat_id,
        (
            f"✅ <b>Заказ #{order_id} подтверждён!</b>\n\n"
            "Мы уже начали готовить твою посылку к отправке. 🚀\n\n"
            "📦 <b>Сроки:</b> Изготовление/отправка обычно занимает от 7 до 10 дней.\n"
            "🔔 <b>Что дальше:</b> Как только заказ будет передан в службу доставки, ты получишь уведомление "
            "с трек-номером для отслеживания.\n\n"
            "Спасибо, что выбрал нас! 🫶"
        ),
    )
    # Динамически обновляем очередь: подтверждённый заказ исчезает из списка.
    try:
        await _refresh_admin_queue_message(query.message, preferred_page=0)
    except Exception as e:
        logger.warning(f"⚠️ refresh queue after confirm: {e}")
    await query.answer("Подтверждён")
    print(Fore.GREEN + f"✅ Админ подтвердил заказ #{order_id}" + Style.RESET_ALL)


@dp.callback_query(F.data.startswith("adm_cn:"))
async def cb_admin_cancel(query: CallbackQuery):
    if query.from_user.id != ADMIN_ID:
        await query.answer("Нет доступа", show_alert=True)
        return
    order_id = int(query.data.split(":")[1])
    row = get_order_by_id(order_id)
    if not row:
        await query.answer("Заказ не найден", show_alert=True)
        return
    st = (row[15] or "new").lower()
    if st in ("sent", "cancelled"):
        await query.answer("Уже финальный статус", show_alert=True)
        return
    if not update_order_status(order_id, "cancelled"):
        await query.answer("Ошибка БД", show_alert=True)
        return
    chat_id = row[13]
    await _notify_client_order(chat_id, f"❌ <b>Заказ #{order_id}</b> отменён.")
    # Динамически обновляем очередь: отменённый заказ исчезает из списка.
    try:
        await _refresh_admin_queue_message(query.message, preferred_page=0)
    except Exception as e:
        logger.warning(f"⚠️ refresh queue after cancel: {e}")
    await query.answer("Отменён")
    print(Fore.YELLOW + f"❌ Админ отменил заказ #{order_id}" + Style.RESET_ALL)


@dp.callback_query(F.data.startswith("adm_sd:"))
async def cb_admin_send_start(query: CallbackQuery, state: FSMContext):
    if query.from_user.id != ADMIN_ID:
        await query.answer("Нет доступа", show_alert=True)
        return
    order_id = int(query.data.split(":")[1])
    row = get_order_by_id(order_id)
    if not row:
        await query.answer("Заказ не найден", show_alert=True)
        return
    if (row[15] or "").lower() != "confirmed":
        await query.answer("Сначала подтверди заказ", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_track)
    await state.update_data(
        order_id=order_id,
        origin_chat_id=query.message.chat.id,
        origin_message_id=query.message.message_id,
    )
    await query.answer()
    await query.message.answer(
        f"📦 Введи <b>трек-номер</b> для заказа <code>#{order_id}</code> одним сообщением.\n"
        f"<i>Отмена: /cancel</i>",
        parse_mode="HTML",
    )
    print(Fore.CYAN + f"📦 Ожидание трека для заказа #{order_id}" + Style.RESET_ALL)


@dp.message(StateFilter(AdminStates.waiting_track), Command("cancel"))
async def admin_cancel_track_input(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    await message.answer("Ввод трека отменён.")


@dp.message(StateFilter(AdminStates.waiting_track), F.from_user.id == ADMIN_ID)
async def admin_track_input(message: types.Message, state: FSMContext):
    track = (message.text or "").strip()
    if not track:
        await message.answer("Пришли трек одним сообщением (текстом).")
        return
    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await state.clear()
        await message.answer("Сессия сброшена. Открой заказ снова через /base ID.")
        return
    row = get_order_by_id(order_id)
    if not row:
        await state.clear()
        await message.answer("Заказ не найден.")
        return
    if (row[15] or "").lower() != "confirmed":
        await state.clear()
        await message.answer("Статус заказа изменился. Ввод трека отменён.")
        return
    safe_track = html.escape(track)
    if not set_order_sent_with_tracking(order_id, track):
        await message.answer("Ошибка сохранения статуса и трека.")
        return
    chat_id = row[13]
    await _notify_client_order(
        chat_id,
        f"📦 <b>Заказ #{order_id}</b> отправлен.\n"
        f"🔖 <b>Трек:</b> <code>{safe_track}</code>",
    )
    await state.clear()
    # Динамически обновляем очередь (заказ sent исчезает).
    origin_chat_id = data.get("origin_chat_id")
    origin_message_id = data.get("origin_message_id")
    try:
        if origin_chat_id and origin_message_id:
            text, kb = get_orders_text(0)
            await bot.edit_message_text(
                chat_id=origin_chat_id,
                message_id=origin_message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=kb,
            )
    except Exception as e:
        logger.warning(f"⚠️ refresh queue after sent: {e}")

    await message.answer(
        f"✅ Трек отправлен клиенту. Заказ <code>#{order_id}</code> — статус <b>sent</b>.",
        parse_mode="HTML",
    )
    print(Fore.GREEN + f"✅ Заказ #{order_id} отправлен, трек: {track}" + Style.RESET_ALL)


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
        
        await message.answer(
            "✅ <b>Скриншот успешно отправлен!</b>\n\n"
            "Наш менеджер уже проверяет транзакцию. Как только всё подтвердится, тебе придет уведомление.\n\n"
            "P.S. Если возникнут вопросы по оплате или данным доставки, менеджер свяжется с тобой лично. "
            "Не переживай, мы на связи! 🤝",
            parse_mode="HTML",
        )
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
        shipping_cost = DELIVERY_PRICE  # Дефолт
        
        if city and city != "—":
            try:
                from cdek_integration import calculate_shipping
                
                print("\n" + "="*80)
                print("🚚 РАСЧЕТ ДОСТАВКИ СДЭК")
                print("="*80)
                print(f"   🏙️  Город: '{city}'")
                print(f"   📞 Вызов: calculate_shipping()")
                
                shipping_cost = await calculate_shipping(city)
                ship_desc = "Стоимость доставки рассчитана"
                
                print(f"   ✅ РЕЗУЛЬТАТ: {shipping_cost}₽")
                print(f"   📝 Описание: {ship_desc}")
                print("="*80 + "\n")
                
            except Exception as e:
                logger.error(f"⚠️ ОШИБКА СДЭК: {e}")
                print(f"⚠️ Ошибка при расчете, используем дефолт {DELIVERY_PRICE}₽\n")
                shipping_cost = DELIVERY_PRICE
        
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
            f"✅ <b>Заказ создан!</b>\n\n"
            f"<b>【 ЗАКАЗ #{order_id} 】</b>\n"
            f"└ 👕 <b>Товар:</b> {item}\n"
            f"└ 📏 <b>Размер:</b> {size}\n"
            f"└ 💵 <b>Стоимость товара:</b> {price}₽\n"
            f"└ 🚚 <b>Доставка:</b> {shipping_cost}₽\n"
            f"└ 💰 <b>ИТОГО:</b> <code>{total}₽</code>\n"
            f"═══════════════════════════════\n\n"
            f"👤 <b>Твои данные (проверь, всё ли верно?):</b>\n"
            f"🙋‍♂️ <b>ФИО:</b> {fio}\n"
            f"📧 <b>Почта:</b> {email}\n"
            f"📞 <b>Тел:</b> {phone}\n"
            f"🔗 <b>Твой профиль:</b> @{username}\n"
            f"🏠 <b>Адрес:</b> {address}\n"
            f"📮 <b>Индекс:</b> {postal_code}\n"
            f"📍 <b>Город:</b> {city}\n\n"
            f"💳 <b>Оплата:</b>\n"
            f"<code>2204 3211 2754 4542</code>\n"
            f"(Ozon-bank)\n\n"
            f"🙏 <b>Отправь скриншот чека!</b>"
        )
        await message.answer(receipt, parse_mode="HTML")
        
        # УВЕДОМЛЕНИЕ АДМИНУ в формате "дерева"
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        admin_tree = format_order_tree(
            order_id,
            fio,
            email,
            phone,
            username,
            address,
            postal_code,
            city,
            item,
            size,
            price,
            shipping_cost,
            total,
            now,
            status="new",
        )

        admin_alert = (
            f"🚀 <b>✨ НОВЫЙ ЗАКАЗ! ✨</b>\n\n{admin_tree}\n\n"
            f"<b>Статус в системе:</b> {status_label_ru('new')}"
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
    init_db()
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запуск бота"),
            BotCommand(command="cmd", description="Справка администратора"),
        ]
    )
    
    print(Fore.BLUE + "█" * 60)
    print(Fore.BLUE + "█" + Fore.YELLOW + "      M N G N V   S H O P   V 1.0     ".center(58) + Fore.BLUE + "█")
    print(Fore.BLUE + "█" + Fore.WHITE + "--------------------------------------".center(58) + Fore.BLUE + "█")
    print(Fore.BLUE + "█" + Fore.GREEN + "   🚀 СТАТУС: СЕРВЕР ПОДНЯТ           ".center(57) + Fore.BLUE + "█")
    print(Fore.BLUE + "█" * 60)

    print(f"✅ {Fore.WHITE}Admin ID: {Fore.YELLOW}{ADMIN_ID}")
    print(f"✅ {Fore.WHITE}Mini App URL: {Fore.CYAN}{MINI_APP_URL}")
    print(f"✅ {Fore.WHITE}Прокси: {Fore.MAGENTA}{'🟢 ВКЛЮЧЕН' if USE_PROXY else '🔴 ОТКЛЮЧЕН'}")
    print(f"✅ {Fore.WHITE}База данных: {DB_PATH}")
    print(Fore.BLUE + "█"*80 + Style.RESET_ALL + "\n")
# Тест критической ошибки (Красный)
    print(Fore.RED + Style.BRIGHT + "🚨 ТЕСТ: КРИТИЧЕСКАЯ ОШИБКА (Например, база данных недоступна!)")

    # Тест предупреждения (Желтый)
    print(Fore.YELLOW + "⚠️ ТЕСТ: ПРЕДУПРЕЖДЕНИЕ (Низкая скорость интернета или долгий ответ СДЭК)")

    # Тест ссылки (Голубой/Cyan)
    print(Fore.CYAN + "🔗 ТЕСТ: ССЫЛКА НА ОПЛАТУ: https://mngnv-shop.ru/pay")

    # Тест информационного сообщения (Белый)
    print(Fore.WHITE + "ℹ️ ТЕСТ: ИНФО (Бот готов к приему новых заказов)")
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
