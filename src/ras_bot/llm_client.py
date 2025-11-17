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

            message = await self._call_openrouter(user_prompt)

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

        # Для S6 заменяем статусы всех слотов
        if slot_config.slot_id == "S6":
            for i in range(1, 6):
                slot_status = context.get(f"s{i}_status", "неизвестно")
                if isinstance(slot_status, bool):
                    slot_status = "да" if slot_status else "нет"
                prompt = prompt.replace(f"{{{{s{i}_status}}}}", slot_status)

        return prompt

    async def _call_openrouter(self, user_prompt: str, max_retries: int = 3) -> str:
        """
        Вызов OpenRouter API с retry логикой.

        Args:
            user_prompt: User-промпт для отправки
            max_retries: Максимальное количество попыток

        Returns:
            Сгенерированное сообщение или пустая строка при ошибке
        """
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.openrouter_config.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": self.openrouter_config.temperature,
                    "max_tokens": self.openrouter_config.max_tokens,
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

