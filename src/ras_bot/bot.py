"""Telegram бот для RAS Bot - обработка команд и сообщений."""

import logging
from datetime import date, datetime, timedelta
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ras_bot.config import Config
from ras_bot.slots import get_slot_buttons, parse_callback_data
from ras_bot.stats import StatsCalculator
from ras_bot.whoop_client import WhoopClient

logger = logging.getLogger(__name__)


class RASBot:
    """Telegram бот для RAS."""

    def __init__(
        self,
        config: Config,
        storage: Any,
        llm_client: Any,
        stats_calculator: StatsCalculator,
        scheduler: Any = None,
        whoop_client: WhoopClient | None = None,
    ):
        """
        Инициализация бота.

        Args:
            config: Конфигурация приложения
            storage: Экземпляр Storage
            llm_client: Экземпляр LLMClient
            stats_calculator: Экземпляр StatsCalculator
            scheduler: Экземпляр SlotScheduler (опционально)
            whoop_client: Экземпляр WhoopClient (опционально)
        """
        self.config = config
        self.storage = storage
        self.llm_client = llm_client
        self.stats_calculator = stats_calculator
        self.scheduler = scheduler
        self.whoop_client = whoop_client

        self.bot = Bot(token=config.telegram_bot_token)
        self.dp = Dispatcher()

        # Создаем роутер для обработчиков
        self.router = Router()
        self._register_handlers()

        # Включаем роутер в диспетчер
        self.dp.include_router(self.router)

        # Middleware для логирования
        self.dp.message.middleware(self._log_message_middleware)
        self.dp.callback_query.middleware(self._log_callback_middleware)

    def _register_handlers(self) -> None:
        """Регистрация всех обработчиков."""
        # Команда /start
        self.router.message.register(self._handle_start, Command("start"))

        # Команда /stats
        self.router.message.register(self._handle_stats, Command("stats"))

        # Команда /health
        self.router.message.register(self._handle_health, Command("health"))

        # Команда /whoop_connect
        self.router.message.register(self._handle_whoop_connect, Command("whoop_connect"))

        # Команда /whoop_code для ручного ввода authorization code
        self.router.message.register(self._handle_whoop_code, Command("whoop_code"))

        # Команда /whoop_now для получения текущих показателей
        self.router.message.register(self._handle_whoop_now, Command("whoop_now"))

        # Команда /whoop_monitoring для включения/выключения мониторинга
        self.router.message.register(self._handle_whoop_monitoring, Command("whoop_monitoring"))

        # Команда /whoop_threshold для настройки порога стресса
        self.router.message.register(self._handle_whoop_threshold, Command("whoop_threshold"))

        # Команда /whoop_alerts для истории уведомлений
        self.router.message.register(self._handle_whoop_alerts, Command("whoop_alerts"))

        # Обработка callback от inline-кнопок
        self.router.callback_query.register(
            self._handle_button_callback, F.data.startswith("slot_")
        )

    async def _log_message_middleware(self, handler, event: Message, data: dict) -> Any:
        """Middleware для логирования сообщений."""
        logger.info(
            "Message received",
            extra={
                "user_id": event.from_user.id,
                "username": event.from_user.username,
                "text": event.text,
            },
        )
        return await handler(event, data)

    async def _log_callback_middleware(
        self, handler, event: CallbackQuery, data: dict
    ) -> Any:
        """Middleware для логирования callback запросов."""
        logger.info(
            "Callback received",
            extra={
                "user_id": event.from_user.id,
                "username": event.from_user.username,
                "data": event.data,
            },
        )
        return await handler(event, data)

    async def _handle_start(self, message: Message) -> None:
        """Обработчик команды /start."""
        user_id = message.from_user.id

        # Сохраняем user_id для планировщика, если он еще не установлен
        if self.scheduler and self.scheduler.user_id is None:
            self.scheduler.user_id = user_id
            logger.info(
                "User ID set for scheduler",
                extra={"user_id": user_id},
            )

        # Проверяем, есть ли параметр для WHOOP OAuth callback
        if message.text and "whoop_auth" in message.text:
            # Пытаемся извлечь code из текста сообщения (на случай если Telegram передаст)
            text = message.text or ""
            code = None
            
            # Пробуем найти code в тексте (может быть передан как часть deep link)
            if "code=" in text:
                try:
                    # Извлекаем code из строки вида "whoop_auth code=XXX" или "whoop_auth?code=XXX"
                    import re
                    match = re.search(r'code=([^&\s]+)', text)
                    if match:
                        code = match.group(1)
                except Exception:
                    pass
            
            if code:
                # Если code найден, обрабатываем сразу
                await self._handle_whoop_code_direct(message, code)
            else:
                # Иначе показываем инструкцию
                await self._handle_whoop_callback(message)
            return

        welcome_text = (
            "Привет! Я RAS Bot — твой личный метроном дня.\n\n"
            "Я буду отправлять тебе 6 мягких пингов в течение дня:\n"
            "• S1 (07:30) — Утро тела\n"
            "• S2 (09:30) — Опора 'я есть'\n"
            "• S3 (11:00) — Фокус-квант\n"
            "• S4 (14:00) — Шаг к деньгам\n"
            "• S5 (17:30) — Закат/присутствие\n"
            "• S6 (21:00) — Оценка дня\n\n"
            "Используй /stats для просмотра статистики.\n"
            "Используй /health для проверки состояния бота.\n"
        )

        # Проверяем, подключен ли WHOOP
        if self.whoop_client and self.config.whoop.is_configured:
            tokens = self.storage.get_whoop_tokens(user_id)
            if tokens:
                welcome_text += "\n✅ WHOOP подключен\n\n"
                welcome_text += "Команды WHOOP:\n"
                welcome_text += "• /whoop_now — текущие показатели\n"
                welcome_text += "• /whoop_monitoring on/off — мониторинг стресса\n"
                welcome_text += "• /whoop_threshold <value> — порог стресса\n"
                welcome_text += "• /whoop_alerts — история уведомлений\n"
            else:
                welcome_text += "\nИспользуй /whoop_connect для подключения WHOOP.\n"

        await message.answer(welcome_text)
        logger.info("Start command processed", extra={"user_id": user_id})

    async def _handle_stats(self, message: Message) -> None:
        """Обработчик команды /stats."""
        try:
            # Статистика за 7 дней
            stats_7 = self.stats_calculator.calculate_statistics(7)
            message_7 = self.stats_calculator.format_stats_message(stats_7)

            # Статистика за 30 дней
            stats_30 = self.stats_calculator.calculate_statistics(30)
            message_30 = self.stats_calculator.format_stats_message(stats_30)

            full_message = f"{message_7}\n\n---\n\n{message_30}"

            await message.answer(full_message)
            logger.info("Stats command processed", extra={"user_id": message.from_user.id})

        except Exception as e:
            logger.error("Failed to process stats command", extra={"error": str(e)})
            await message.answer("Произошла ошибка при получении статистики. Попробуйте позже.")

    async def _handle_health(self, message: Message) -> None:
        """Обработчик команды /health."""
        try:
            health_status = []

            # Проверка Telegram API
            try:
                bot_info = await self.bot.get_me()
                health_status.append(f"✅ Telegram API: OK (@{bot_info.username})")
            except Exception as e:
                health_status.append(f"❌ Telegram API: {str(e)}")

            # Проверка OpenRouter API
            try:
                openrouter_ok, error_msg = await self.llm_client.health_check()
                if openrouter_ok:
                    health_status.append("✅ OpenRouter API: OK")
                else:
                    if "data policy" in error_msg.lower() or "privacy" in error_msg.lower():
                        health_status.append(
                            "⚠️ OpenRouter API: требуется настройка приватности\n"
                            "   Настройте: https://openrouter.ai/settings/privacy\n"
                            "   (будет использован fallback)"
                        )
                    else:
                        health_status.append(
                            f"⚠️ OpenRouter API: {error_msg[:50]}...\n"
                            "   (будет использован fallback)"
                        )
            except Exception as e:
                health_status.append(f"⚠️ OpenRouter API: {str(e)} (будет использован fallback)")

            # Проверка БД
            try:
                # Простой запрос к БД
                self.storage.get_slot_statistics("S1", 1)
                health_status.append("✅ База данных: OK")
            except Exception as e:
                health_status.append(f"❌ База данных: {str(e)}")

            health_message = "🏥 Статус бота:\n\n" + "\n".join(health_status)
            await message.answer(health_message)

        except Exception as e:
            logger.error("Failed to process health command", extra={"error": str(e)})
            await message.answer("Произошла ошибка при проверке здоровья бота.")

    async def _handle_button_callback(self, callback_query: CallbackQuery) -> None:
        """Обработчик нажатий на inline-кнопки."""
        try:
            # Парсим callback_data
            parsed = parse_callback_data(callback_query.data)
            if not parsed:
                await callback_query.answer("Неверный формат данных.")
                return

            slot_id, button_choice = parsed

            # Сохраняем ответ
            self.storage.save_response(slot_id, button_choice)

            # Отвечаем пользователю
            await callback_query.answer("Спасибо! Ответ сохранён.")

            logger.info(
                "Button callback processed",
                extra={
                    "user_id": callback_query.from_user.id,
                    "slot_id": slot_id,
                    "button_choice": button_choice,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to process button callback",
                extra={"error": str(e), "data": callback_query.data},
            )
            await callback_query.answer("Произошла ошибка при сохранении ответа.")

    async def _handle_whoop_connect(self, message: Message) -> None:
        """Обработчик команды /whoop_connect."""
        user_id = message.from_user.id

        if not self.whoop_client or not self.config.whoop.is_configured:
            await message.answer(
                "WHOOP API не настроен. Пожалуйста, настройте WHOOP_CLIENT_ID и WHOOP_CLIENT_SECRET в .env файле."
            )
            return

        try:
            # Генерируем URL для авторизации
            auth_url = self.whoop_client.get_authorization_url(user_id)

            await message.answer(
                "🔗 Для подключения WHOOP:\n\n"
                f"1. Перейди по ссылке: {auth_url}\n\n"
                "2. Авторизуйся в WHOOP\n\n"
                "3. После авторизации скопируй authorization code из адресной строки браузера\n"
                "   (он будет в параметре `code=` в URL)\n\n"
                "4. Отправь команду: `/whoop_code <твой_code>`\n\n"
                "Например: `/whoop_code abc123xyz456`\n\n"
                "⚠️ **Важно:** Telegram не передает code автоматически, поэтому нужен ручной ввод."
            )
            logger.info("WHOOP connect initiated", extra={"user_id": user_id})

        except Exception as e:
            logger.error("Failed to initiate WHOOP connection", extra={"error": str(e), "user_id": user_id})
            await message.answer(f"Произошла ошибка при подключении WHOOP: {str(e)}")

    async def _handle_whoop_callback(self, message: Message) -> None:
        """Обработчик OAuth callback от WHOOP."""
        user_id = message.from_user.id

        if not self.whoop_client:
            await message.answer("WHOOP клиент не инициализирован.")
            return

        # Telegram не передает query параметры в deep link
        # Показываем инструкцию для ручного ввода code
        await message.answer(
            "🔗 После авторизации в WHOOP ты будешь перенаправлен обратно.\n\n"
            "⚠️ Telegram не передает authorization code автоматически.\n\n"
            "📋 **Что делать:**\n"
            "1. После авторизации скопируй authorization code из адресной строки браузера\n"
            "2. Отправь команду: `/whoop_code <твой_code>`\n\n"
            "Например: `/whoop_code abc123xyz456`\n\n"
            "Или попробуй подключиться заново через /whoop_connect"
        )

    async def _handle_whoop_code_direct(self, message: Message, code: str) -> None:
        """Прямая обработка authorization code (из deep link)."""
        user_id = message.from_user.id

        if not self.whoop_client or not self.config.whoop.is_configured:
            await message.answer(
                "WHOOP API не настроен. Пожалуйста, настройте WHOOP_CLIENT_ID и WHOOP_CLIENT_SECRET в .env файле."
            )
            return

        try:
            # Обмениваем code на токены
            await self.whoop_client.exchange_code_for_tokens(user_id, code)

            await message.answer(
                "✅ WHOOP успешно подключен!\n\n"
                "Теперь в вечернем слоте S6 ты будешь получать физические показатели "
                "(Recovery, Sleep, Strain, Workouts) вместе с оценкой дня.\n\n"
                "Данные будут автоматически обновляться каждый день в 22:00."
            )
            logger.info("WHOOP connected successfully via deep link", extra={"user_id": user_id})

        except Exception as e:
            logger.error("Failed to handle WHOOP code from deep link", extra={"error": str(e), "user_id": user_id})
            # Если автоматическая обработка не сработала, показываем инструкцию
            await message.answer(
                f"⚠️ Не удалось автоматически обработать authorization code.\n\n"
                f"Попробуй вручную:\n"
                f"1. Скопируй code из URL браузера\n"
                f"2. Отправь команду: `/whoop_code <твой_code>`\n\n"
                f"Code из URL: `{code[:50]}...`"
            )

    async def _handle_whoop_code(self, message: Message) -> None:
        """Обработчик команды /whoop_code для ручного ввода authorization code."""
        user_id = message.from_user.id

        if not self.whoop_client or not self.config.whoop.is_configured:
            await message.answer(
                "WHOOP API не настроен. Пожалуйста, настройте WHOOP_CLIENT_ID и WHOOP_CLIENT_SECRET в .env файле."
            )
            return

        try:
            # Извлекаем code из команды: /whoop_code <code>
            text = message.text or ""
            parts = text.split(maxsplit=1)
            
            if len(parts) < 2:
                await message.answer(
                    "❌ Не указан authorization code.\n\n"
                    "Использование: `/whoop_code <твой_code>`\n\n"
                    "Например: `/whoop_code abc123xyz456`\n\n"
                    "Получить code можно через /whoop_connect"
                )
                return

            code = parts[1].strip()
            
            # Очищаем code от возможных лишних параметров (если пользователь скопировал весь URL)
            # Удаляем все после первого & или пробела
            code = code.split("&")[0].split("?")[0].split()[0].strip()

            if not code:
                await message.answer("❌ Authorization code не может быть пустым.")
                return

            # Обмениваем code на токены
            await self.whoop_client.exchange_code_for_tokens(user_id, code)

            await message.answer(
                "✅ WHOOP успешно подключен!\n\n"
                "Теперь в вечернем слоте S6 ты будешь получать физические показатели "
                "(Recovery, Sleep, Strain, Workouts) вместе с оценкой дня.\n\n"
                "Данные будут автоматически обновляться каждый день в 22:00."
            )
            logger.info("WHOOP connected successfully via manual code", extra={"user_id": user_id})

        except Exception as e:
            logger.error("Failed to handle WHOOP code", extra={"error": str(e), "user_id": user_id})
            error_msg = str(e)
            if "Failed to exchange code" in error_msg or "401" in error_msg or "400" in error_msg:
                await message.answer(
                    f"❌ Не удалось подключить WHOOP: {error_msg}\n\n"
                    "Возможные причины:\n"
                    "• Authorization code уже использован или истек\n"
                    "• Неверный code\n\n"
                    "Попробуй подключиться заново через /whoop_connect"
                )
            else:
                await message.answer(
                    f"❌ Произошла ошибка при подключении WHOOP: {error_msg}\n\n"
                    "Попробуй подключиться заново через /whoop_connect"
                )

    async def _handle_whoop_now(self, message: Message) -> None:
        """Обработчик команды /whoop_now для получения текущих показателей WHOOP."""
        user_id = message.from_user.id

        if not self.whoop_client or not self.config.whoop.is_configured:
            await message.answer(
                "WHOOP не подключен. Используй /whoop_connect для подключения."
            )
            return

        try:
            # Получаем текущие данные за сегодня
            today = date.today()
            whoop_data = await self.whoop_client.get_all_data(user_id, today)

            # Формируем сообщение
            parts = []
            parts.append("📊 Текущие показатели WHOOP:\n")

            # Recovery (если доступен за сегодня)
            recovery_score = whoop_data.get("recovery_score")
            if recovery_score is not None:
                # Пробуем получить детальные данные для HRV и RHR
                # Сначала из raw_data (если есть), потом через API
                hrv = None
                rhr = None
                recovery_data = None
                
                # Проверяем raw_data из get_all_data
                raw_data = whoop_data.get("raw_data", {})
                recovery_raw = raw_data.get("recovery")
                if recovery_raw:
                    score = recovery_raw.get("score", {})
                    hrv = score.get("hrv_rmssd_milli") or score.get("hrv_rmssd") or score.get("hrv")
                    rhr = score.get("resting_heart_rate") or score.get("resting_hr")
                
                # Если не нашли в raw_data, пробуем через API
                if hrv is None or rhr is None:
                    recovery_data = await self.whoop_client.get_recovery(user_id, today)
                    if recovery_data:
                        score = recovery_data.get("score", {})
                        recovery_score = score.get("recovery_score") or recovery_score
                        if hrv is None:
                            hrv = score.get("hrv_rmssd_milli") or score.get("hrv_rmssd") or score.get("hrv")
                        if rhr is None:
                            rhr = score.get("resting_heart_rate") or score.get("resting_hr")

                # Эмодзи в зависимости от уровня Recovery
                if recovery_score >= 67:
                    recovery_emoji = "🟢"
                elif recovery_score >= 34:
                    recovery_emoji = "🟡"
                else:
                    recovery_emoji = "🔴"

                recovery_line = f"{recovery_emoji} Recovery: {recovery_score:.0f}%"
                # HRV может быть в миллисекундах (hrv_rmssd_milli) или уже в миллисекундах
                if hrv is not None and hrv > 0:
                    # Если значение больше 1000, значит это микросекунды, делим на 1000
                    # Если меньше 1000, значит уже в миллисекундах
                    if hrv > 1000:
                        hrv_display = hrv / 1000
                    else:
                        hrv_display = hrv
                    recovery_line += f" | HRV: {hrv_display:.0f}ms"
                if rhr is not None:
                    recovery_line += f" | RHR: {rhr:.0f} bpm"
                parts.append(recovery_line)

            # Sleep (если доступен за сегодня)
            sleep_duration = whoop_data.get("sleep_duration")
            if sleep_duration is not None:
                # Эмодзи в зависимости от продолжительности сна
                if sleep_duration >= 7:
                    sleep_emoji = "😴"
                elif sleep_duration >= 6:
                    sleep_emoji = "😌"
                else:
                    sleep_emoji = "😴"
                parts.append(f"{sleep_emoji} Sleep: {sleep_duration:.1f}ч (сегодня)")
            else:
                # Пробуем получить за вчера
                yesterday = date.today() - timedelta(days=1)
                sleep_data = await self.whoop_client.get_sleep(user_id, yesterday)
                if sleep_data:
                    stage_summary = sleep_data.get("score", {}).get("stage_summary", {})
                    sleep_duration_ms = stage_summary.get("total_in_bed_time_milli", 0)
                    if sleep_duration_ms:
                        sleep_hours = sleep_duration_ms / (1000 * 60 * 60)
                        if sleep_hours >= 7:
                            sleep_emoji = "😴"
                        elif sleep_hours >= 6:
                            sleep_emoji = "😌"
                        else:
                            sleep_emoji = "😴"
                        parts.append(f"{sleep_emoji} Sleep: {sleep_hours:.1f}ч (вчера)")

            # Strain (текущий за сегодня)
            strain_score = whoop_data.get("strain_score")
            if strain_score is not None:
                # Эмодзи в зависимости от уровня Strain
                if strain_score >= 18:
                    strain_emoji = "🔥"
                elif strain_score >= 14:
                    strain_emoji = "⚡"
                elif strain_score >= 10:
                    strain_emoji = "💪"
                else:
                    strain_emoji = "😊"
                parts.append(f"{strain_emoji} Strain: {strain_score:.1f} (сегодня)")

            # Workouts
            workouts_count = whoop_data.get("workouts_count", 0)
            if workouts_count > 0:
                parts.append(f"🏋️ Workouts: {workouts_count}")
            else:
                parts.append("🏋️ Workouts: 0")

            # Время обновления
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M")
            parts.append(f"\n⏰ Обновлено: {current_time}")

            message_text = "\n".join(parts)
            await message.answer(message_text)

            logger.info("WHOOP now command processed", extra={"user_id": user_id})

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to get WHOOP current data", extra={"error": error_msg, "user_id": user_id})
            
            # Проверяем, является ли ошибка проблемой с токеном
            if "401" in error_msg or "Authorization" in error_msg or "token" in error_msg.lower():
                await message.answer(
                    "❌ Токен WHOOP истек или недействителен.\n\n"
                    "Необходимо переподключить WHOOP:\n"
                    "1. Отправь команду /whoop_connect\n"
                    "2. Перейди по ссылке и авторизуйся\n"
                    "3. Скопируй authorization code со страницы\n"
                    "4. Отправь команду /whoop_code <твой_код>"
                )
            else:
                await message.answer(
                    f"❌ Не удалось получить данные WHOOP: {error_msg}\n\n"
                    "Проверь подключение через /whoop_connect"
                )

    async def _handle_whoop_monitoring(self, message: Message) -> None:
        """Обработчик команды /whoop_monitoring on/off."""
        user_id = message.from_user.id
        text = (message.text or "").strip().lower()

        if not self.whoop_client or not self.config.whoop.is_configured:
            await message.answer(
                "WHOOP не подключен. Используй /whoop_connect для подключения."
            )
            return

        try:
            # Парсим команду: /whoop_monitoring on или /whoop_monitoring off
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                # Показываем текущий статус
                settings = self.storage.get_user_settings(user_id)
                status = "включен" if settings["monitoring_enabled"] else "выключен"
                await message.answer(
                    f"📊 Мониторинг стресса: {status}\n\n"
                    "Использование:\n"
                    "• `/whoop_monitoring on` — включить мониторинг\n"
                    "• `/whoop_monitoring off` — выключить мониторинг"
                )
                return

            action = parts[1].strip().lower()

            if action == "on":
                self.storage.update_user_settings(user_id, monitoring_enabled=True)
                await message.answer(
                    "✅ Автоматический мониторинг стресса включен.\n\n"
                    "Бот будет проверять уровень стресса каждые 30 минут с 8:00 до 00:00 "
                    "и отправлять уведомления при высоком стрессе."
                )
                logger.info("WHOOP monitoring enabled", extra={"user_id": user_id})
            elif action == "off":
                self.storage.update_user_settings(user_id, monitoring_enabled=False)
                await message.answer(
                    "⏸ Автоматический мониторинг стресса выключен.\n\n"
                    "Ты все еще можешь получать данные через /whoop_now"
                )
                logger.info("WHOOP monitoring disabled", extra={"user_id": user_id})
            else:
                await message.answer(
                    "❌ Неверная команда. Используй:\n"
                    "• `/whoop_monitoring on` — включить\n"
                    "• `/whoop_monitoring off` — выключить"
                )

        except Exception as e:
            logger.error("Failed to handle whoop_monitoring", extra={"error": str(e), "user_id": user_id})
            await message.answer(f"❌ Произошла ошибка: {str(e)}")

    async def _handle_whoop_threshold(self, message: Message) -> None:
        """Обработчик команды /whoop_threshold <value>."""
        user_id = message.from_user.id
        text = (message.text or "").strip()

        if not self.whoop_client or not self.config.whoop.is_configured:
            await message.answer(
                "WHOOP не подключен. Используй /whoop_connect для подключения."
            )
            return

        try:
            # Парсим команду: /whoop_threshold 12.5
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                # Показываем текущий порог
                settings = self.storage.get_user_settings(user_id)
                threshold = settings["stress_threshold"]
                await message.answer(
                    f"📊 Текущий порог стресса: {threshold:.1f}\n\n"
                    "Использование: `/whoop_threshold <значение>`\n"
                    "Например: `/whoop_threshold 12.5`\n\n"
                    "Диапазон: 0-21 (где 21 — максимальный Strain)"
                )
                return

            try:
                threshold_value = float(parts[1].strip())
            except ValueError:
                await message.answer(
                    "❌ Неверное значение. Укажи число от 0 до 21.\n"
                    "Например: `/whoop_threshold 12.5`"
                )
                return

            # Валидация диапазона
            if threshold_value < 0 or threshold_value > 21:
                await message.answer(
                    "❌ Значение должно быть от 0 до 21.\n"
                    "Например: `/whoop_threshold 12.5`"
                )
                return

            # Сохраняем порог
            self.storage.update_user_settings(user_id, stress_threshold=threshold_value)
            await message.answer(
                f"✅ Порог стресса установлен: {threshold_value:.1f}\n\n"
                "Уведомления будут приходить, когда Strain достигнет или превысит это значение."
            )
            logger.info("WHOOP threshold updated", extra={"user_id": user_id, "threshold": threshold_value})

        except Exception as e:
            logger.error("Failed to handle whoop_threshold", extra={"error": str(e), "user_id": user_id})
            await message.answer(f"❌ Произошла ошибка: {str(e)}")

    async def _handle_whoop_alerts(self, message: Message) -> None:
        """Обработчик команды /whoop_alerts для истории уведомлений."""
        user_id = message.from_user.id

        if not self.whoop_client or not self.config.whoop.is_configured:
            await message.answer(
                "WHOOP не подключен. Используй /whoop_connect для подключения."
            )
            return

        try:
            history = self.storage.get_notification_history(user_id, limit=20)

            if not history:
                await message.answer(
                    "📋 История уведомлений пуста.\n\n"
                    "Уведомления о высоком стрессе будут появляться здесь после их отправки."
                )
                return

            # Формируем сообщение с историей
            parts = ["📋 История уведомлений о стрессе:\n"]

            for i, alert in enumerate(history[:10], 1):  # Показываем последние 10
                sent_at = datetime.fromisoformat(alert["sent_at"])
                time_str = sent_at.strftime("%d.%m %H:%M")
                strain = alert.get("strain_score")
                recovery = alert.get("recovery_score")

                alert_line = f"{i}. {time_str} | Strain: {strain:.1f}" if strain else f"{i}. {time_str}"
                if recovery is not None:
                    alert_line += f" | Recovery: {recovery:.0f}%"
                parts.append(alert_line)

            if len(history) > 10:
                parts.append(f"\n... и еще {len(history) - 10} уведомлений")

            message_text = "\n".join(parts)
            await message.answer(message_text)

            logger.info("WHOOP alerts command processed", extra={"user_id": user_id, "count": len(history)})

        except Exception as e:
            logger.error("Failed to get WHOOP alerts", extra={"error": str(e), "user_id": user_id})
            await message.answer(f"❌ Произошла ошибка при получении истории: {str(e)}")

    async def send_slot_message(self, slot_id: str, user_id: int) -> None:
        """
        Отправка сообщения слота пользователю.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            user_id: ID пользователя Telegram
        """
        try:
            # Получаем контекст для генерации сообщения
            context = await self.stats_calculator.get_context_for_slot(slot_id, user_id)

            # Для S6 отправляем отдельный блок с WHOOP данными перед основным сообщением
            if slot_id == "S6" and self.whoop_client:
                # Сначала пробуем получить из БД
                whoop_data = self.storage.get_today_whoop_data()
                
                # Если данных нет в БД, пробуем получить через API
                if not whoop_data:
                    try:
                        today = date.today()
                        whoop_data_dict = await self.whoop_client.get_all_data(user_id, today)
                        if whoop_data_dict:
                            whoop_data = {
                                "recovery_score": whoop_data_dict.get("recovery_score"),
                                "sleep_duration": whoop_data_dict.get("sleep_duration"),
                                "strain_score": whoop_data_dict.get("strain_score"),
                                "workouts_count": whoop_data_dict.get("workouts_count", 0),
                            }
                    except Exception as e:
                        logger.warning("Failed to get WHOOP data for S6 display", extra={"error": str(e)})
                
                # Отображаем данные, если они есть
                if whoop_data and (
                    whoop_data.get("recovery_score") is not None
                    or whoop_data.get("sleep_duration") is not None
                    or whoop_data.get("strain_score") is not None
                ):
                    whoop_block = "📊 Физические показатели WHOOP:\n"
                    parts = []

                    if whoop_data.get("recovery_score") is not None:
                        parts.append(f"Recovery: {whoop_data['recovery_score']:.0f}%")
                    if whoop_data.get("sleep_duration") is not None:
                        parts.append(f"Sleep: {whoop_data['sleep_duration']:.1f}ч")
                    if whoop_data.get("strain_score") is not None:
                        parts.append(f"Strain: {whoop_data['strain_score']:.1f}")
                    if whoop_data.get("workouts_count", 0) > 0:
                        parts.append(f"Workouts: {whoop_data['workouts_count']}")

                    if parts:
                        whoop_block += " | ".join(parts)
                        await self.bot.send_message(chat_id=user_id, text=whoop_block)

            # Генерируем сообщение через LLM
            message_text = await self.llm_client.generate_slot_message(slot_id, context)

            # Получаем кнопки для слота
            keyboard = get_slot_buttons(slot_id)

            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=user_id,
                text=message_text,
                reply_markup=keyboard,
            )

            logger.info(
                "Slot message sent",
                extra={"slot_id": slot_id, "user_id": user_id},
            )

        except Exception as e:
            logger.error(
                "Failed to send slot message",
                extra={"error": str(e), "slot_id": slot_id, "user_id": user_id},
            )
            # Пытаемся отправить fallback сообщение
            try:
                slot_config = self.config.get_slot_config(slot_id)
                keyboard = get_slot_buttons(slot_id)
                await self.bot.send_message(
                    chat_id=user_id,
                    text=slot_config.fallback_message,
                    reply_markup=keyboard,
                )
            except Exception as fallback_error:
                logger.error(
                    "Failed to send fallback message",
                    extra={"error": str(fallback_error), "slot_id": slot_id},
                )

    async def start_polling(self) -> None:
        """Запуск бота в режиме polling."""
        logger.info("Starting bot polling...")
        await self.dp.start_polling(self.bot)

    async def stop(self) -> None:
        """Остановка бота."""
        logger.info("Stopping bot...")
        await self.bot.session.close()

