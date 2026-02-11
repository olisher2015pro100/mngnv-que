import telebot
from telebot import types
import json

# Твои данные
TOKEN = '8515886958:AAHWLWjmGtFj9BsUleOSsqZCaoN7NxdBHf4'
ADMIN_ID = 1018181608 

bot = telebot.TeleBot(TOKEN)

# Главное меню с кнопкой каталога
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Твоя актуальная ссылка на GitHub Pages
    web_link = "https://olisher2015pro100.github.io/my-shop-app/"
    markup.add(types.KeyboardButton("Открыть каталог 🛍️", web_app=types.WebAppInfo(web_link)))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "Привет! Я бот магазина mister snich. \n\n"
        "🛍️ Чтобы сделать заказ — жми кнопку 'Открыть каталог'\n"
        "📩 Если есть вопрос — просто пиши сюда, менеджер ответит!", 
        reply_markup=main_menu()
    )

# 🚨 ОБРАБОТКА ЗАКАЗА С САЙТА
@bot.message_handler(content_types=['web_app_data'])
def get_order(message):
    try:
        # Распаковываем данные из мини-приложения
        data = json.loads(message.web_app_data.data)
        
        # Формируем расширенный отчет для менеджера
        order_text = (
            f"🚨 **НОВЫЙ ЗАКАЗ!**\n"
            f"━━━━━━━━━━━━━━\n"
            f"📦 **Товар:** {data['item']}\n"
            f"💰 **Цена:** {data['price']}\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 **ФИО:** {data['customer_name']}\n"
            f"🏠 **Адрес:** {data['address']}\n"
            f"📮 **Индекс:** {data.get('zip', 'не указан')}\n"
            f"📞 **Телефон:** {data['phone']}\n"
            f"📧 **E-mail:** {data['email']}\n"
            f"📱 **TG контакт:** {data['tg_contact']}\n"
            f"━━━━━━━━━━━━━━\n"
            f"🆔 **ID клиента:** {message.chat.id}"
        )
        
        # Отправляем админу
        bot.send_message(ADMIN_ID, order_text, parse_mode="Markdown")
        
        # Подтверждение клиенту
        bot.send_message(message.chat.id, "✅ Заказ отправлен менеджеру! Я скоро свяжусь с тобой для оплаты.")
        
    except Exception as e:
        print(f"Ошибка при получении данных заказа: {e}")
        bot.send_message(ADMIN_ID, f"❌ Ошибка в данных заказа: {e}")

# 📩 САППОРТ (Клиент -> Менеджер)
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_ID)
def to_admin(m):
    bot.send_message(ADMIN_ID, f"📩 Сообщение от клиента (ID: {m.chat.id}):")
    bot.forward_message(ADMIN_ID, m.chat.id, m.message_id)

# 📩 САППОРТ (Менеджер -> Клиент)
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.reply_to_message)
def from_admin(m):
    try:
        if m.reply_to_message.forward_from:
            cid = m.reply_to_message.forward_from.id
        else:
            text_parts = m.reply_to_message.text.split("ID: ")
            cid = int(text_parts[1].split("):")[0])
            
        bot.send_message(cid, f"👨‍💻 Ответ менеджера:\n\n{m.text}")
        bot.send_message(ADMIN_ID, "✅ Ответ отправлен!")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Ошибка отправки: возможно, у клиента скрыт профиль или ID не найден.")

if __name__ == '__main__':
    print("🚀 Бот запущен! Окно не закрывай.")
    bot.infinity_polling()