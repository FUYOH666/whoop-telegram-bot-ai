"""Клиент для интеграции с OpenRouter API."""

import asyncio
import logging
from typing import Any

import httpx

from ras_bot.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """Клиент для работы с OpenRouter API."""

    def __init__(self, config: Config):
        """
        Инициализация клиента.

        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.openrouter_config = config.openrouter
        self.system_prompt = config.system_prompt
        self.client = httpx.AsyncClient(
            timeout=self.openrouter_config.timeout,
            headers={
                "Authorization": f"Bearer {self.openrouter_config.api_key}",
                "HTTP-Referer": "https://github.com/ras-bot",
                "X-Title": "RAS Bot",
            },
        )

    async def generate_slot_message(
        self, slot_id: str, context: dict[str, Any]
    ) -> str:
        """
        Генерация персонализированного сообщения для слота.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            context: Контекст для генерации (статистика, история и т.д.)

        Returns:
            Сгенерированное сообщение или fallback сообщение при ошибке
        """
        try:
            slot_config = self.config.get_slot_config(slot_id)
            user_prompt = self._build_user_prompt(slot_config, context)

            message = await self._call_openrouter(user_prompt, max_tokens=slot_config.max_tokens)

            if message:
                logger.info(
                    "Message generated successfully",
                    extra={"slot_id": slot_id, "length": len(message)},
                )
                return message
            else:
                logger.warning(
                    "Empty response from OpenRouter, using fallback",
                    extra={"slot_id": slot_id},
                )
                return slot_config.fallback_message

        except Exception as e:
            logger.error(
                "Failed to generate message, using fallback",
                extra={"slot_id": slot_id, "error": str(e)},
            )
            try:
                slot_config = self.config.get_slot_config(slot_id)
                return slot_config.fallback_message
            except Exception:
                return "Привет. Время для следующего шага в твоём эталонном дне."

    def _build_user_prompt(self, slot_config: Any, context: dict[str, Any]) -> str:
        """
        Построение user-промпта для слота.

        Args:
            slot_config: Конфигурация слота
            context: Контекст (статистика, история)

        Returns:
            Сформированный user-промпт
        """
        template = slot_config.user_prompt_template

        # Заменяем плейсхолдеры в шаблоне
        prompt = template

        # Заменяем стандартные плейсхолдеры
        yesterday_status = context.get("yesterday_status", "неизвестно")
        if yesterday_status:
            if isinstance(yesterday_status, bool):
                yesterday_status = "выполнен" if yesterday_status else "пропущен"
            prompt = prompt.replace("{{yesterday_status}}", yesterday_status)

        last_7_days_count = context.get("last_7_days_count", 0)
        prompt = prompt.replace("{{last_7_days_count}}", str(last_7_days_count))

        # Заменяем WHOOP плейсхолдеры для S1-S5
        if slot_config.slot_id == "S1":
            # S1: Recovery вчера
            whoop_recovery_yesterday = context.get("whoop_recovery_yesterday")
            if whoop_recovery_yesterday is not None:
                prompt = prompt.replace("{{whoop_recovery_yesterday}}", f"{whoop_recovery_yesterday:.0f}%")
            else:
                prompt = prompt.replace("{{whoop_recovery_yesterday}}", "недоступно")
        elif slot_config.slot_id == "S2":
            # S2: Sleep вчера
            whoop_sleep_yesterday = context.get("whoop_sleep_yesterday")
            if whoop_sleep_yesterday is not None:
                prompt = prompt.replace("{{whoop_sleep_yesterday}}", f"{whoop_sleep_yesterday:.1f}ч")
            else:
                prompt = prompt.replace("{{whoop_sleep_yesterday}}", "недоступно")
        elif slot_config.slot_id in ["S3", "S4", "S5"]:
            # S3-S5: Strain сегодня
            whoop_strain_today = context.get("whoop_strain_today")
            if whoop_strain_today is not None:
                prompt = prompt.replace("{{whoop_strain_today}}", f"{whoop_strain_today:.1f}")
            else:
                prompt = prompt.replace("{{whoop_strain_today}}", "недоступно")

        # Для S6 заменяем статусы всех слотов и WHOOP данные
        if slot_config.slot_id == "S6":
            for i in range(1, 6):
                slot_status = context.get(f"s{i}_status", "неизвестно")
                if isinstance(slot_status, bool):
                    slot_status = "да" if slot_status else "нет"
                prompt = prompt.replace(f"{{{{s{i}_status}}}}", slot_status)

            # Заменяем WHOOP данные
            whoop_recovery = context.get("whoop_recovery")
            if whoop_recovery is not None:
                prompt = prompt.replace("{{whoop_recovery}}", f"{whoop_recovery:.0f}%")
            else:
                prompt = prompt.replace("{{whoop_recovery}}", "недоступно")

            whoop_sleep = context.get("whoop_sleep")
            if whoop_sleep is not None:
                prompt = prompt.replace("{{whoop_sleep}}", f"{whoop_sleep:.1f}ч")
            else:
                prompt = prompt.replace("{{whoop_sleep}}", "недоступно")

            whoop_strain = context.get("whoop_strain")
            if whoop_strain is not None:
                prompt = prompt.replace("{{whoop_strain}}", f"{whoop_strain:.1f}")
            else:
                prompt = prompt.replace("{{whoop_strain}}", "недоступно")

            whoop_workouts = context.get("whoop_workouts", 0)
            prompt = prompt.replace("{{whoop_workouts}}", str(whoop_workouts))

        return prompt

    async def _call_openrouter(self, user_prompt: str, max_retries: int = 3, max_tokens: int | None = None) -> str:
        """
        Вызов OpenRouter API с retry логикой.

        Args:
            user_prompt: User-промпт для отправки
            max_retries: Максимальное количество попыток
            max_tokens: Максимальное количество токенов (если не указано, используется значение из конфигурации)

        Returns:
            Сгенерированное сообщение или пустая строка при ошибке
        """
        if max_tokens is None:
            max_tokens = self.openrouter_config.max_tokens

        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.openrouter_config.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": self.openrouter_config.temperature,
                    "max_tokens": max_tokens,
                }

                response = await self.client.post(
                    self.openrouter_config.api_url,
                    json=payload,
                )

                response.raise_for_status()
                data = response.json()

                # Извлекаем сообщение из ответа
                if "choices" in data and len(data["choices"]) > 0:
                    message = data["choices"][0]["message"]["content"].strip()
                    return message
                else:
                    logger.warning(
                        "Unexpected response format from OpenRouter",
                        extra={"response": data},
                    )
                    return ""

            except httpx.TimeoutException:
                wait_time = 2 ** attempt
                logger.warning(
                    "OpenRouter timeout, retrying",
                    extra={"attempt": attempt + 1, "wait_time": wait_time},
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("OpenRouter timeout after all retries")
                    return ""

            except httpx.HTTPStatusError as e:
                logger.error(
                    "OpenRouter HTTP error",
                    extra={
                        "status_code": e.response.status_code,
                        "attempt": attempt + 1,
                    },
                )
                if attempt < max_retries - 1 and e.response.status_code >= 500:
                    # Retry только для серверных ошибок
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    return ""

            except Exception as e:
                logger.error(
                    "Unexpected error calling OpenRouter",
                    extra={"error": str(e), "attempt": attempt + 1},
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    return ""

        return ""

    async def generate_stress_advice(
        self,
        strain_score: float,
        recovery_score: float | None = None,
        current_time: str | None = None,
    ) -> str:
        """
        Генерация совета по снижению стресса на основе текущих показателей WHOOP.

        Args:
            strain_score: Текущий уровень Strain
            recovery_score: Уровень Recovery (опционально)
            current_time: Текущее время в формате HH:MM (опционально)

        Returns:
            Сгенерированный совет или fallback сообщение при ошибке
        """
        try:
            from datetime import datetime

            if current_time is None:
                current_time = datetime.now().strftime("%H:%M")

            if recovery_score is None:
                recovery_score = 0  # По умолчанию, если Recovery недоступен

            # Получаем промпт из конфигурации
            prompt_template = self.config.whoop_monitoring.stress_advice_prompt

            # Заменяем плейсхолдеры
            user_prompt = prompt_template.replace("{{strain_score}}", str(strain_score))
            user_prompt = user_prompt.replace("{{recovery_score}}", str(recovery_score))
            user_prompt = user_prompt.replace("{{current_time}}", current_time)

            # Обрабатываем условную логику для Recovery
            # Упрощенная обработка: если Recovery < 50, добавляем соответствующую инструкцию
            if recovery_score < 50:
                user_prompt += "\n\nУчти: Recovery низкий (< 50%), значит восстановление недостаточное. Рекомендуй более щадящие техники восстановления."
            elif recovery_score >= 70:
                user_prompt += "\n\nУчти: Recovery хороший (>= 70%), значит организм готов к нагрузке. Можно рекомендовать более активные техники переключения."

            # Вызываем OpenRouter
            advice = await self._call_openrouter(user_prompt, max_retries=3, max_tokens=300)

            return advice.strip()

        except Exception as e:
            logger.error("Failed to generate stress advice", extra={"error": str(e)})
            # Fallback сообщение
            if recovery_score is not None and recovery_score < 50:
                return (
                    f"Твой текущий Strain: {strain_score:.1f}, Recovery низкий ({recovery_score:.0f}%). "
                    "Рекомендую сделать паузу: несколько глубоких вдохов, короткая прогулка или легкая растяжка. "
                    "Помни: восстановление — это инвестиция в завтрашнюю продуктивность."
                )
            else:
                return (
                    f"Твой текущий Strain: {strain_score:.1f}. "
                    "Рекомендую сделать паузу: несколько глубоких вдохов, переключение внимания на что-то другое, "
                    "или короткая прогулка. Помни: ясность важнее скорости."
                )

    async def close(self) -> None:
        """Закрытие HTTP клиента."""
        await self.client.aclose()

    async def health_check(self) -> tuple[bool, str]:
        """
        Проверка доступности OpenRouter API.

        Returns:
            Кортеж (успех, сообщение об ошибке)
        """
        try:
            # Простой тестовый запрос
            payload = {
                "model": self.openrouter_config.model,
                "messages": [
                    {"role": "user", "content": "test"},
                ],
                "max_tokens": 5,
            }

            response = await self.client.post(
                self.openrouter_config.api_url,
                json=payload,
                timeout=5.0,
            )

            if response.status_code == 200:
                return (True, "")
            
            # Пытаемся извлечь сообщение об ошибке
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text[:100])
            except Exception:
                error_msg = response.text[:100] if response.text else f"HTTP {response.status_code}"
            
            logger.warning(
                "OpenRouter health check failed",
                extra={"status_code": response.status_code, "error": error_msg},
            )
            return (False, error_msg)
        except Exception as e:
            error_msg = str(e)
            logger.warning("OpenRouter health check failed", extra={"error": error_msg})
            return (False, error_msg)

