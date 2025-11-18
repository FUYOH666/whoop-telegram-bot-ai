"""Telegram бот для RAS Bot - обработка команд и сообщений."""

import logging
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
            # Обрабатываем OAuth callback от WHOOP
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
                welcome_text += "✅ WHOOP подключен\n"
            else:
                welcome_text += "Используй /whoop_connect для подключения WHOOP.\n"

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
                "Для подключения WHOOP перейди по ссылке и авторизуйся:\n\n"
                f"{auth_url}\n\n"
                "После авторизации ты будешь перенаправлен обратно в бота."
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

        try:
            # Извлекаем authorization code из параметров deep link
            # Формат: /start whoop_auth?code=XXX&state=YYY
            text = message.text or ""
            code = None

            # Парсим параметры из текста сообщения
            if "code=" in text:
                parts = text.split("code=")
                if len(parts) > 1:
                    code_part = parts[1].split("&")[0].split(" ")[0]
                    code = code_part.strip()

            if not code:
                await message.answer(
                    "Не удалось получить authorization code. "
                    "Попробуй подключиться заново через /whoop_connect"
                )
                return

            # Обмениваем code на токены
            await self.whoop_client.exchange_code_for_tokens(user_id, code)

            await message.answer(
                "✅ WHOOP успешно подключен!\n\n"
                "Теперь в вечернем слоте S6 ты будешь получать физические показатели "
                "(Recovery, Sleep, Strain, Workouts) вместе с оценкой дня."
            )
            logger.info("WHOOP connected successfully", extra={"user_id": user_id})

        except Exception as e:
            logger.error("Failed to handle WHOOP callback", extra={"error": str(e), "user_id": user_id})
            await message.answer(
                f"Произошла ошибка при подключении WHOOP: {str(e)}\n\n"
                "Попробуй подключиться заново через /whoop_connect"
            )

    async def send_slot_message(self, slot_id: str, user_id: int) -> None:
        """
        Отправка сообщения слота пользователю.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            user_id: ID пользователя Telegram
        """
        try:
            # Получаем контекст для генерации сообщения
            context = self.stats_calculator.get_context_for_slot(slot_id, user_id)

            # Для S6 отправляем отдельный блок с WHOOP данными перед основным сообщением
            if slot_id == "S6" and self.whoop_client:
                whoop_data = self.storage.get_today_whoop_data()
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

