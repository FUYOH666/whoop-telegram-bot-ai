# Решение проблем с подключением WHOOP

## Проблема: Ошибка 400 "invalid_grant"

Эта ошибка обычно означает одно из следующего:

### 1. Authorization code истек
**Решение:** Authorization codes действительны только **1-2 минуты**. Нужно получить новый код и использовать его сразу.

**Шаги:**
1. Отправьте боту `/whoop_connect`
2. **Сразу** после авторизации в WHOOP скопируйте code из URL
3. **Немедленно** отправьте `/whoop_code <ваш_code>` боту

### 2. Authorization code уже использован
**Решение:** Каждый code можно использовать только один раз. Получите новый через `/whoop_connect`.

### 3. Redirect URI не совпадает
**Проверьте:**
- В WHOOP Developer Platform должен быть указан: `https://t.me/RAS_AI_bot?start=whoop_auth`
- В `config.yaml` должен быть тот же URL: `https://t.me/RAS_AI_bot?start=whoop_auth`
- Они должны совпадать **ТОЧНО**, включая регистр и все символы

### 4. Client ID/Secret неверны
**Проверьте:**
- `WHOOP_CLIENT_ID` в `.env` совпадает с Client ID в WHOOP Developer Platform
- `WHOOP_CLIENT_SECRET` в `.env` совпадает с Client Secret в WHOOP Developer Platform

## Быстрое решение

1. **Получите новый код:**
   ```
   /whoop_connect
   ```

2. **Авторизуйтесь в WHOOP** (откроется браузер)

3. **Сразу после авторизации:**
   - Скопируйте только сам code из URL (часть после `code=`)
   - Не копируйте `&scope=...` и другие параметры
   - Пример: `js2cjtzA1CjRGgZgEETbjf3pk9DvAdtZ6WneQKD7WjI.rQUahhao503aN9KYQtDz2UL5NNZ7E5qjb0n01IfkUYA`

4. **Немедленно отправьте:**
   ```
   /whoop_code js2cjtzA1CjRGgZgEETbjf3pk9DvAdtZ6WneQKD7WjI.rQUahhao503aN9KYQtDz2UL5NNZ7E5qjb0n01IfkUYA
   ```

## Проверка через терминал

Если хотите проверить подключение через терминал:

```bash
cd /Users/aleksandrmordvinov/development/RAS-TGbot
uv run python manual_whoop_connect.py "ВАШ_СВЕЖИЙ_CODE"
```

**Важно:** Code должен быть получен **прямо сейчас** (в течение последней минуты).

## Проверка текущего статуса

```bash
cd /Users/aleksandrmordvinov/development/RAS-TGbot
uv run python test_whoop_connection.py
```

Этот скрипт покажет:
- Настроена ли конфигурация WHOOP
- Есть ли токены в БД
- Работает ли подключение (если токены есть)

