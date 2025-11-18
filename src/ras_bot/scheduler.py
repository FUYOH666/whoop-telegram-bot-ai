"""Планировщик задач для RAS Bot - отправка слотов по расписанию."""

import asyncio
import logging
from datetime import date, datetime, time
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class SlotScheduler:
    """Планировщик для отправки слотов по расписанию."""

    def __init__(self, bot: Any, config: Any, user_id: int | None):
        """
        Инициализация планировщика.

        Args:
            bot: Экземпляр RASBot
            config: Конфигурация приложения
            user_id: ID пользователя Telegram для отправки сообщений (может быть None)
        """
        self.bot = bot
        self.config = config
        self.user_id = user_id
        self.scheduler = AsyncIOScheduler()

    def setup_scheduler(self) -> None:
        """Настройка расписания для всех слотов."""
        slots_config = self.config.slots

        for slot_id, slot_config in slots_config.items():
            self._schedule_slot(slot_id, slot_config.time)

        # Планируем обновление WHOOP данных в 22:00 (после S6)
        if self.config.whoop.is_configured:
            self._schedule_whoop_update()

        logger.info("Scheduler setup completed", extra={"slots_count": len(slots_config)})

    def _schedule_slot(self, slot_id: str, time_str: str) -> None:
        """
        Планирование одного слота.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            time_str: Время в формате HH:MM
        """
        try:
            # Парсим время
            hour, minute = map(int, time_str.split(":"))

            # Создаем cron trigger для ежедневного выполнения в указанное время
            trigger = CronTrigger(hour=hour, minute=minute)

            # Добавляем задачу в планировщик
            self.scheduler.add_job(
                self._send_slot_job,
                trigger=trigger,
                args=[slot_id],
                id=f"slot_{slot_id}",
                name=f"Send {slot_id}",
                replace_existing=True,
                max_instances=1,
            )

            logger.info(
                "Slot scheduled",
                extra={"slot_id": slot_id, "time": time_str},
            )

        except Exception as e:
            logger.error(
                "Failed to schedule slot",
                extra={"error": str(e), "slot_id": slot_id, "time": time_str},
            )

    async def _send_slot_job(self, slot_id: str) -> None:
        """
        Задача для отправки сообщения слота.

        Args:
            slot_id: Идентификатор слота (S1-S6)
        """
        if self.user_id is None:
            logger.warning(
                "Cannot send slot message: user_id not set",
                extra={"slot_id": slot_id},
            )
            return

        max_retries = 3
        retry_delay = 2.0

        for attempt in range(max_retries):
            try:
                await self.bot.send_slot_message(slot_id, self.user_id)
                logger.info(
                    "Slot job executed successfully",
                    extra={"slot_id": slot_id, "attempt": attempt + 1},
                )
                return

            except Exception as e:
                logger.warning(
                    "Slot job failed, retrying",
                    extra={
                        "error": str(e),
                        "slot_id": slot_id,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                    },
                )

                if attempt < max_retries - 1:
                    # Экспоненциальная задержка перед повтором
                    wait_time = retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Slot job failed after all retries",
                        extra={"slot_id": slot_id, "error": str(e)},
                    )

    def start(self) -> None:
        """Запуск планировщика."""
        try:
            self.scheduler.start()
            logger.info("Scheduler started")
        except Exception as e:
            logger.error("Failed to start scheduler", extra={"error": str(e)})
            raise

    def stop(self) -> None:
        """Остановка планировщика."""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error("Failed to stop scheduler", extra={"error": str(e)})

    def get_next_run_times(self) -> dict[str, str]:
        """
        Получение времени следующего запуска для каждого слота.

        Returns:
            Словарь {slot_id: next_run_time}
        """
        next_runs = {}
        for job in self.scheduler.get_jobs():
            if job.id.startswith("slot_"):
                slot_id = job.id.replace("slot_", "")
                next_run = job.next_run_time
                if next_run:
                    next_runs[slot_id] = next_run.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    next_runs[slot_id] = "Не запланировано"

        return next_runs

    def _schedule_whoop_update(self) -> None:
        """Планирование задачи обновления WHOOP данных."""
        try:
            # Планируем на 22:00 каждый день
            trigger = CronTrigger(hour=22, minute=0)

            self.scheduler.add_job(
                self._update_whoop_data_job,
                trigger=trigger,
                id="whoop_update",
                name="Update WHOOP data",
                replace_existing=True,
                max_instances=1,
            )

            logger.info("WHOOP update job scheduled", extra={"time": "22:00"})

        except Exception as e:
            logger.error("Failed to schedule WHOOP update", extra={"error": str(e)})

    async def _update_whoop_data_job(self) -> None:
        """
        Задача для обновления WHOOP данных за сегодня.

        Выполняется в 22:00 для получения полных данных за день.
        """
        if self.user_id is None:
            logger.warning("Cannot update WHOOP data: user_id not set")
            return

        if not self.bot or not self.bot.whoop_client:
            logger.debug("WHOOP client not available, skipping update")
            return

        try:
            whoop_client = self.bot.whoop_client
            storage = self.bot.storage

            # Получаем все данные WHOOP за сегодня
            today = date.today()
            whoop_data = await whoop_client.get_all_data(self.user_id, today)

            # Сохраняем в БД
            storage.save_whoop_data(
                target_date=today.isoformat(),
                recovery_score=whoop_data.get("recovery_score"),
                sleep_duration=whoop_data.get("sleep_duration"),
                strain_score=whoop_data.get("strain_score"),
                workouts_count=whoop_data.get("workouts_count", 0),
                raw_data=whoop_data.get("raw_data"),
            )

            logger.info(
                "WHOOP data updated successfully",
                extra={
                    "date": today.isoformat(),
                    "recovery": whoop_data.get("recovery_score"),
                    "sleep": whoop_data.get("sleep_duration"),
                    "strain": whoop_data.get("strain_score"),
                    "workouts": whoop_data.get("workouts_count", 0),
                },
            )

        except Exception as e:
            logger.error(
                "Failed to update WHOOP data",
                extra={"error": str(e), "user_id": self.user_id},
            )
            # Не блокируем работу бота при ошибке WHOOP

