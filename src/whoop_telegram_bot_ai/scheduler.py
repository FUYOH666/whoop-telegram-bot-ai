"""Планировщик задач для RAS Bot - отправка слотов по расписанию."""

import asyncio
import logging
from datetime import date, datetime, time
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class SlotScheduler:
    """Планировщик для отправки слотов по расписанию."""

    def __init__(self, bot: Any, config: Any, user_id: int | None):
        """
        Инициализация планировщика.

        Args:
            bot: Экземпляр WhoopTelegramBotAI
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

        # Планируем мониторинг стресса WHOOP в реальном времени
        if (
            self.config.whoop.is_configured
            and hasattr(self.config, "whoop_monitoring")
            and self.config.whoop_monitoring.enabled
        ):
            self._schedule_stress_monitoring()

        # Планируем еженедельный отчет (каждое воскресенье в 20:00)
        self._schedule_weekly_report()

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
        Также проверяет и обновляет токены при необходимости.
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

            # Проверяем и обновляем токены перед запросом данных
            # Это гарантирует, что токены всегда свежие
            try:
                # _get_access_token автоматически обновит токен, если нужно
                await whoop_client._get_access_token(self.user_id)
                logger.debug("Token check completed before data update", extra={"user_id": self.user_id})
            except Exception as token_error:
                logger.warning(
                    "Token check failed, but continuing with data update",
                    extra={"error": str(token_error), "user_id": self.user_id},
                )
                # Продолжаем попытку получить данные - возможно, токен еще валиден

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

        except ValueError as e:
            # Если ошибка связана с истечением токена, отправляем уведомление пользователю
            error_msg = str(e)
            if "reconnect" in error_msg.lower() or "expired" in error_msg.lower():
                logger.warning(
                    "WHOOP token expired, notifying user",
                    extra={"user_id": self.user_id, "error": error_msg},
                )
                if self.bot and self.bot.bot:
                    try:
                        await self.bot.bot.send_message(
                            self.user_id,
                            "⚠️ Токен WHOOP истек. Необходимо переподключение:\n\n"
                            "1. Отправь команду /whoop_connect\n"
                            "2. Перейди по ссылке и авторизуйся\n"
                            "3. Скопируй authorization code со страницы\n"
                            "4. Отправь команду /whoop_code <твой_код>\n\n"
                            "После переподключения данные будут обновляться автоматически."
                        )
                    except Exception as send_error:
                        logger.error(
                            "Failed to send reconnection notification",
                            extra={"user_id": self.user_id, "error": str(send_error)},
                        )
            raise
        except Exception as e:
            logger.error(
                "Failed to update WHOOP data",
                extra={"error": str(e), "user_id": self.user_id},
            )
            # Не блокируем работу бота при ошибке WHOOP

    def _schedule_stress_monitoring(self) -> None:
        """Планирование периодической проверки уровня стресса."""
        try:
            monitoring_config = self.config.whoop_monitoring
            interval_minutes = monitoring_config.check_interval_minutes

            # Используем IntervalTrigger для периодической проверки
            trigger = IntervalTrigger(minutes=interval_minutes)

            self.scheduler.add_job(
                self._check_stress_job,
                trigger=trigger,
                id="whoop_stress_monitoring",
                name="WHOOP Stress Monitoring",
                replace_existing=True,
                max_instances=1,
            )

            logger.info(
                "Stress monitoring scheduled",
                extra={
                    "interval_minutes": interval_minutes,
                    "start_time": monitoring_config.start_time,
                    "end_time": monitoring_config.end_time,
                },
            )

        except Exception as e:
            logger.error("Failed to schedule stress monitoring", extra={"error": str(e)})

    async def _check_stress_job(self) -> None:
        """
        Задача для проверки уровня стресса и отправки уведомлений.

        Проверяет текущий Strain и отправляет уведомление, если он превышает порог.
        Учитывает активные часы и cooldown между уведомлениями.
        """
        if self.user_id is None:
            logger.warning("Cannot check stress: user_id not set")
            return

        try:
            monitoring_config = self.config.whoop_monitoring
            storage = self.bot.storage
            whoop_client = self.bot.whoop_client
            llm_client = self.bot.llm_client

            # Проверяем, включен ли мониторинг для пользователя
            user_settings = storage.get_user_settings(self.user_id)
            if not user_settings.get("monitoring_enabled", True):
                logger.debug("Stress monitoring disabled for user", extra={"user_id": self.user_id})
                return

            # Проверяем активные часы
            current_time = datetime.now().time()
            start_time = datetime.strptime(monitoring_config.start_time, "%H:%M").time()
            end_time = datetime.strptime(monitoring_config.end_time, "%H:%M").time()

            # Если end_time = 00:00, это означает "до полуночи", т.е. до 23:59:59
            if end_time == time(0, 0):
                end_time = time(23, 59, 59)

            if not (start_time <= current_time <= end_time):
                logger.debug(
                    "Outside active hours for stress monitoring",
                    extra={"current_time": current_time.strftime("%H:%M"), "user_id": self.user_id},
                )
                return

            # Проверяем cooldown
            last_notification = storage.get_last_notification(
                self.user_id, "high_strain", monitoring_config.notification_cooldown_hours
            )
            if last_notification:
                logger.debug(
                    "Cooldown active, skipping stress check",
                    extra={"user_id": self.user_id},
                )
                return

            # Получаем текущие данные WHOOP
            today = date.today()
            try:
                # Проверяем и обновляем токены перед запросом
                await whoop_client._get_access_token(self.user_id)

                # Получаем данные через cycle endpoint (самый полный источник)
                cycle_data = await whoop_client.get_cycle(self.user_id, today)
                if not cycle_data:
                    logger.debug("No cycle data available for stress check", extra={"user_id": self.user_id})
                    return

                # Извлекаем Strain из cycle данных
                strain_score = None
                if "score" in cycle_data and "strain" in cycle_data["score"]:
                    strain_score = cycle_data["score"]["strain"].get("average")

                if strain_score is None:
                    logger.debug("Strain score not available", extra={"user_id": self.user_id})
                    return

                # Получаем порог из настроек пользователя или используем значение по умолчанию
                threshold = user_settings.get("stress_threshold", monitoring_config.stress_threshold)

                # Проверяем, превышает ли Strain порог
                if strain_score < threshold:
                    logger.debug(
                        "Strain below threshold",
                        extra={"strain": strain_score, "threshold": threshold, "user_id": self.user_id},
                    )
                    return

                # Получаем Recovery для более умного уведомления
                recovery_score = None
                try:
                    recovery_data = await whoop_client.get_recovery(self.user_id, today)
                    if recovery_data and "score" in recovery_data:
                        score = recovery_data["score"]
                        recovery_score = score.get("recovery_score") or score.get("recovery_percentage")
                except Exception as e:
                    logger.warning("Failed to get recovery for stress notification", extra={"error": str(e)})

                # Генерируем совет через LLM
                current_time_str = datetime.now().strftime("%H:%M")
                advice_text = await llm_client.generate_stress_advice(
                    strain_score=strain_score,
                    recovery_score=recovery_score,
                    current_time=current_time_str,
                )

                # Отправляем уведомление пользователю
                notification_message = f"⚠️ Высокий уровень стресса\n\n"
                notification_message += f"Strain: {strain_score:.1f}"
                if recovery_score is not None:
                    notification_message += f" | Recovery: {recovery_score:.0f}%"
                notification_message += f"\n\n{advice_text}"

                await self.bot.bot.send_message(chat_id=self.user_id, text=notification_message)

                # Сохраняем уведомление в БД
                storage.save_notification(
                    user_id=self.user_id,
                    notification_type="high_strain",
                    strain_score=strain_score,
                    recovery_score=recovery_score,
                    advice_text=advice_text,
                )

                logger.info(
                    "Stress notification sent",
                    extra={
                        "user_id": self.user_id,
                        "strain": strain_score,
                        "recovery": recovery_score,
                        "threshold": threshold,
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to check stress or send notification",
                    extra={"error": str(e), "user_id": self.user_id},
                )
                # Не блокируем работу бота при ошибках WHOOP API

        except Exception as e:
            logger.error("Failed to execute stress check job", extra={"error": str(e)})

    def _schedule_weekly_report(self) -> None:
        """Планирование задачи отправки еженедельного отчета."""
        try:
            # Планируем на воскресенье в 20:00
            trigger = CronTrigger(day_of_week="sun", hour=20, minute=0)

            self.scheduler.add_job(
                self._send_weekly_report_job,
                trigger=trigger,
                id="weekly_report",
                name="Send Weekly Report",
                replace_existing=True,
                max_instances=1,
            )

            logger.info("Weekly report job scheduled", extra={"time": "Sunday 20:00"})

        except Exception as e:
            logger.error("Failed to schedule weekly report", extra={"error": str(e)})

    async def _send_weekly_report_job(self) -> None:
        """
        Задача для отправки еженедельного отчета.

        Выполняется каждое воскресенье в 20:00.
        """
        if self.user_id is None:
            logger.warning("Cannot send weekly report: user_id not set")
            return

        if not self.bot:
            logger.warning("Bot not available for weekly report")
            return

        try:
            # Проверяем наличие модулей аналитики
            analytics_module = self.bot._get_analytics_module()
            if not analytics_module:
                logger.info("No export data available for weekly report")
                # Можно отправить сообщение пользователю, что данных нет
                if self.bot and self.bot.bot:
                    await self.bot.bot.send_message(
                        self.user_id,
                        "📊 Еженедельный отчет недоступен: экспортированные данные WHOOP не найдены.\n\n"
                        "Для получения еженедельных отчетов экспортируйте данные из WHOOP приложения "
                        "и поместите CSV файлы в папку my_whoop_data_YYYY_MM_DD/ в корне проекта."
                    )
                return

            analytics, report_generator = analytics_module

            # Генерируем отчет
            report = await report_generator.generate_weekly_report()

            # Отправляем отчет пользователю
            # Разбиваем длинное сообщение на части
            max_length = 4000
            if len(report) > max_length:
                parts = [report[i : i + max_length] for i in range(0, len(report), max_length)]
                for i, part in enumerate(parts, 1):
                    if i == 1:
                        await self.bot.bot.send_message(
                            self.user_id,
                            f"📊 **Еженедельный отчет** (часть {i}/{len(parts)}):\n\n{part}"
                        )
                    else:
                        await self.bot.bot.send_message(
                            self.user_id,
                            f"(продолжение {i}/{len(parts)})\n\n{part}"
                        )
            else:
                await self.bot.bot.send_message(
                    self.user_id,
                    f"📊 **Еженедельный отчет:**\n\n{report}"
                )

            logger.info("Weekly report sent successfully", extra={"user_id": self.user_id})

        except Exception as e:
            logger.error(
                "Failed to send weekly report",
                extra={"error": str(e), "user_id": self.user_id},
            )
            # Пытаемся отправить сообщение об ошибке
            if self.bot and self.bot.bot:
                try:
                    await self.bot.bot.send_message(
                        self.user_id,
                        f"❌ Произошла ошибка при генерации еженедельного отчета: {str(e)}"
                    )
                except Exception:
                    pass

