"""Точка входа Whoop Telegram Bot AI - инициализация и запуск всех компонентов."""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

from whoop_telegram_bot_ai.bot import WhoopTelegramBotAI
from whoop_telegram_bot_ai.config import Config
from whoop_telegram_bot_ai.llm_client import LLMClient
from whoop_telegram_bot_ai.scheduler import SlotScheduler
from whoop_telegram_bot_ai.stats import StatsCalculator
from whoop_telegram_bot_ai.storage import Storage
from whoop_telegram_bot_ai.whoop_client import WhoopClient


def setup_logging(config: Config) -> None:
    """
    Настройка структурного логирования.

    Args:
        config: Конфигурация приложения
    """
    log_level = getattr(logging, config.logging_config.level, logging.INFO)

    if config.logging_config.format == "json":
        # JSON формат для структурированного логирования
        handler = logging.StreamHandler(sys.stdout)

        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "time": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "service": "whoop_telegram_bot_ai",
                    "message": record.getMessage(),
                }
                # Добавляем дополнительные поля из extra
                if hasattr(record, "extra"):
                    log_data.update(record.extra)
                else:
                    # Извлекаем поля из record.__dict__
                    for key, value in record.__dict__.items():
                        if key not in [
                            "name",
                            "msg",
                            "args",
                            "created",
                            "filename",
                            "funcName",
                            "levelname",
                            "levelno",
                            "lineno",
                            "module",
                            "msecs",
                            "message",
                            "pathname",
                            "process",
                            "processName",
                            "relativeCreated",
                            "thread",
                            "threadName",
                            "exc_info",
                            "exc_text",
                            "stack_info",
                        ]:
                            log_data[key] = value

                return json.dumps(log_data, ensure_ascii=False)

        handler.setFormatter(JSONFormatter())
    else:
        # Текстовый формат
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s · %(levelname)s · %(name)s · %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=[handler],
    )

    logger = logging.getLogger(__name__)
    logger.info("Logging configured", extra={"level": log_level, "format": config.logging_config.format})


async def main() -> None:
    """Главная функция запуска бота."""
    logger = logging.getLogger(__name__)

    try:
        # Загрузка конфигурации
        logger.info("Loading configuration...")
        config = Config()
        config.validate()

        # Настройка логирования
        setup_logging(config)

        logger.info("Configuration loaded and validated")

        # Инициализация компонентов
        logger.info("Initializing components...")

        # Хранилище
        storage = Storage(db_path=config.database.path)

        # LLM клиент
        llm_client = LLMClient(config)

        # WHOOP клиент (опционально, если настроен)
        whoop_client = None
        if config.whoop.is_configured:
            whoop_client = WhoopClient(config.whoop, storage)
            logger.info("WHOOP client initialized")
        else:
            logger.info("WHOOP client not initialized (not configured)")

        # Калькулятор статистики
        stats_calculator = StatsCalculator(storage, whoop_client)

        # Планировщик
        # Получаем user_id из переменной окружения или используем None
        # Бот будет получать user_id из первого сообщения /start
        import os
        user_id = os.getenv("TELEGRAM_USER_ID")
        if user_id:
            user_id = int(user_id)
        else:
            logger.warning(
                "TELEGRAM_USER_ID not set. Bot will store user_id from first /start command. "
                "Set TELEGRAM_USER_ID in .env for immediate scheduling."
            )
            user_id = None  # Будет установлен при первом /start

        scheduler = SlotScheduler(bot=None, config=config, user_id=user_id)
        scheduler.setup_scheduler()

        # Telegram бот (передаем scheduler для установки user_id)
        bot = WhoopTelegramBotAI(config, storage, llm_client, stats_calculator, scheduler, whoop_client)
        
        # Устанавливаем бот в планировщик
        scheduler.bot = bot

        logger.info("All components initialized")

        # Обработка сигналов для graceful shutdown
        shutdown_event = asyncio.Event()

        def signal_handler(signum, frame):
            logger.info("Shutdown signal received", extra={"signal": signum})
            shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Запуск планировщика
        scheduler.start()
        logger.info("Scheduler started")

        # Запуск бота
        logger.info("Starting bot...")
        logger.warning(
            "IMPORTANT: Bot will only send messages to users who have started it with /start. "
            "Make sure to start the bot first!"
        )

        # Запускаем бота в фоне
        bot_task = asyncio.create_task(bot.start_polling())

        # Ждем сигнала завершения
        await shutdown_event.wait()

        # Graceful shutdown
        logger.info("Shutting down...")

        # Останавливаем планировщик
        scheduler.stop()

        # Останавливаем бота
        await bot.stop()

        # Закрываем LLM клиент
        await llm_client.close()

        # Закрываем WHOOP клиент
        if whoop_client:
            await whoop_client.close()

        logger.info("Shutdown complete")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Fatal error", extra={"error": str(e)}, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

