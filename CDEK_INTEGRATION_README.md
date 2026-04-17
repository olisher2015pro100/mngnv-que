# 🛍️ mngnv Mini App - Интеграция CDEK API

Полная интеграция расчета доставки CDEK v2.0 в Telegram Mini App на aiogram 3.x.

## 📋 Содержание

1. [Что было создано](#-что-было-создано)
2. [Быстрый старт](#-быстрый-старт)
3. [Установка зависимостей](#-установка-зависимостей)
4. [Конфигурация](#-конфигурация)
5. [Структура кода](#-структура-кода)
6. [API Endpoints](#-api-endpoints)
7. [Дебаг и тестирование](#-дебаг-и-тестирование)
8. [Обработка ошибок](#-обработка-ошибок)

---

## 🆕 Что было создано

### 1️⃣ **cdek_integration.py** — Модуль CDEK API
Асинхронный модуль для работы с CDEK API v2.0:

- **`get_cdek_oauth_token()`** — Получение OAuth токена с кэшированием
- **`get_city_code(city_name)`** — Поиск кода города по названию
- **`calculate_shipping(city_name)`** — Расчет стоимости доставки
- **`validate_phone(phone)`** — Валидация номера телефона
- **`validate_city(city_name)`** — Проверка наличия города в CDEK

**Особенности:**
- ✅ Асинхронность (async/await)
- ✅ Обработка ошибок с дефолтной стоимостью 500 ₽
- ✅ Кэширование OAuth токена
- ✅ Логирование всех операций

### 2️⃣ **index_updated.html** — Обновленный фронтенд Mini App

**Новые компоненты:**
- 🏙️ **Поле города** с автодополнением (30 популярных городов РФ)
- 📱 **Поле телефона** тип `tel` с красивым форматированием
- 💰 **Блок расчета доставки** — показывает стоимость в real-time
- ✅ **Валидация** всех полей перед отправкой
- 🔄 **Запрос к API** `/api/calculate-shipping` при выборе города

**UI Улучшения:**
- Индикаторы загрузки с "спиннером"
- Цветные статусы (успех/ошибка)
- Адаптивный дизайн для мобильных
- Приятная анимация переходов

### 3️⃣ **bot_with_cdek.py** — Интегрированный бот aiogram 3.x

**Структура:**
```python
├── AIOGRAM BOT
│   ├── /start — Кнопка открытия Mini App
│   ├── Web App Data Handler — Обработка заказов
│   ├── format_customer_confirmation() — Сообщение покупателю
│   └── format_admin_notification() — Уведомление администраторам
│
└── FASTAPI API
    ├── POST /api/calculate-shipping — Расчет доставки
    ├── GET /api/health — Проверка статуса
    └── GET / — Главная страница API
```

---

## 🚀 Быстрый старт

### Шаг 1: Получи ключи CDEK

1. Перейди на https://partner.cdek.ru
2. Авторизуйся или создай аккаунт
3. Найди в личном кабинете:
   - `CLIENT_ID` (в разделе API ключи)
   - `CLIENT_SECRET` (в разделе API ключи)

### Шаг 2: Подготовь файлы

```bash
# Скопируй в свой проект:
cp cdek_integration.py /path/to/project/
cp bot_with_cdek.py /path/to/project/
cp index_updated.html /path/to/project/
cp .env.example /path/to/project/.env
```

### Шаг 3: Отредактируй .env

```bash
# .env
BOT_TOKEN=твой_токен_от_@BotFather
CDEK_CLIENT_ID=4I5vLAbLUPdMIOEhVD0osn4fS0fvTttj
CDEK_CLIENT_SECRET=g1WXBI56G3ZAPrY0TleKblVIwsnMCm8J
MINI_APP_URL=https://yourdomain.com/index_updated.html
```

### Шаг 4: Запусти бота

```bash
python bot_with_cdek.py
```

---

## 📦 Установка зависимостей

```bash
pip install aiogram==3.x
pip install aiohttp
pip install fastapi
pip install uvicorn
pip install python-dotenv
```

Или через requirements.txt:

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
aiogram==3.x
aiohttp==3.9.x
fastapi==0.104.x
uvicorn==0.24.x
python-dotenv==1.0.x
```

---

## ⚙️ Конфигурация

### Переменные окружения (.env)

| Переменная | Описание | Пример |
|-----------|---------|--------|
| `BOT_TOKEN` | Токен от @BotFather | `` |
| `ADMINS` | ID администраторов (через запятую) | `` |
| `CDEK_CLIENT_ID` | Client ID CDEK | ` |
| `CDEK_CLIENT_SECRET` | Client Secret CDEK | ` |
| `MINI_APP_URL` | URL к index_updated.html | `` |

### Параметры CDEK

В `cdek_integration.py`:
```python
SENDER_CITY_CODE = 442  # Улан-Удэ
PACKAGE_WEIGHT = 0.9  # кг
PACKAGE_LENGTH = 30  # см
PACKAGE_WIDTH = 25  # см
PACKAGE_HEIGHT = 10  # см
```

**Меняешь эти параметры в зависимости от твоей посылки.**

---

## 📂 Структура кода

### cdek_integration.py — Модули

```python
# 1. OAuth Токен
async def get_cdek_oauth_token() -> Optional[str]:
    """Получить OAuth2 токен CDEK"""

# 2. Поиск города
async def get_city_code(city_name: str) -> Optional[int]:
    """Получить код города по названию"""

# 3. Расчет доставки (ОСНОВНАЯ ФУНКЦИЯ)
async def calculate_shipping(city_name: str) -> Tuple[int, str]:
    """
    Рассчитать доставку до города
    
    Returns:
        (500, "Доставка (сумма по умолчанию)")  # При ошибке
        (750, "Доставка: Экспресс 1 день")      # При успехе
    """

# 4. Валидация
async def validate_phone(phone: str) -> bool:
async def validate_city(city_name: str) -> bool:

# 5. Демо
async def demo_cdek():
```

### bot_with_cdek.py — Handlers

**Aiogram Handlers:**
```python
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Показать кнопку Mini App"""

@dp.message(types.Message)
async def handle_web_app_data(message: types.Message):
    """Получить и обработать заказ из Mini App"""
```

**FastAPI Endpoints:**
```python
@app.post("/api/calculate-shipping")
async def calculate_shipping_endpoint(request: Request) -> Dict:
    """POST: {"city": "Москва"} -> {"cost": 500, "description": "..."}"""

@app.get("/api/health")
async def health_check():
    """Проверка статуса бота и CDEK"""
```

### index_updated.html — Frontend

Ключевые функции:
```javascript
// Подсказки города
async function onCityInput(e)
async function selectCity(cityName)

// Запрос доставки к API
const response = await fetch('/api/calculate-shipping', {
    method: 'POST',
    body: JSON.stringify({ city: cityName })
});

// Форматирование телефона
function formatPhone(e)

// Отправка заказа
function sendOrder()
```

---

## 🌐 API Endpoints

### 1. Расчет доставки

```http
POST /api/calculate-shipping
Content-Type: application/json

{
    "city": "Москва"
}
```

**Ответ (успех):**
```json
{
    "cost": 450,
    "description": "Доставка: Стандартная доставка до 5 дней",
    "city": "Москва"
}
```

**Ответ (ошибка):**
```json
{
    "cost": 500,
    "description": "Доставка (город не найден, дефолтная стоимость)",
    "city": "Москва"
}
```

### 2. Проверка здоровья

```http
GET /api/health
```

**Ответ:**
```json
{
    "status": "ok",
    "cdek_connected": true,
    "bot_initialized": true
}
```

### 3. Главная страница API

```http
GET /
```

---

## 🐛 Дебаг и тестирование

### Тест CDEK интеграции

```bash
python cdek_integration.py
```

Выведет:
```
🚀 ДЕМО CDEK INTEGRATION
==================================================

1️⃣ ТЕСТ ПОЛУЧЕНИЯ ТОКЕНА:
✅ Токен получен: eyJhbGciOiJIUzI1NiIsIn...

2️⃣ ТЕСТ ПОИСКА ГОРОДА:
✅ Москва: код 1
✅ Санкт-Петербург: код 2
✅ Новосибирск: код 1220

3️⃣ ТЕСТ РАСЧЕТА ДОСТАВКИ:
  Москва: 450 руб - Доставка: Стандартная доставка
  ...

✅ Демо завершено
```

### Логирование

В файлах видно детальное логирование:
```
2024-01-15 10:30:45 - cdek_integration - INFO - ✅ Получен новый CDEK OAuth токен
2024-01-15 10:30:46 - cdek_integration - INFO - ✅ Найден код города 'Москва': 1
2024-01-15 10:30:48 - cdek_integration - INFO - ✅ Стоимость доставки в 'Москва': 450 руб
```

### Тестирование через curl

```bash
# Проверка API
curl -X GET http://127.0.0.1:8000/api/health

# Расчет доставки
curl -X POST http://127.0.0.1:8000/api/calculate-shipping \
  -H "Content-Type: application/json" \
  -d '{"city": "Москва"}'
```

---

## ⚠️ Обработка ошибок

### Что происходит при ошибке?

| Ошибка | Результат | Код |
|-------|-----------|------|
| Неверные CDEK ключи | Возврат 500 ₽ | CDEK auth failed |
| Город не найден | Возврат 500 ₽ | City not found |
| CDEK API недоступен | Возврат 500 ₽ | Timeout/Connection Error |
| Нет тарифов | Возврат 500 ₽ | No tariffs available |

### Примеры ошибок в логах

```
❌ CDEK_CLIENT_ID или CDEK_CLIENT_SECRET не установлены!
⚠️ Используем дефолт 500 руб

⏱️ Timeout при расчете доставки в 'Москва'
🌐 Ошибка сетевого соединения CDEK: ...

⚠️ Город 'Неизвестный город' не найден в СДЭК
```

### Кэширование токена

Токен CDEK автоматически кэшируется на 55 минут (1 час - 5 минут буфер). При каждом запросе проверяется валидность и переиспользуется кэшированный токен для экономии API запросов.

---

## 📝 Примеры использования

### Пример 1: Использование в своем боте

```python
from cdek_integration import calculate_shipping

# В твоем handler'е
@dp.message(...)
async def my_handler(message: types.Message):
    cost, description = await calculate_shipping("Москва")
    await message.answer(f"Доставка: {cost} ₽")
```

### Пример 2: Валидация без расчета

```python
from cdek_integration import validate_city, validate_phone

is_valid_city = await validate_city("Москва")
is_valid_phone = await validate_phone("+7 999 123 45 67")
```

### Пример 3: Получение токена для других операций

```python
from cdek_integration import get_cdek_oauth_token

token = await get_cdek_oauth_token()
if token:
    # Использовать token для других CDEK API запросов
    pass
else:
    # Ошибка получения токена
    pass
```

---

## 🔐 Безопасность

### ✅ Что уже защищено:

1. **CDEK ключи хранятся в .env** — никогда не коммитим в Git
2. **OAuth токен кэшируется** — минимизируем запросы
3. **Ошибки обрабатываются** — не ломаем заказ при проблемах
4. **Валидация данных** — проверяем входные данные
5. **Логирование** — все операции записываются

### ⚠️ Что нужно сделать:

1. **Добавь .env в .gitignore:**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **Не коммитай реальные ключи** — используй .env.example

3. **На продакшене используй переменные окружения:**
   ```bash
   export BOT_TOKEN="твой_токен"
   export CDEK_CLIENT_ID="твой_id"
   export CDEK_CLIENT_SECRET="твой_secret"
   ```

---

## 🚀 Продакшн деплой

### Вариант 1: Systemd сервис

Создай `/etc/systemd/system/mngnv-bot.service`:
```ini
[Unit]
Description=mngnv Shop Bot with CDEK
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 /path/to/bot/bot_with_cdek.py
Restart=always
RestartSec=10

Environment="BOT_TOKEN=your_token"
Environment="CDEK_CLIENT_ID=your_id"
Environment="CDEK_CLIENT_SECRET=your_secret"

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl enable mngnv-bot
sudo systemctl start mngnv-bot
sudo systemctl status mngnv-bot
```

### Вариант 2: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot_with_cdek.py"]
```

```bash
docker build -t mngnv-bot .
docker run -d -e BOT_TOKEN=... -e CDEK_CLIENT_ID=... mngnv-bot
```

---

## 📞 Поддержка и контрибьютинг

**Если что-то не работает:**

1. Проверь логи:
   ```bash
   tail -f bot_with_cdek.log
   ```

2. Убедись что CDEK ключи правильные в .env

3. Запусти тест:
   ```bash
   python cdek_integration.py
   ```

4. Проверь статус API:
   ```bash
   curl http://127.0.0.1:8000/api/health
   ```

---

## 📄 Лицензия

Код готов к использованию в любых целях.

---

**Удачи с магазином!** 🛍️✨
