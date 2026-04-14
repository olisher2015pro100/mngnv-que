"""
СДЭК API v2.0 Интеграция для Telegram Mini App
Асинхронный модуль для расчета доставки с OAuth токеном
"""

import aiohttp
import asyncio
import logging
import os
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# ==========================================
# КОНФИГ И ПЕРЕМЕННЫЕ
# ==========================================

# ⚠️ ЗАПОЛНИ СВОИ КЛЮЧИ В .env файл:
CDEK_CLIENT_ID = os.getenv("CDEK_CLIENT_ID", "")
CDEK_CLIENT_SECRET = os.getenv("CDEK_CLIENT_SECRET", "")

# API endpoints
CDEK_AUTH_URL = "https://api.cdek.ru/v2/oauth/token"
CDEK_CALC_URL = "https://api.cdek.ru/v2/calculator/tarifflist"
CDEK_CITIES_URL = "https://api.cdek.ru/v2/location/cities"

# Параметры посылки
SENDER_CITY_CODE = 442  # Улан-Удэ
PACKAGE_WEIGHT = 0.9  # кг
PACKAGE_LENGTH = 30  # см
PACKAGE_WIDTH = 25  # см
PACKAGE_HEIGHT = 10  # см

# Кэширование токена (простое решение)
_token_cache: Dict[str, any] = {"token": None, "expires_at": None}

logger = logging.getLogger(__name__)


# ==========================================
# 1️⃣ ПОЛУЧЕНИЕ OAuth ТОКЕНА
# ==========================================

async def get_cdek_oauth_token() -> Optional[str]:
    """
    Получить OAuth токен CDEK API v2.0
    
    Returns:
        str: OAuth токен или None при ошибке
        
    Raises:
        Обработанные исключения записываются в лог
    """
    
    # Проверяем кэш
    if _token_cache["token"] and _token_cache["expires_at"]:
        if datetime.now() < _token_cache["expires_at"]:
            logger.debug("🔑 Используем кэшированный токен CDEK")
            return _token_cache["token"]
    
    # Проверка наличия ключей
    if not CDEK_CLIENT_ID or not CDEK_CLIENT_SECRET:
        logger.error("❌ CDEK_CLIENT_ID или CDEK_CLIENT_SECRET не установлены!")
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "grant_type": "client_credentials",
                "client_id": CDEK_CLIENT_ID,
                "client_secret": CDEK_CLIENT_SECRET
            }
            
            # ⚠️ ВАЖНО: CDEK требует form-encoded, не JSON!
            async with session.post(CDEK_AUTH_URL, data=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    
                    # Сохраняем в кэш (на 5 минут меньше, чем реальное время)
                    _token_cache["token"] = token
                    _token_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 300)
                    
                    logger.info(f"✅ Получен новый CDEK OAuth токен (истечет через {expires_in}с)")
                    return token
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Ошибка получения токена CDEK (статус {resp.status}): {error_text}")
                    return None
                    
    except asyncio.TimeoutError:
        logger.error("⏱️ Timeout при попытке получить токен CDEK")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"🌐 Ошибка сетевого соединения CDEK: {e}")
        return None
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка при получении токена: {e}")
        return None


# ==========================================
# 2️⃣ ПОЛУЧЕНИЕ КОДА ГОРОДА ПО НАЗВАНИЮ
# ==========================================

async def get_city_code(city_name: str) -> Optional[int]:
    """
    Получить код города СДЭК по названию
    
    Args:
        city_name: Название города
        
    Returns:
        int: Код города или None
    """
    
    token = await get_cdek_oauth_token()
    if not token:
        logger.warning(f"⚠️ Не удалось получить токен для поиска города '{city_name}'")
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            params = {"city": city_name, "size": 10}
            
            async with session.get(
                CDEK_CITIES_URL,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Обработка разных форматов ответа CDEK
                    cities = None
                    
                    # Вариант 1: data = {"city": [...]}
                    if isinstance(data, dict) and data.get("city"):
                        cities = data["city"]
                    # Вариант 2: data = [...]  (прямо список)
                    elif isinstance(data, list):
                        cities = data
                    
                    if cities and len(cities) > 0:
                        # Берем первый результат
                        first_city = cities[0]
                        
                        # Обработка разных форматов города
                        if isinstance(first_city, dict):
                            city_code = first_city.get("code")
                        elif isinstance(first_city, (int, str)):
                            city_code = int(first_city)
                        else:
                            city_code = None
                        
                        if city_code:
                            logger.info(f"✅ Найден код города '{city_name}': {city_code}")
                            return city_code
                    
                    logger.warning(f"⚠️ Город '{city_name}' не найден в СДЭК")
                    return None
                else:
                    logger.error(f"❌ Ошибка поиска города (статус {resp.status})")
                    return None
                    
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Timeout при поиске города '{city_name}'")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"🌐 Ошибка сетевого соединения при поиске города: {e}")
        return None
    except Exception as e:
        logger.error(f"💥 Ошибка при поиске города '{city_name}': {e}")
        return None


# ==========================================
# 3️⃣ РАСЧЕТ ДОСТАВКИ
# ==========================================

async def calculate_shipping(city_name: str) -> Tuple[int, str]:
    """
    Рассчитать стоимость доставки до города
    
    Args:
        city_name: Название города получателя (например "Москва")
        
    Returns:
        Tuple[int, str]: (стоимость в руб, описание)
                        При ошибке возвращает (500, "Доставка (сумма по умолчанию)")
                        
    Logika:
        1. Получаем код города
        2. Запрашиваем тариф доставки через CDEK API
        3. Если ошибка - возвращаем дефолт 500 руб
    """
    
    if not city_name or city_name.strip() == "":
        logger.warning("⚠️ Передано пустое имя города")
        return 500, "Доставка (сумма по умолчанию)"
    
    try:
        city_name = city_name.strip()
        
        # Получаем код города
        city_code = await get_city_code(city_name)
        if not city_code:
            logger.warning(f"⚠️ Не удалось найти код для города '{city_name}', используем дефолт 500 руб")
            return 500, "Доставка (город не найден, дефолтная стоимость)"
        
        # Получаем токен
        token = await get_cdek_oauth_token()
        if not token:
            logger.warning("⚠️ Не удалось получить токен CDEK, используем дефолт 500 руб")
            return 500, "Доставка (ошибка API, дефолтная стоимость)"
        
        # Запрашиваем тариф
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Основной тариф для посылок между ФФ - 5 (стандартная надежная)
            payload = {
                "from_location": {"code": SENDER_CITY_CODE},  # От Улан-Удэ (442)
                "to_location": {"code": city_code},  # До города получателя
                "packages": [
                    {
                        "weight": int(PACKAGE_WEIGHT * 1000),  # в граммах (900)
                        "length": int(PACKAGE_LENGTH),  # см
                        "width": int(PACKAGE_WIDTH),  # см
                        "height": int(PACKAGE_HEIGHT),  # см
                    }
                ]
            }
            
            # type передаем как параметр URL, а не в теле запроса!
            params = {"type": 36}
            
            async with session.post(
                CDEK_CALC_URL,
                json=payload,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Разбираем результат - CDEK может возвращать "result" или "tariff_codes"
                    tariffs = data.get("tariff_codes") or data.get("result")
                    
                    if tariffs and isinstance(tariffs, list) and len(tariffs) > 0:
                        # Берем самый дешевый тариф
                        cheapest = min(tariffs, key=lambda x: x.get("delivery_sum", float('inf')))
                        delivery_cost = int(cheapest.get("delivery_sum", 500))
                        tariff_name = cheapest.get("tariff_name", "Стандартная доставка")
                        
                        logger.info(f"✅ Стоимость доставки в '{city_name}': {delivery_cost} руб ({tariff_name})")
                        return delivery_cost, f"Доставка: {tariff_name}"
                    else:
                        logger.warning(f"⚠️ Нет доступных тарифов для '{city_name}'")
                        return 500, "Доставка (тариф недоступен, дефолтная стоимость)"
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Ошибка расчета доставки CDEK (статус {resp.status}): {error_text}")
                    return 500, "Доставка (сумма по умолчанию)"
                    
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Timeout при расчете доставки в '{city_name}'")
        return 500, "Доставка (timeout, дефолтная стоимость)"
    except aiohttp.ClientError as e:
        logger.error(f"🌐 Ошибка сетевого соединения при расчете доставки: {e}")
        return 500, "Доставка (ошибка сети, дефолтная стоимость)"
    except KeyError as e:
        logger.error(f"🔑 Ошибка парсинга ответа CDEK: {e}")
        return 500, "Доставка (ошибка парсинга, дефолтная стоимость)"
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка при расчете доставки: {e}")
        return 500, "Доставка (неизвестная ошибка, дефолтная стоимость)"


# ==========================================
# 4️⃣ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ВАЛИДАЦИИ
# ==========================================

async def validate_phone(phone: str) -> bool:
    """
    Простая валидация номера телефона (должен содержать минимум 10 цифр)
    
    Args:
        phone: Номер телефона
        
    Returns:
        bool: True если валиден, False если нет
    """
    digits = "".join(filter(str.isdigit, phone))
    is_valid = len(digits) >= 10
    
    if is_valid:
        logger.info(f"✅ Номер телефона валиден: {phone}")
    else:
        logger.warning(f"⚠️ Номер телефона невалиден: {phone}")
    
    return is_valid


async def validate_city(city_name: str) -> bool:
    """
    Валидация названия города (проверяет наличие в CDEK)
    
    Args:
        city_name: Название города
        
    Returns:
        bool: True если город найден, False если нет
    """
    city_code = await get_city_code(city_name)
    return city_code is not None


# ==========================================
# 5️⃣ ДЕМО ФУНКЦИЯ ДЛЯ ТЕСТИРОВАНИЯ
# ==========================================

async def demo_cdek():
    """Демо-функция для тестирования интеграции"""
    
    # Устанавливаем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 ДЕМО CDEK INTEGRATION")
    print("=" * 50)
    
    # Тест 1: Получение токена
    print("\n1️⃣ ТЕСТ ПОЛУЧЕНИЯ ТОКЕНА:")
    token = await get_cdek_oauth_token()
    if token:
        print(f"✅ Токен получен: {token[:20]}...")
    else:
        print("❌ Ошибка получения токена (проверьте CDEK_CLIENT_ID и CDEK_CLIENT_SECRET)")
    
    # Тест 2: Поиск города
    print("\n2️⃣ ТЕСТ ПОИСКА ГОРОДА:")
    test_cities = ["Москва", "Санкт-Петербург", "Новосибирск"]
    for city in test_cities:
        code = await get_city_code(city)
        if code:
            print(f"✅ {city}: код {code}")
        else:
            print(f"❌ {city}: не найден")
    
    # Тест 3: Расчет доставки
    print("\n3️⃣ ТЕСТ РАСЧЕТА ДОСТАВКИ:")
    test_destinations = ["Москва", "Санкт-Петербург", "Казань", "Неизвестный город"]
    for city in test_destinations:
        cost, description = await calculate_shipping(city)
        print(f"  {city}: {cost} руб - {description}")
    
    print("\n" + "=" * 50)
    print("✅ Демо завершено")


if __name__ == "__main__":
    asyncio.run(demo_cdek())
