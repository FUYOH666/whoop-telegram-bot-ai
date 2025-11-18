# Multi-stage build для RAS Bot
# Источник правды: uv.lock

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

# Установка uv
RUN pip install --no-cache-dir uv

# Копирование файлов проекта
COPY --chown=1000:1000 pyproject.toml uv.lock ./
COPY --chown=1000:1000 README.md ./
COPY --chown=1000:1000 src ./src
COPY --chown=1000:1000 config.yaml ./

# Синхронизация зависимостей из uv.lock (источник правды)
RUN uv sync --frozen --no-dev

# Установка пакета в editable mode, чтобы модуль был доступен
RUN uv pip install -e .

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 rasbot && \
    chown -R rasbot:rasbot /app

# Копирование зависимостей из builder
COPY --from=builder --chown=rasbot:rasbot /build/.venv /app/.venv
# Копируем файлы напрямую из исходников
COPY --chown=rasbot:rasbot pyproject.toml /app/
COPY --chown=rasbot:rasbot README.md /app/
COPY --chown=rasbot:rasbot src /app/src
COPY --chown=rasbot:rasbot config.yaml /app/config.yaml

# Установка uv для установки пакета
RUN pip install --no-cache-dir uv

# Установка пакета в editable mode для доступа к модулю
RUN uv pip install -e /app

# Переключение на непривилегированного пользователя
USER rasbot

# Переменные окружения
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

# Точка входа
CMD ["python", "-m", "ras_bot.main"]

