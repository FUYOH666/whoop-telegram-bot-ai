#!/usr/bin/env python3
"""Ручное подключение WHOOP через authorization code."""

import asyncio
import sys
from ras_bot.config import Config
from ras_bot.storage import Storage
from ras_bot.whoop_client import WhoopClient


async def manual_connect(authorization_code: str):
    """Ручное подключение WHOOP."""
    print("=== Ручное подключение WHOOP ===\n")
    
    # Загружаем конфигурацию
    config = Config()
    if not config.whoop.is_configured:
        print("❌ WHOOP не настроен. Проверьте .env файл")
        return False
    
    storage = Storage()
    user_id = 8347160745  # Ваш user_id
    
    # Очищаем code от лишних параметров
    code = authorization_code.split("&")[0].split("?")[0].split()[0].strip()
    print(f"Используемый code: {code[:50]}...")
    print(f"Redirect URI: {config.whoop.redirect_uri}\n")
    
    whoop_client = WhoopClient(config.whoop, storage)
    
    try:
        print("Обмениваю authorization code на токены...")
        tokens = await whoop_client.exchange_code_for_tokens(user_id, code)
        
        print("\n✅ Успешно подключено!")
        print(f"   Access token: {tokens['access_token'][:30]}...")
        print(f"   Refresh token: {tokens['refresh_token'][:30]}...")
        print(f"   Expires in: {tokens['expires_in']} секунд")
        
        # Пробуем получить данные для проверки
        print("\nПроверяю получение данных...")
        data = await whoop_client.get_all_data(user_id)
        
        if data:
            print("✅ Данные получены:")
            print(f"   Recovery: {data.get('recovery_score')}")
            print(f"   Sleep: {data.get('sleep_duration')}ч")
            print(f"   Strain: {data.get('strain_score')}")
            print(f"   Workouts: {data.get('workouts_count')}")
        else:
            print("⚠️ Данных за сегодня нет (это нормально, если еще рано)")
        
        await whoop_client.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        await whoop_client.close()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python manual_whoop_connect.py <authorization_code>")
        print("\nПример:")
        print("  python manual_whoop_connect.py 'pZMzwLi5vZK0kziUQVoqnK3oCEmzZnJr-2V8cNRoKNI.WOn13n6o0oUYgVX1ouWKcqVaWZYyDGQwBrQcOjLRcZQ'")
        sys.exit(1)
    
    code = sys.argv[1]
    success = asyncio.run(manual_connect(code))
    sys.exit(0 if success else 1)

