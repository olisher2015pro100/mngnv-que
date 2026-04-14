import telebot
from telebot import types
import json
import re
import sqlite3
import os

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
TOKEN = '8515886958:AAHWLWjmGtFj9BsUleOSsqZCaoN7NxdBHf4'
ADMINS = [1018181608]
# Primary admin id for single-admin checks
ADMIN_ID = ADMINS[0] if ADMINS else None

# Абсолютный путь к базе данных
DB_PATH = '/home/olisher2015pro100/orders.db'

bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Создаём таблицу только если её нет
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders
                      (fio TEXT, phone TEXT, address TEXT, post_index TEXT, item TEXT, price TEXT, 
                       contact TEXT, email TEXT, chat_id TEXT)''')
    
    # Проверяем, есть ли колонка size, если нет - добавляем (миграция)
    cursor.execute("PRAGMA table_info(orders)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'size' not in columns:
        cursor.execute('ALTER TABLE orders ADD COLUMN size TEXT')
        print("[MIGRATION] Добавлена колонка 'size' в таблицу 'orders'")
    
    conn.commit()
    conn.close()
    print(f"✅ База данных подключена по адресу: {DB_PATH}")

init_db()

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_link = "https://olisher2015pro100.github.io/mngnv-que/"
    markup.add(types.KeyboardButton("открыть каталог 🛍️", web_app=types.WebAppInfo(web_link)))
    welcome_text = (
        "🔥 <b>привет друк — это бот покупок</b>\n\n"
        "тут ты можешь купить вещь или терроризировать менеджера.\n"
        "нажми кнопку ниже, чтобы открыть каталог и подобрать свой размер.\n\n")

    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.message_handler(content_types=['web_app_data'])
def get_order(message):
    try:
        data = json.loads(message.web_app_data.data)
        item = data.get('item', '—')
        price = data.get('price', '—')
        size = data.get('size', 'не указан')
        fio = data.get('customer', '—')
        addr = data.get('address', '—')
        idx = data.get('index', '—')
        phone = data.get('phone', '—')
        email = data.get('email', '—')
        tg_nick = data.get('tg_user', '—')

        # Добавляем доставку к цене
        try:
            base_price = int(price)
            total_price = base_price + 500
        except (ValueError, TypeError):
            total_price = price
            base_price = price
        
        # СООБЩЕНИЕ ПОКУПАТЕЛЮ — подробное подтверждение данных
        client_msg = (
            f"✅ <b>Заказ получен!</b>\n\n"
            f"📦 <b>Товар:</b> {item}\n"
            f"📏 <b>Размер:</b> {size}\n"
            f"💰 <b>Цена товара:</b> {base_price} руб\n"
            f"🚚 <b>Доставка:</b> 500 руб\n"
            f"<b>Итого к оплате:</b> {total_price} руб (включая доставку)\n\n"
            f"👤 <b>твои данные:</b>\n"
            f"• ФИО: {fio}\n"
            f"• Телефон: {phone}\n"
            f"• Почта: {email}\n"
            f"• Адрес: {addr}\n"
            f"• Индекс: {idx}\n"
            f"• TG: {tg_nick}\n\n"
            f"📍 Реквизиты для оплаты:\n<code>2200 7020 9556 5789</code> (Т-Банк / Минганов И.А)\n\n"
            f"🙏 Пожалуйста, пришли скриншот чека, ответив на это сообщение — как только получим платёж, подтвердим заказ."
        )
        bot.send_message(message.chat.id, client_msg, parse_mode="HTML")

        # Сохранить заказ в локальную БД сразу при получении
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO orders (fio, phone, address, post_index, item, size, price, contact, email, chat_id)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (fio, phone, addr, idx, item, size, total_price, tg_nick or "—", email, str(message.chat.id)))
            conn.commit()
            conn.close()
        except Exception as db_e:
            print(f"Ошибка при сохранении заказа в БД: {db_e}")

        # УВЕДОМЛЕНИЕ АДМИНУ
        admin_msg = (
            f"🚀 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
            f"👤 <b>ФИО:</b> {fio}\n"
            f"📱 <b>тел:</b> {phone}\n"
            f"📧 <b>почта:</b> {email}\n"
            f"📍 <b>адрес:</b> {addr}\n"
            f"📮 <b>индекс:</b> {idx}\n"
            f"👕 <b>товар:</b> {item}\n"
            f"📏 <b>размер:</b> {size}\n"
            f"💰 <b>цена товара:</b> {base_price} rub\n"
            f"🚚 <b>доставка:</b> 500 rub\n"
            f"<b>итого:</b> {total_price} rub\n"
            f"🔗 <b>связь:</b> {tg_nick}\n"
            f"🆔 ID для ответа: <code>{message.chat.id}</code>"
        )
        for admin_id in ADMINS:
            bot.send_message(admin_id, admin_msg, parse_mode="HTML")

    except Exception as e:
        print(f"Ошибка в get_order: {e}")

@bot.message_handler(commands=['base'])
def show_base(message):
    # allow any id from ADMINS list (supports multiple admins)
    print(f"[DEBUG] /base команда от {message.chat.id}, ADMINS={ADMINS}")
    if message.chat.id in ADMINS:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT fio, phone, email, address, post_index, item, size, price, contact, chat_id FROM orders')
            rows = cursor.fetchall()
            conn.close()
            print(f"[DEBUG] Найдено {len(rows)} заказов")

            if rows:
                res = "<b>📋 ВСЕ ЗАКАЗЫ:</b>\n\n"
                for idx, r in enumerate(rows, 1):
                    fio, phone, email, addr, post_idx, item, size, price, contact, chat = r
                    res += (f"<b>#{idx}</b>\n"
                            f"👤 <b>ФИО:</b> {fio}\n"
                            f"📱 <b>тел:</b> {phone}\n"
                            f"📧 <b>почта:</b> {email}\n"
                            f"📍 <b>адрес:</b> {addr}\n"
                            f"📮 <b>индекс:</b> {post_idx}\n"
                            f"👕 <b>товар:</b> {item}\n"
                            f"📏 <b>размер:</b> {size}\n"
                            f"💵 <b>итого к оплате:</b> {price} rub\n"
                            f"🔗 <b>связь:</b> {contact}\n"
                            f"🆔 <b>чат ID:</b> <code>{chat}</code>\n")
                    res += "—"*30 + "\n"
                bot.send_message(message.chat.id, res, parse_mode="HTML")
            else:
                bot.send_message(message.chat.id, "❌ База пока пуста.")
        except Exception as e:
            print(f"[ERROR] в show_base: {e}")
            bot.send_message(message.chat.id, f"⚠️ Ошибка: {e}")
    else:
        print(f"[DEBUG] Доступ запрещен для {message.chat.id}")
        bot.send_message(message.chat.id, "❌ У вас нет доступа к этой команде.")


@bot.message_handler(commands=['id', 'whoami'])
def show_my_id(message):
    # convenience command to learn your chat id
    try:
        bot.reply_to(message, f"Ваш chat id: <code>{message.chat.id}</code>", parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка в show_my_id: {e}")


@bot.message_handler(commands=['del'])
def delete_order(message):
    # /del <номер> - удалить конкретный заказ
    # /del all - удалить всё
    if message.chat.id not in ADMINS:
        bot.reply_to(message, "❌ У вас нет доступа к этой команде.")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "📝 Использование:\n/del <номер> - удалить заказ\n/del all - удалить всё\n\nНапример: /del 1")
            return
        
        arg = args[1].lower()
        
        # Если "all" - удаляем всё
        if arg == "all":
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM orders')
            count = cursor.fetchone()[0]
            
            if count == 0:
                bot.reply_to(message, "❌ База уже пуста.")
                conn.close()
                return
            
            cursor.execute('DELETE FROM orders')
            conn.commit()
            conn.close()
            
            bot.reply_to(message, f"🗑️ Все {count} заказов удалены! База очищена.")
            return
        
        # Иначе удаляем по номеру
        order_num = int(arg)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders')
        rows = cursor.fetchall()
        
        if order_num < 1 or order_num > len(rows):
            bot.reply_to(message, f"❌ Заказ #{order_num} не найден. Всего заказов: {len(rows)}")
            conn.close()
            return
        
        # Удалить нужную запись (порядковый номер order_num)
        target_row = rows[order_num - 1]
        fio = target_row[0]
        
        # Удаляем по уникальной комбинации (первая запись с этим ФИО и адресом)
        cursor.execute('DELETE FROM orders WHERE fio = ? AND address = ? AND phone = ? LIMIT 1',
                      (target_row[0], target_row[2], target_row[1]))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Заказ #{order_num} (ФИО: {fio}) удалён из базы.")
    except ValueError:
        bot.reply_to(message, "❌ Ошибка: используйте /del <номер> или /del all")
    except Exception as e:
        print(f"[ERROR] в delete_order: {e}")
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

@bot.message_handler(content_types=['photo', 'text'])
def handle_all_messages(message):
    try:
        # 1. АДМИН ОТВЕЧАЕТ КЛИЕНТУ
        if message.chat.id == ADMIN_ID and message.reply_to_message:
            text_to_search = message.reply_to_message.text or message.reply_to_message.caption or ""
            found_ids = re.findall(r'\d{9,12}', text_to_search)

            if found_ids:
                target_id = found_ids[-1]

                if message.text and message.text.strip().lower() == "одобрено":
                    text = message.reply_to_message.text

                    fio = re.search(r"ФИО:\s*(.+)", text).group(1) if "ФИО:" in text else "—"
                    phone = re.search(r"тел:\s*(.+)", text).group(1) if "тел:" in text else "—"
                    email = re.search(r"почта:\s*(.+)", text).group(1) if "почта:" in text else "—"
                    addr = re.search(r"адрес:\s*(.+)", text).group(1) if "адрес:" in text else "—"
                    idx = re.search(r"индекс:\s*(.+)", text).group(1) if "индекс:" in text else "—"
                    item = re.search(r"товар:\s*(.+)", text).group(1) if "товар:" in text else "—"
                    size = re.search(r"размер:\s*(.+)", text).group(1) if "размер:" in text else "—"
                    price = re.search(r"итого:\s*(.+?)\s*rub", text).group(1) if "итого:" in text else "—"

                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''INSERT INTO orders (fio, phone, address, post_index, item, size, price, contact, email)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (fio, phone, addr, idx, item, size, price, "link", email))
                    conn.commit()
                    conn.close()

                    bot.send_message(target_id, "✨ <b>Ваш заказ одобрен!</b>", parse_mode="HTML")
                    bot.reply_to(message, "✅ Данные сохранены в базу!")
                else:
                    bot.send_message(target_id, f"<b>Сообщение от магазина:</b>\n\n{message.text}", parse_mode="HTML")
                    bot.reply_to(message, "✅ ответ отправлен.")
            return

        # 2. КЛИЕНТ ПИШЕТ АДМИНУ
        if message.chat.id != ADMIN_ID:
            username = message.from_user.username if message.from_user.username else "ник скрыт"
            info = f"💬 <b>Новое сообщение!</b>\nОт: @{username}\n🆔 ID: <code>{message.chat.id}</code>\n\n"

            if message.content_type == 'text':
                bot.send_message(ADMIN_ID, info + f"Текст: {message.text}", parse_mode="HTML")
            elif message.content_type == 'photo':
                bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=info + "Прислал фото/чек", parse_mode="HTML")

    except Exception as e:
        print(f"Ошибка связи: {e}")

if __name__ == '__main__':
    bot.infinity_polling()