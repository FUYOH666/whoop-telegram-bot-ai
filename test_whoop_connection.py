#!/usr/bin/env python3
"""Тестовый скрипт для проверки подключения WHOOP."""

import asyncio
import sys
from ras_bot.config import Config
from ras_bot.storage import Storage
from ras_bot.whoop_client import WhoopClient


async def test_whoop_connection():
    """Тестирование подключения WHOOP."""
    print("=== Тест подключения WHOOP ===\n")
    
    # Загружаем конфигурацию
    try:
        config = Config()
        print(f"✅ Конфигурация загружена")
        print(f"   WHOOP configured: {config.whoop.is_configured}")
        print(f"   Redirect URI: {config.whoop.redirect_uri}")
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return
    
    if not config.whoop.is_configured:
        print("\n❌ WHOOP не настроен. Проверьте WHOOP_CLIENT_ID и WHOOP_CLIENT_SECRET в .env")
        return
    
    # Проверяем хранилище
    storage = Storage()
    user_id = 8347160745  # Ваш user_id
    
    # Проверяем существующие токены
    tokens = storage.get_whoop_tokens(user_id)
    if tokens:
        print(f"\n✅ Токены найдены в БД для user_id {user_id}")
        print(f"   Expires at: {tokens['expires_at']}")
        
        # Пробуем использовать существующие токены
        whoop_client = WhoopClient(config.whoop, storage)
        try:
            print("\n=== Тест получения данных WHOOP ===")
            today_data = await whoop_client.get_all_data(user_id)
            
            if today_data:
                print("✅ Данные получены успешно:")
                print(f"   Recovery: {today_data.get('recovery_score')}")
                print(f"   Sleep: {today_data.get('sleep_duration')}ч")
                print(f"   Strain: {today_data.get('strain_score')}")
                print(f"   Workouts: {today_data.get('workouts_count')}")
            else:
                print("⚠️ Данные не получены (возможно, нет данных за сегодня)")
        except Exception as e:
            print(f"❌ Ошибка при получении данных: {e}")
            print("\nВозможные причины:")
            print("  - Токены истекли и не обновились")
            print("  - Проблема с API WHOOP")
            print("  - Нет данных за сегодня")
        finally:
            await whoop_client.close()
    else:
        print(f"\n❌ Токены не найдены для user_id {user_id}")
        print("\nДля подключения:")
        print("1. Отправьте боту команду: /whoop_connect")
        print("2. Авторизуйтесь в WHOOP")
        print("3. Скопируйте authorization code из URL")
        print("4. Отправьте боту: /whoop_code <ваш_code>")
        
        # Показываем пример URL для авторизации
        whoop_client = WhoopClient(config.whoop, storage)
        auth_url = whoop_client.get_authorization_url(user_id)
        print(f"\nПример URL для авторизации:")
        print(auth_url)
        await whoop_client.close()


if __name__ == "__main__":
    asyncio.run(test_whoop_connection())

