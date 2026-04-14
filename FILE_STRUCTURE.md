# 📁 Структура файлов проекта CDEK Integration

## 🎯 Быстрый обзор

После интеграции у тебя будут эти файлы:

```
bot_shop/
├── 🔵 cdek_integration.py           ← Модуль API CDEK (ОСНОВНОЙ)
├── 🔵 bot_with_cdek.py              ← Бот aiogram 3.x + FastAPI (ОСНОВНОЙ)
├── 🔵 index_updated.html            ← Mini App фронтенд с доставкой (НОВЫЙ)
│
├── 📄 .env                          ← Конфиг с ключами (ЗАПОЛНИ САМИ!)
├── 📄 .env.example                  ← Пример .env
├── 📦 requirements.txt              ← Зависимости pip
│
├── 📖 CDEK_INTEGRATION_README.md    ← Полная документация
├── 📖 CHEATSHEET.py                 ← Краткий справочник
├── 📖 QUICK_START_EXAMPLES.py       ← 8 примеров использования
├── 📖 TROUBLESHOOTING.md            ← Решение проблем
│
├── (старые файлы)
├── index.html                       ← Старый фронтенд (оставить как бэкап)
├── main.py                          ← Старый бот
└── ...
```

---

## 📄 Описание каждого файла

### 1. **cdek_integration.py** (ЗВЕЗДА ⭐)

**Что это?** 
Асинхронный модуль для работы с CDEK API v2.0.

**Главные функции:**
- `get_cdek_oauth_token()` — Получить токен
- `calculate_shipping(city_name)` — Расчет доставки **← ОСНОВАЦИЯ**
- `validate_phone(phone)` — Проверка номера
- `validate_city(city_name)` — Проверка города

**Когда использовать?**
```python
# Импортируй и используй где угодно
from cdek_integration import calculate_shipping

cost, description = await calculate_shipping("Москва")
print(f"Доставка: {cost} ₽")  # 450 ₽
```

**Что внутри?**
- ~400 строк чистого кода
- Полное логирование (debug, info, error)
- Обработка 10+ типов ошибок
- Кэширование OAuth токена
- Таймауты для CDEK API

**Файл готов к использованию как есть!** ✅

---

### 2. **bot_with_cdek.py** (ЗВЕЗДА ⭐)

**Что это?**
Полный бот на aiogram 3.x + FastAPI, готовый к запуску.

**Структура:**
```
AIOGRAM BOT (телеграм)
├── @dp.message(Command("start"))       — Кнопка Mini App
├── handle_web_app_order()              — Обработка заказов
├── format_customer_confirmation()      — Сообщение покупателю
└── format_admin_notification()         — Оповещение администраторам

FASTAPI API (расчет доставки)
├── POST /api/calculate-shipping        — Главный endpoint
├── GET /api/health                     — Проверка статуса
└── GET /                               — Информация об API
```

**Как запустить?**
```bash
# 1. Заполни .env
# 2. Запусти:
python bot_with_cdek.py

# Результат:
🤖 Запускаю Telegram бота...
✅ API запущена на http://127.0.0.1:8000
```

**Что делает?**
1. Слушает Telegram команды (/start)
2. Показывает кнопку "Открыть магазин" (Mini App)
3. Получает заказы из Mini App (JSON)
4. Обрабатывает POST запросы к `/api/calculate-shipping`
5. Отправляет подтверждения пользователю
6. Отправляет уведомления администраторам

**Файл готов к запуску!** ✅

---

### 3. **index_updated.html** (ЗВЕЗДА ⭐)

**Что это?**
Обновленный фронтенд Mini App с интеграцией CDEK.

**Новые компоненты:**
- 🏙️ Поле города с подсказками (30 популярных городов РФ)
- 📱 Поле телефона type="tel" с форматированием
- 💰 Блок расчета доставки (real-time расчет при выборе города)
- ✅ Валидация всех полей перед отправкой

**Как заменить?**
```bash
# Старый файл сохрани как бэкап
cp index.html index.html.bak

# Используй новый
cp index_updated.html index.html

# Или оставь оба - на вкус
```

**Структура HTML:**
```html
<div id="order-page">
  <!-- Поле города с подсказками -->
  <input id="city" placeholder="Начни вводить город...">
  <div id="city-suggestions"></div>
  
  <!-- Информация о доставке -->
  <div id="shipping-info">
    <div id="shipping-cost">...</div>
    <div id="shipping-status">Загрузка...</div>
  </div>
  
  <!-- Поле телефона -->
  <input type="tel" id="phone" placeholder="Номер телефона">
</div>
```

**Ключевая функция JavaScript:**
```javascript
async function selectCity(cityName) {
    // Отправляет POST запрос к /api/calculate-shipping
    const response = await fetch('/api/calculate-shipping', {
        method: 'POST',
        body: JSON.stringify({ city: cityName })
    });
    
    // Получает стоимость и обновляет UI
    const data = await response.json();
    document.getElementById('shipping-cost').innerText = `${data.cost} ₽`;
}
```

**Файл готов к использованию!** ✅

---

### 4. **.env** (КРИТИЧНО! ⚠️)

**Что это?**
Файл с конфигурацией и секретными ключами.

**Как создать?**
```bash
# Скопируй пример
cp .env.example .env

# Отредактируй в своем редакторе (VS Code, Sublime, etc)
# Заполний все значения
```

**Что должно быть внутри?**
```bash
# Телеграм бот
BOT_TOKEN=8515886958:AAHWLWjmGtFj9BsUleOSsqZCaoN7NxdBHf4
ADMINS=1018181608

# CDEK API (ОБЯЗАТЕЛЬНО получи эти ключи!)
CDEK_CLIENT_ID=4I5vLAbLUPdMIOEhVD0osn4fS0fvTttj
CDEK_CLIENT_SECRET=g1WXBI56G3ZAPrY0TleKblVIwsnMCm8J

# Твой Mini App URL
MINI_APP_URL=https://yourdomain.com/index_updated.html
```

**ВАЖНО:**
- ❌ Не коммитай .env в Git!
- ✅ Добавь в .gitignore: `echo ".env" >> .gitignore`
- ✅ Используй .env.example как шаблон

---

### 5. **requirements.txt**

**Что это?**
Список всех Python зависимостей проекта.

**Как использовать?**
```bash
pip install -r requirements.txt
```

**Что внутри?**
```
aiogram==3.5.0           # Telegram bot framework
aiohttp==3.9.3           # Async HTTP (для CDEK)
fastapi==0.104.1         # Web framework
uvicorn==0.24.0          # ASGI server
python-dotenv==1.0.0     # Чтение .env
```

---

### 📖 ДОКУМЕНТАЦИЯ

#### **CDEK_INTEGRATION_README.md** 
**Полная документация (20+ страниц)**

Содержит:
- Подробное описание каждой функции
- Примеры использования
- API endpoints с curl примерами
- Обработка ошибок
- Deployment на продакшене
- Docker и Systemd примеры

**Когда читать?**
- Когда нужна полная информация
- Для продакшена
- Для глубокого понимания кода

---

#### **CHEATSHEET.py**
**Краткий справочник (2 страницы)**

Содержит:
- Быстрый старт (5 минут)
- Основные функции
- Примеры для Telegram бота
- Обработка ошибок
- Обновление параметров посылки
- API endpoints
- Код безопасности

**Когда читать?**
- Нужна быстрая ответ
- Стоишь в спешке
- Хочешь вспомнить синтаксис

---

#### **QUICK_START_EXAMPLES.py**
**8 практических примеров (коды)**

Примеры:
1. Простая интеграция в существующий бот
2. Middleware для автоматического расчета
3. Кэш для популярных городов
4. Валидация телефона
5. Полный Mini App пример
6. Расширенное логирование
7. Батч запросы нескольких городов
8. Safe функция, не ломающая заказ

**Когда использовать?**
- Копируешь примеры в свой код
- Учишься на готовых решениях
- Адаптируешь под свои задачи

---

#### **TROUBLESHOOTING.md**
**Решение проблем (8 основных проблем)**

Проблемы:
1. ❌ CDEK ключи не установлены
2. ❌ "Connection refused" порт занят
3. ❌ Timeout при расчете доставки
4. ❌ Город не найден
5. ❌ Mini App не открывается
6. ❌ "Fetch failed" при расчете
7. ❌ Номер не форматируется
8. ❌ Синтаксис ошибки

Для каждой проблемы:
- Что видишь (症状)
- Почему это происходит (причина)
- Как исправить (5+ шагов)
- Как предотвратить (лучшие практики)

**Когда использовать?**
- Что-то не работает
- Видишь ошибку в консоли
- Нужен быстрый debug

---

## 🚀 ШАГ-ЗА-ШАГОМ ЗАПУСК

### Шаг 1: Подготовка (10 минут)
```bash
# Скопируй все файлы в папку проекта
cp cdek_integration.py /path/to/bot_shop/
cp bot_with_cdek.py /path/to/bot_shop/
cp index_updated.html /path/to/bot_shop/
cp .env.example /path/to/bot_shop/

# Перейди в папку
cd /path/to/bot_shop

# Установи зависимости
pip install -r requirements.txt
```

### Шаг 2: Конфигурация (5 минут)
```bash
# Создай .env
cp .env.example .env

# Отредактируй .env (открой в редакторе)
# Заполни: BOT_TOKEN, CDEK_CLIENT_ID, CDEK_CLIENT_SECRET, MINI_APP_URL

# Проверь что все правильно
cat .env
```

### Шаг 3: Тестирование (5 минут)
```bash
# Тест CDEK интеграции
python cdek_integration.py

# Должно вывести:
# ✅ Токен получен
# ✅ Города найдены
# ✅ Доставка рассчитана
```

### Шаг 4: Запуск (1 минута)
```bash
# Запусти бота
python bot_with_cdek.py

# Должно вывести:
# 🚀 ЗАПУСК mngnv SHOP BOT
# ✅ API запущена на http://127.0.0.1:8000
# 🤖 Запускаю Telegram бота...
```

### Шаг 5: Проверка (5 минут)
```bash
# В другом терминале
curl http://127.0.0.1:8000/api/health

# Должно вернуться:
# {"status": "ok", "cdek_connected": true, "bot_initialized": true}

# Открой Telegram бота
# Нажми /start
# Должна быть кнопка "🛍️ Открыть магазин"
# Нажми кнопку
# Должен открыться Mini App
```

---

## 📊 Диаграмма взаимодействия

```
ПОЛЬЗОВАТЕЛЬ (Telegram)
         ↓
    нажимает /start
         ↓
bot_with_cdek.py (cmd_start handler)
    показывает кнопку "🛍️ Открыть магазин"
         ↓
    нажимает кнопку
         ↓
Открывается WebView (Mini App)
    index_updated.html
         ↓
    Пользователь вводит город
         ↓
JavaScript (selectCity) вызывает fetch()
    POST http://localhost:8000/api/calculate-shipping
         ↓
bot_with_cdek.py (FastAPI endpoint)
    вызывает:  calculate_shipping("Москва")
         ↓
cdek_integration.py
    1. get_cdek_oauth_token()
    2. get_city_code("Москва")
    3. вызов CDEK API (/calculator/tarifflist)
    4. return (450, "Доставка: Стандартная")
         ↓
FastAPI возвращает JSON
    {"cost": 450, "description": "...", "city": "Москва"}
         ↓
JavaScript обновляет UI
    показывает: "💰 450 ₽"
         ↓
Пользователь заполняет форму и нажимает "Оформить"
         ↓
Mini App отправляет JSON в Telegram
    {
        "item": "zip-hoodie",
        "price": 8000,
        "shipping_cost": 450,
        "shipping_city": "Москва",
        ...
    }
         ↓
bot_with_cdek.py (handle_web_app_order handler)
    полностью обрабатывает заказ
    отправляет подтверждение пользователю
    отправляет уведомление администраторам
         ↓
КОНЕЦ 🎉
```

---

## ✅ ЧЕКЛИСТ ПЕРЕД НАЧАЛОМ

- [ ] Все файлы скопированы в проект
- [ ] .env создан и заполнен
- [ ] BOT_TOKEN вставлен
- [ ] CDEK_CLIENT_ID вставлен
- [ ] CDEK_CLIENT_SECRET вставлен
- [ ] requirements.txt установлен (pip install -r requirements.txt)
- [ ] cdek_integration.py тестировался (python cdek_integration.py)
- [ ] Бот запустился без ошибок
- [ ] API слушает на 127.0.0.1:8000
- [ ] curl http://127.0.0.1:8000/api/health вернул 200 OK

Если все ✅ → **Готово! Все работает!** 🎉

---

## 📞 ВОПРОСЫ?

1. **Ошибка при запуске?** → Смотри `TROUBLESHOOTING.md`
2. **Как использовать функцию?** → Смотри `QUICK_START_EXAMPLES.py`
3. **Нужна полная информация?** → Смотри `CDEK_INTEGRATION_README.md`
4. **Забыл синтаксис?** → Смотри `CHEATSHEET.py`

---

**Удачи с магазином!** 🛍️✨
