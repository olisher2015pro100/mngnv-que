#!/usr/bin/env python3
"""
🔧 DIAGNOSTIC TOOL - Инструмент для диагностики и мониторинга
Проверит все компоненты и выведет отчет о состоянии
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Красивый заголовок"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text: str):
    """Зеленый текст (успех)"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    """Красный текст (ошибка)"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text: str):
    """Желтый текст (предупреждение)"""
    print(f"{Colors.YELLOW}⚠️ {text}{Colors.END}")

def print_info(text: str):
    """Голубой текст (информация)"""
    print(f"{Colors.BLUE}ℹ️ {text}{Colors.END}")


async def check_imports() -> Tuple[bool, List[str]]:
    """Проверить импорты всех модулей"""
    
    print_info("Проверяю импорты...")
    
    required_modules = [
        'aiogram',
        'aiohttp',
        'fastapi',
        'uvicorn',
        'dotenv'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print_success(f"Модуль '{module}' установлен")
        except ImportError:
            print_error(f"Модуль '{module}' НЕ установлен")
            missing.append(module)
    
    return len(missing) == 0, missing


async def check_files() -> Dict[str, bool]:
    """Проверить наличие всех нужных файлов"""
    
    print_info("Проверяю файлы...")
    
    files = {
        'cdek_integration.py': 'Модуль CDEK',
        'bot_with_cdek.py': 'Бот + API',
        'index_updated.html': 'Mini App фронтенд',
        '.env': 'Конфиг окружения',
        'requirements.txt': 'Зависимости',
    }
    
    results = {}
    for filename, description in files.items():
        path = Path(filename)
        if path.exists():
            size = path.stat().st_size
            print_success(f"{description}: {filename} ({size} байт)")
            results[filename] = True
        else:
            print_error(f"{description}: {filename} НЕ НАЙДЕН")
            results[filename] = False
    
    return results


async def check_env_config() -> Tuple[bool, Dict[str, str]]:
    """Проверить .env конфиг"""
    
    print_info("Проверяю .env конфиг...")
    
    required_keys = [
        'BOT_TOKEN',
        'CDEK_CLIENT_ID',
        'CDEK_CLIENT_SECRET',
        'MINI_APP_URL'
    ]
    
    env_data = {}
    missing_keys = []
    
    env_path = Path('.env')
    if not env_path.exists():
        print_error(".env файл НЕ НАЙДЕН")
        return False, {}
    
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_data[key.strip()] = value.strip()
        
        for key in required_keys:
            if key in env_data and env_data[key]:
                value = env_data[key]
                # Не показываем полные значения ключей
                if len(value) > 20:
                    display_value = value[:10] + "..." + value[-5:]
                else:
                    display_value = value
                print_success(f"{key}: {display_value}")
            else:
                print_error(f"{key}: ОТСУТСТВУЕТ или пуст")
                missing_keys.append(key)
        
        return len(missing_keys) == 0, env_data
        
    except Exception as e:
        print_error(f"Ошибка чтения .env: {e}")
        return False, {}


async def check_cdek_module() -> bool:
    """Проверить CDEK модуль"""
    
    print_info("Проверяю CDEK модуль...")
    
    try:
        from cdek_integration import (
            get_cdek_oauth_token,
            calculate_shipping,
            validate_phone,
            validate_city
        )
        
        print_success("Функция get_cdek_oauth_token импортирована")
        print_success("Функция calculate_shipping импортирована")
        print_success("Функция validate_phone импортирована")
        print_success("Функция validate_city импортирована")
        
        return True
        
    except ImportError as e:
        print_error(f"Ошибка импорта cdek_integration.py: {e}")
        return False
    except Exception as e:
        print_error(f"Ошибка проверки CDEK модуля: {e}")
        return False


async def check_bot_module() -> bool:
    """Проверить бот модуль"""
    
    print_info("Проверяю бот модуль...")
    
    try:
        # Только проверим что файл валидный Python
        import ast
        with open('bot_with_cdek.py', 'r', encoding='utf-8') as f:
            code = f.read()
            ast.parse(code)
        
        print_success("bot_with_cdek.py имеет корректный синтаксис Python")
        return True
        
    except SyntaxError as e:
        print_error(f"Синтаксис ошибка в bot_with_cdek.py: {e}")
        return False
    except Exception as e:
        print_error(f"Ошибка проверки bot_with_cdek.py: {e}")
        return False


async def check_cdek_connectivity() -> bool:
    """Проверить связь с CDEK API"""
    
    print_info("Проверяю связь с CDEK API...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Точная проверка на рабочий эндпоинт (как в cdek_integration.py)
            # Используем /v2/calculator/tarifflist который мы реально используем
            # Достаточно проверить что URL доступен, даже без параметров
            async with session.get('https://api.cdek.ru/v2/calculator/tarifflist', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                # Статус 400+ OK - сервер доступен (может требовать параметры)
                if 200 <= resp.status < 500:
                    print_success(f"CDEK API доступен (https://api.cdek.ru/v2/calculator/tarifflist)")
                    return True
                else:
                    print_error(f"CDEK API ответил статусом {resp.status}")
                    return False
        
    except asyncio.TimeoutError:
        print_error("Timeout при подключении к CDEK (проверь интернет)")
        return False
    except aiohttp.ClientError as e:
        print_error(f"Ошибка подключения к CDEK: {e}")
        return False
    except Exception as e:
        print_error(f"Неожиданная ошибка при проверке CDEK: {e}")
        return False


async def check_port_availability(port: int = 8000) -> bool:
    """Проверить доступность порта"""
    
    print_info(f"Проверяю портт {port}...")
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print_warning(f"Порт {port} ЗАНЯТ (может быть запущен другой bot)")
            return False
        else:
            print_success(f"Порт {port} свободен")
            return True
            
    except Exception as e:
        print_warning(f"Ошибка проверки порта: {e}")
        return False


async def test_cdek_token() -> bool:
    """Протестировать получение токена от CDEK"""
    
    print_info("Тестирую получение CDEK токена...")
    
    try:
        from cdek_integration import get_cdek_oauth_token
        
        token = await get_cdek_oauth_token()
        
        if token:
            display_token = token[:20] + "..." + token[-5:] if len(token) > 30 else "***"
            print_success(f"Токен получен: {display_token}")
            return True
        else:
            print_error("Токен не получен (проверь CDEK_CLIENT_ID и CDEK_CLIENT_SECRET в .env)")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при получении токена: {e}")
        return False


async def test_cdek_shipping() -> bool:
    """Протестировать расчет доставки"""
    
    print_info("Тестирую расчет доставки...")
    
    try:
        from cdek_integration import calculate_shipping
        
        cost, description = await calculate_shipping("Москва")
        
        print_success(f"Доставка в Москву: {cost} ₽")
        print_info(f"Описание: {description}")
        
        return True
        
    except Exception as e:
        print_error(f"Ошибка при расчете доставки: {e}")
        return False


async def generate_report(results: Dict) -> str:
    """Сгенерировать итоговый отчет"""
    
    print_header("📋 ИТОГОВЫЙ ОТЧЕТ")
    
    total_checks = len(results)
    passed_checks = sum(1 for v in results.values() if v is True)
    failed_checks = sum(1 for v in results.values() if v is False)
    
    percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    print(f"Всего проверок: {total_checks}")
    print_success(f"Пройдено: {passed_checks}")
    print_error(f"Не пройдено: {failed_checks}")
    print_info(f"Процент готовности: {percentage:.0f}%")
    
    print(f"\n{Colors.BOLD}Статус компонентов:{Colors.END}")
    
    status_map = {
        'imports': 'Импорты',
        'files': 'Файлы',
        'env': 'Конфиг (.env)',
        'cdek_module': 'CDEK модуль',
        'bot_module': 'Бот модуль',
        'cdek_api': 'CDEK API доступ',
        'port': 'Порт 8000',
        'cdek_token': 'Токен CDEK',
        'cdek_shipping': 'Расчет доставки'
    }
    
    for key, label in status_map.items():
        if key in results:
            if results[key] is True:
                print_success(f"{label}")
            elif results[key] is False:
                print_error(f"{label}")
            else:
                print_info(f"{label}")
    
    if percentage == 100:
        print_success("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Можешь запустить бота!")
        return "OK"
    elif percentage >= 80:
        print_warning("\n⚠️ Большинство проверок пройдено. Могут быть проблемы.")
        return "WARNING"
    else:
        print_error("\n❌ Много проблем. Смотри TROUBLESHOOTING.md")
        return "ERROR"


async def main():
    """Главная функция диагностики"""
    
    print_header("🔧 ДИАГНОСТИКА DIY Mini App + CDEK")
    
    results = {}
    
    # Проверка 1: Импорты
    try:
        ok, missing = await check_imports()
        results['imports'] = ok
        if not ok:
            print_error(f"Установи: pip install {' '.join(missing)}")
    except Exception as e:
        print_error(f"Ошибка проверки импортов: {e}")
        results['imports'] = False
    
    # Проверка 2: Файлы
    try:
        files_ok = await check_files()
        results['files'] = all(files_ok.values())
    except Exception as e:
        print_error(f"Ошибка проверки файлов: {e}")
        results['files'] = False
    
    # Проверка 3: .env конфиг
    try:
        env_ok, env_data = await check_env_config()
        results['env'] = env_ok
    except Exception as e:
        print_error(f"Ошибка проверки .env: {e}")
        results['env'] = False
    
    # Проверка 4: CDEK модуль
    try:
        cdek_mod_ok = await check_cdek_module()
        results['cdek_module'] = cdek_mod_ok
    except Exception as e:
        print_error(f"Ошибка проверки CDEK модуля: {e}")
        results['cdek_module'] = False
    
    # Проверка 5: Бот модуль
    try:
        bot_mod_ok = await check_bot_module()
        results['bot_module'] = bot_mod_ok
    except Exception as e:
        print_error(f"Ошибка проверки бот модуля: {e}")
        results['bot_module'] = False
    
    # Проверка 6: CDEK API доступ
    try:
        cdek_api_ok = await check_cdek_connectivity()
        results['cdek_api'] = cdek_api_ok
    except Exception as e:
        print_error(f"Ошибка проверки CDEK API: {e}")
        results['cdek_api'] = False
    
    # Проверка 7: Портт
    try:
        port_ok = await check_port_availability(8000)
        results['port'] = port_ok
    except Exception as e:
        print_error(f"Ошибка проверки порта: {e}")
        results['port'] = False
    
    # Проверка 8: CDEK токен (только если .env заполнен)
    try:
        if results.get('env', False):
            token_ok = await test_cdek_token()
            results['cdek_token'] = token_ok
        else:
            print_warning("Пропускаю тест токена (.env не заполнен)")
            results['cdek_token'] = None
    except Exception as e:
        print_error(f"Ошибка тестирования токена: {e}")
        results['cdek_token'] = False
    
    # Проверка 9: Расчет доставки
    try:
        if results.get('cdek_token', False) is True:
            shipping_ok = await test_cdek_shipping()
            results['cdek_shipping'] = shipping_ok
        else:
            print_warning("Пропускаю тест доставки (токен не получен)")
            results['cdek_shipping'] = None
    except Exception as e:
        print_error(f"Ошибка тестирования доставки: {e}")
        results['cdek_shipping'] = False
    
    # Финальный отчет
    status = await generate_report(results)
    
    # Рекомендации
    print(f"\n{Colors.BOLD}💡 Рекомендации:{Colors.END}")
    
    if results.get('imports') is False:
        print_error("✨ Установи зависимости: pip install -r requirements.txt")
    
    if results.get('env') is False:
        print_error("✨ Заполни .env file: cp .env.example .env")
    
    if results.get('cdek_api') is False:
        print_warning("✨ Проверь интернет соединение")
    
    if results.get('port') is False:
        print_warning("✨ Закрой процесс на порту 8000 или используй другой порт")
    
    if status == "OK":
        print_success("\n✨ Можешь запустить: python bot_with_cdek.py")
    
    return 0 if status in ["OK", "WARNING"] else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n❌ Диагностика отменена пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        sys.exit(1)
