# Деплой Whoop Telegram Bot AI на сервер

Инструкции по запуску бота на Linux сервере для работы 24/7.

## Выбор хостинга

### Бесплатные варианты

#### 1. **Render** (PaaS - Platform as a Service)
- **Цена:** Бесплатно (750 часов/месяц)
- **Особенности:** 
  - Простое развертывание через GitHub
  - Автоматический деплой при push
  - Может "засыпать" после 15 минут простоя (но для бота это не критично)
- **Подходит для:** Тестирования и небольших проектов
- **Ссылка:** https://render.com

#### 2. **Railway** (PaaS)
- **Цена:** Бесплатно ($5 кредитов/месяц)
- **Особенности:**
  - Очень простое развертывание
  - Автоматический деплой из GitHub
  - Хорошая документация
- **Подходит для:** Быстрого старта
- **Ссылка:** https://railway.app

#### 3. **Fly.io**
- **Цена:** Бесплатно (3 shared-cpu VMs)
- **Особенности:**
  - Глобальная сеть (близко к пользователям)
  - Docker-based деплой
  - Хорошо для production
- **Подходит для:** Production проектов
- **Ссылка:** https://fly.io

#### 4. **Replit** (онлайн IDE + хостинг)
- **Цена:** Бесплатно (с ограничениями)
- **Особенности:**
  - Онлайн IDE встроен
  - Простое развертывание
  - Может быть нестабильным на бесплатном тарифе
- **Подходит для:** Быстрого прототипирования
- **Ссылка:** https://replit.com

### Дешевые VPS (от $2-5/месяц)

#### 1. **Hetzner Cloud**
- **Цена:** от €4.15/месяц (~$4.50)
- **Характеристики:** 2 vCPU, 4GB RAM, 40GB SSD
- **Особенности:**
  - Отличное соотношение цена/качество
  - Немецкое качество
  - Быстрые SSD
- **Подходит для:** Production
- **Ссылка:** https://www.hetzner.com/cloud

#### 2. **DigitalOcean**
- **Цена:** от $4/месяц
- **Характеристики:** 1 vCPU, 512MB RAM, 10GB SSD
- **Особенности:**
  - Отличная документация
  - Простое управление
  - Стабильность
- **Подходит для:** Начинающих и production
- **Ссылка:** https://www.digitalocean.com

#### 3. **Vultr**
- **Цена:** от $2.50/месяц
- **Характеристики:** 1 vCPU, 512MB RAM, 10GB SSD
- **Особенности:**
  - Очень дешево
  - Много локаций
  - Pay-as-you-go
- **Подходит для:** Бюджетных проектов
- **Ссылка:** https://www.vultr.com

#### 4. **Linode (Akamai)**
- **Цена:** от $5/месяц
- **Характеристики:** 1 vCPU, 1GB RAM, 25GB SSD
- **Особенности:**
  - Надежность
  - Хорошая поддержка
  - Простое управление
- **Подходит для:** Production
- **Ссылка:** https://www.linode.com

#### 5. **Contabo**
- **Цена:** от €3.99/месяц (~$4.30)
- **Характеристики:** 4 vCPU, 8GB RAM, 200GB SSD
- **Особенности:**
  - Очень много ресурсов за деньги
  - Хорошо для тяжелых проектов
- **Подходит для:** Если нужны ресурсы
- **Ссылка:** https://www.contabo.com

### Российские провайдеры

#### 1. **Timeweb Cloud**
- **Цена:** от 199₽/месяц (~$2)
- **Характеристики:** 1 vCPU, 1GB RAM, 10GB SSD
- **Особенности:**
  - Российский провайдер
  - Русскоязычная поддержка
  - Удобная панель
- **Ссылка:** https://timeweb.com/cloud

#### 2. **Selectel**
- **Цена:** от 200₽/месяц (~$2)
- **Характеристики:** 1 vCPU, 1GB RAM, 10GB SSD
- **Особенности:**
  - Российский провайдер
  - Хорошая инфраструктура
- **Ссылка:** https://selectel.ru

### Рекомендации для Whoop Telegram Bot AI

**Для начала (бесплатно):**
- **Render** или **Railway** — простое развертывание, достаточно для тестирования

**Для production (дешево):**
- **Hetzner Cloud** (€4.15/мес) — лучшее соотношение цена/качество
- **Vultr** ($2.50/мес) — самый дешевый вариант
- **DigitalOcean** ($4/мес) — если нужна простота

**Минимальные требования для Whoop Telegram Bot AI:**
- 512MB RAM (достаточно)
- 1 vCPU (достаточно)
- 10GB SSD (более чем достаточно)
- Ubuntu 22.04 или Debian 12

**Примечание:** Whoop Telegram Bot AI очень легкий (6 запросов в день к OpenRouter, SQLite БД), поэтому даже самый дешевый VPS справится без проблем.

## Быстрый старт на Render (бесплатно)

Если хотите быстро задеплоить бесплатно:

1. Зарегистрируйтесь на https://render.com
2. Подключите GitHub репозиторий
3. Создайте новый **"Background Worker"** (не Web Service!)
4. Укажите:
   - Build Command: `pip install uv && uv sync`
   - Start Command: `uv run python -m whoop_telegram_bot_ai.main`
5. Добавьте переменные окружения из `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENROUTER_API_KEY`
   - `TELEGRAM_USER_ID` (опционально)
6. Deploy!

**Примечание:** Render может "засыпать" после простоя, но для бота это не критично — он будет работать по расписанию. Для production лучше использовать VPS.

## Вариант 1: Docker (рекомендуется)

### Требования

- Docker и Docker Compose установлены на сервере
- Файл `.env` с секретами

### Шаги деплоя

1. **Скопируйте проект на сервер:**

```bash
# На вашем компьютере
scp -r /path/to/whoop-telegram-bot-ai user@your-server:/opt/whoop-telegram-bot-ai
```

2. **На сервере создайте `.env` файл:**

```bash
cd /opt/whoop-telegram-bot-ai
nano .env
# Вставьте ваши секреты:
# TELEGRAM_BOT_TOKEN=...
# OPENROUTER_API_KEY=...
# TELEGRAM_USER_ID=... (опционально)
```

3. **Запустите через Docker Compose:**

```bash
docker-compose up -d
```

4. **Проверьте логи:**

```bash
docker-compose logs -f
```

5. **Остановка:**

```bash
docker-compose down
```

6. **Обновление:**

```bash
git pull  # если используете git
docker-compose build --no-cache
docker-compose up -d
```

### Преимущества Docker:

- Автоматический перезапуск при сбоях (`restart: unless-stopped`)
- Изоляция окружения
- Легкое обновление
- Логирование встроено

## Вариант 2: Systemd Service

### Создание service файла

Создайте файл `/etc/systemd/system/whoop-telegram-bot-ai.service`:

```ini
[Unit]
Description=Whoop Telegram Bot AI
After=network.target

[Service]
Type=simple
User=whoopbot
WorkingDirectory=/opt/whoop-telegram-bot-ai
Environment="PATH=/opt/whoop-telegram-bot-ai/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/whoop-telegram-bot-ai/.venv/bin/python -m whoop_telegram_bot_ai.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Управление service

```bash
# Запуск
sudo systemctl start whoop-telegram-bot-ai

# Автозапуск при загрузке системы
sudo systemctl enable whoop-telegram-bot-ai

# Проверка статуса
sudo systemctl status whoop-telegram-bot-ai

# Просмотр логов
sudo journalctl -u whoop-telegram-bot-ai -f

# Остановка
sudo systemctl stop whoop-telegram-bot-ai
```

## Вариант 3: Screen/Tmux (быстрое решение)

### Использование screen:

```bash
# Установка screen (если нет)
sudo apt install screen  # Debian/Ubuntu
# или
sudo yum install screen  # CentOS/RHEL

# Создание сессии
screen -S whoop-telegram-bot-ai

# Запуск бота
cd /opt/whoop-telegram-bot-ai
uv run python -m whoop_telegram_bot_ai.main

# Отключение: Ctrl+A, затем D

# Подключение обратно
screen -r whoop-telegram-bot-ai
```

### Использование tmux:

```bash
# Установка tmux
sudo apt install tmux

# Создание сессии
tmux new -s whoop-telegram-bot-ai

# Запуск бота
cd /opt/whoop-telegram-bot-ai
uv run python -m whoop_telegram_bot_ai.main

# Отключение: Ctrl+B, затем D

# Подключение обратно
tmux attach -t whoop-telegram-bot-ai
```

## Рекомендации

1. **Используйте Docker** — самый надежный вариант с автоперезапуском
2. **Настройте мониторинг** — можно добавить простой health-check скрипт
3. **Резервное копирование БД** — регулярно копируйте `whoop_telegram_bot_ai.db`
4. **Логи** — настройте ротацию логов (Docker делает это автоматически)

## Проверка работы

После деплоя проверьте:

```bash
# В Telegram отправьте боту
/health

# Должно показать:
# ✅ Telegram API: OK
# ✅ OpenRouter API: OK
# ✅ База данных: OK
```

## Troubleshooting

**Бот не запускается:**
- Проверьте `.env` файл и секреты
- Проверьте логи: `docker-compose logs` или `journalctl -u whoop-telegram-bot-ai`
- Убедитесь, что порты не заняты

**Бот не отправляет сообщения:**
- Убедитесь, что отправили `/start` боту
- Проверьте `TELEGRAM_USER_ID` в `.env`
- Проверьте настройки приватности OpenRouter

