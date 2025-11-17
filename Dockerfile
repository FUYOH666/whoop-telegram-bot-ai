# Multi-stage build для RAS Bot
# Источник правды: uv.lock

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /build

# Установка uv
COPY --chown=1000:1000 . /build/
RUN pip install --no-cache-dir uv

# Синхронизация зависимостей из uv.lock (источник правды)
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 rasbot && \
    chown -R rasbot:rasbot /app

# Копирование зависимостей из builder
COPY --from=builder --chown=rasbot:rasbot /build/.venv /app/.venv
COPY --chown=rasbot:rasbot /build/src /app/src
COPY --chown=rasbot:rasbot /build/config.yaml /app/config.yaml
COPY --chown=rasbot:rasbot /build/pyproject.toml /app/pyproject.toml

# Переключение на непривилегированного пользователя
USER rasbot

# Переменные окружения
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Точка входа
CMD ["python", "-m", "ras_bot.main"]

