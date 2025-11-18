"""Клиент для интеграции с WHOOP API."""

import asyncio
import logging
from datetime import date, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from ras_bot.config import WhoopConfig

logger = logging.getLogger(__name__)


class WhoopClient:
    """Клиент для работы с WHOOP API."""

    def __init__(self, config: WhoopConfig, storage: Any):
        """
        Инициализация клиента.

        Args:
            config: Конфигурация WHOOP API
            storage: Экземпляр Storage для работы с токенами
        """
        self.config = config
        self.storage = storage
        self.client = httpx.AsyncClient(timeout=30.0)

    def get_authorization_url(self, user_id: int, state: str | None = None) -> str:
        """
        Генерация URL для авторизации OAuth 2.0.

        Args:
            user_id: ID пользователя Telegram (для state)
            state: Дополнительный state параметр (опционально)

        Returns:
            URL для авторизации
        """
        if not self.config.is_configured:
            raise ValueError("WHOOP API not configured. Please set WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET")

        if state is None:
            state = str(user_id)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }

        return f"{self.config.oauth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self, user_id: int, authorization_code: str
    ) -> dict[str, Any]:
        """
        Обмен authorization code на access_token и refresh_token.

        Args:
            user_id: ID пользователя Telegram
            authorization_code: Authorization code от WHOOP

        Returns:
            Словарь с токенами:
            {
                "access_token": str,
                "refresh_token": str,
                "expires_in": int
            }

        Raises:
            ValueError: Если обмен не удался
        """
        if not self.config.is_configured:
            raise ValueError("WHOOP API not configured")

        try:
            # Очищаем code от возможных лишних символов (если пользователь скопировал весь URL)
            code = authorization_code.split("&")[0].split("?")[0].strip()
            
            data = {
                "grant_type": "authorization_code",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "code": code,
                "redirect_uri": self.config.redirect_uri,
            }

            logger.info(
                "Exchanging authorization code for tokens",
                extra={
                    "user_id": user_id,
                    "code_length": len(code),
                    "code_preview": code[:20] + "..." if len(code) > 20 else code,
                    "redirect_uri": self.config.redirect_uri,
                    "client_id": self.config.client_id[:20] + "..." if self.config.client_id else None,
                },
            )

            # Логируем данные запроса (без секретов)
            log_data = {k: v if k != "client_secret" else "***" for k, v in data.items()}
            logger.debug("Token exchange request data", extra={"data": log_data})

            response = await self.client.post(
                self.config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Логируем детали ответа для отладки
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    logger.error(
                        "WHOOP token exchange failed",
                        extra={
                            "status_code": response.status_code,
                            "error": error_data,
                            "response_text": response.text[:500],
                        },
                    )
                except Exception:
                    logger.error(
                        "WHOOP token exchange failed",
                        extra={
                            "status_code": response.status_code,
                            "response_text": response.text[:500],
                        },
                    )

            response.raise_for_status()
            token_data = response.json()

            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)

            if not access_token or not refresh_token:
                logger.error(
                    "Invalid token response structure",
                    extra={"response_keys": list(token_data.keys())},
                )
                raise ValueError("Invalid token response from WHOOP")

            # Сохраняем токены в БД
            self.storage.save_whoop_tokens(user_id, access_token, refresh_token, expires_in)

            logger.info("WHOOP tokens exchanged successfully", extra={"user_id": user_id})

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to exchange code: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg += f" - {error_data.get('error')}"
                if "error_description" in error_data:
                    error_msg += f": {error_data.get('error_description')}"
            except Exception:
                error_msg += f" - {e.response.text[:200]}"
            
            logger.error(
                "Failed to exchange code for tokens",
                extra={
                    "status_code": e.response.status_code,
                    "error": error_msg,
                    "response_text": e.response.text[:500],
                },
            )
            raise ValueError(error_msg) from e
        except Exception as e:
            logger.error("Unexpected error exchanging code", extra={"error": str(e)}, exc_info=True)
            raise ValueError(f"Failed to exchange code: {str(e)}") from e

    async def refresh_access_token(self, user_id: int) -> str:
        """
        Обновление access_token через refresh_token.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Новый access_token

        Raises:
            ValueError: Если обновление не удалось
        """
        if not self.config.is_configured:
            raise ValueError("WHOOP API not configured")

        tokens = self.storage.get_whoop_tokens(user_id)
        if not tokens:
            raise ValueError("No tokens found for user")

        refresh_token = tokens["refresh_token"]

        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
            }

            response = await self.client.post(
                self.config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            response.raise_for_status()
            token_data = response.json()

            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)

            if not access_token:
                raise ValueError("Invalid token response from WHOOP")

            # Обновляем токены в БД
            self.storage.update_whoop_tokens(user_id, access_token, expires_in)

            logger.info("WHOOP access token refreshed", extra={"user_id": user_id})

            return access_token

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to refresh token",
                extra={"status_code": e.response.status_code, "error": e.response.text},
            )
            raise ValueError(f"Failed to refresh token: {e.response.status_code}") from e
        except Exception as e:
            logger.error("Unexpected error refreshing token", extra={"error": str(e)})
            raise ValueError(f"Failed to refresh token: {str(e)}") from e

    async def _get_access_token(self, user_id: int) -> str:
        """
        Получение валидного access_token (с автоматическим refresh при необходимости).

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Валидный access_token
        """
        tokens = self.storage.get_whoop_tokens(user_id)
        if not tokens:
            raise ValueError("No tokens found. Please connect WHOOP first.")

        # Проверяем, не истек ли токен (с запасом в 5 минут)
        expires_at = datetime.fromisoformat(tokens["expires_at"])
        if datetime.now() >= expires_at:
            # Токен истек, обновляем
            return await self.refresh_access_token(user_id)

        return tokens["access_token"]

    async def _make_request(
        self, user_id: int, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Выполнение запроса к WHOOP API с автоматическим refresh токена.

        Args:
            user_id: ID пользователя Telegram
            endpoint: Endpoint API (например, "/recovery")
            params: Параметры запроса

        Returns:
            Ответ от API

        Raises:
            ValueError: Если запрос не удался
        """
        if not self.config.is_configured:
            raise ValueError("WHOOP API not configured")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                access_token = await self._get_access_token(user_id)

                url = f"{self.config.api_url}{endpoint}"
                headers = {"Authorization": f"Bearer {access_token}"}

                response = await self.client.get(url, headers=headers, params=params)

                if response.status_code == 401 and attempt < max_retries - 1:
                    # Токен невалиден, пробуем обновить
                    logger.warning("Token expired, refreshing...", extra={"user_id": user_id})
                    await self.refresh_access_token(user_id)
                    continue

                # Обработка rate limit (429 Too Many Requests)
                if response.status_code == 429:
                    # Извлекаем Retry-After заголовок, если есть
                    retry_after = response.headers.get("Retry-After", "60")
                    try:
                        wait_seconds = int(retry_after)
                    except ValueError:
                        wait_seconds = 60  # По умолчанию 60 секунд

                    if attempt < max_retries - 1:
                        logger.warning(
                            "WHOOP API rate limit exceeded, waiting before retry",
                            extra={
                                "endpoint": endpoint,
                                "retry_after": wait_seconds,
                                "attempt": attempt + 1,
                            },
                        )
                        await asyncio.sleep(wait_seconds)
                        continue
                    else:
                        logger.error(
                            "WHOOP API rate limit exceeded after all retries",
                            extra={"endpoint": endpoint},
                        )
                        raise ValueError(
                            f"WHOOP API rate limit exceeded. Please try again later."
                        )

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                # Пропускаем 429, так как уже обработали выше
                if e.response.status_code == 429:
                    continue

                logger.error(
                    "WHOOP API request failed",
                    extra={
                        "endpoint": endpoint,
                        "status_code": e.response.status_code,
                        "error": e.response.text[:200],  # Ограничиваем длину лога
                    },
                )
                raise ValueError(f"WHOOP API error: {e.response.status_code}") from e
            except Exception as e:
                logger.error("Unexpected error calling WHOOP API", extra={"error": str(e)})
                raise ValueError(f"WHOOP API error: {str(e)}") from e

        raise ValueError("Failed to get valid access token")

    async def get_recovery(self, user_id: int, target_date: date | None = None) -> dict[str, Any] | None:
        """
        Получение Recovery Score за указанную дату.

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Словарь с данными Recovery или None при ошибке
        """
        if target_date is None:
            target_date = date.today()

        try:
            # WHOOP API использует формат YYYY-MM-DD для дат
            start = target_date.isoformat()
            end = target_date.isoformat()

            response = await self._make_request(
                user_id, "/recovery", params={"start": start, "end": end}
            )

            # WHOOP возвращает массив записей
            records = response.get("records", [])
            if records:
                return records[0]  # Возвращаем первую запись за день
            return None

        except Exception as e:
            logger.error("Failed to get recovery", extra={"error": str(e), "date": target_date.isoformat()})
            return None

    async def get_sleep(self, user_id: int, target_date: date | None = None) -> dict[str, Any] | None:
        """
        Получение данных сна за указанную дату.

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Словарь с данными сна или None при ошибке
        """
        if target_date is None:
            target_date = date.today()

        try:
            start = target_date.isoformat()
            end = target_date.isoformat()

            response = await self._make_request(user_id, "/sleep", params={"start": start, "end": end})

            records = response.get("records", [])
            if records:
                return records[0]
            return None

        except Exception as e:
            logger.error("Failed to get sleep", extra={"error": str(e), "date": target_date.isoformat()})
            return None

    async def get_strain(self, user_id: int, target_date: date | None = None) -> dict[str, Any] | None:
        """
        Получение Strain Score за указанную дату.

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Словарь с данными Strain или None при ошибке
        """
        if target_date is None:
            target_date = date.today()

        try:
            start = target_date.isoformat()
            end = target_date.isoformat()

            response = await self._make_request(user_id, "/workout", params={"start": start, "end": end})

            records = response.get("records", [])
            if records:
                # Strain обычно рассчитывается из тренировок
                # Возвращаем агрегированные данные за день
                total_strain = sum(record.get("score", {}).get("strain", 0) for record in records)
                return {"strain": total_strain, "workouts": records}
            return None

        except Exception as e:
            logger.error("Failed to get strain", extra={"error": str(e), "date": target_date.isoformat()})
            return None

    async def get_workouts(self, user_id: int, target_date: date | None = None) -> list[dict[str, Any]]:
        """
        Получение тренировок за указанную дату.

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Список тренировок или пустой список при ошибке
        """
        if target_date is None:
            target_date = date.today()

        try:
            start = target_date.isoformat()
            end = target_date.isoformat()

            response = await self._make_request(user_id, "/workout", params={"start": start, "end": end})

            return response.get("records", [])

        except Exception as e:
            logger.error("Failed to get workouts", extra={"error": str(e), "date": target_date.isoformat()})
            return []

    async def get_all_data(self, user_id: int, target_date: date | None = None) -> dict[str, Any]:
        """
        Получение всех данных WHOOP за указанную дату (агрегация).

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Словарь с агрегированными данными:
            {
                "recovery_score": float | None,
                "sleep_duration": float | None,
                "strain_score": float | None,
                "workouts_count": int,
                "raw_data": dict
            }
        """
        if target_date is None:
            target_date = date.today()

        result = {
            "recovery_score": None,
            "sleep_duration": None,
            "strain_score": None,
            "workouts_count": 0,
            "raw_data": {},
        }

        try:
            # Получаем Recovery
            recovery = await self.get_recovery(user_id, target_date)
            if recovery:
                result["recovery_score"] = recovery.get("score", {}).get("recovery_percentage")
                result["raw_data"]["recovery"] = recovery

            # Получаем Sleep
            sleep = await self.get_sleep(user_id, target_date)
            if sleep:
                # Продолжительность сна в часах
                sleep_duration_ms = sleep.get("score", {}).get("total_sleep_time_milli", 0)
                result["sleep_duration"] = sleep_duration_ms / (1000 * 60 * 60) if sleep_duration_ms else None
                result["raw_data"]["sleep"] = sleep

            # Получаем Workouts и рассчитываем Strain
            workouts = await self.get_workouts(user_id, target_date)
            result["workouts_count"] = len(workouts)
            result["raw_data"]["workouts"] = workouts

            if workouts:
                # Рассчитываем общий Strain из тренировок
                # Strain может быть в score.strain или в score.zone_duration (зависит от API версии)
                total_strain = sum(
                    workout.get("score", {}).get("strain", 0) 
                    or workout.get("score", {}).get("kilojoule", 0) / 100  # Fallback расчет
                    for workout in workouts
                )
                result["strain_score"] = total_strain if total_strain > 0 else None

            return result

        except Exception as e:
            logger.error("Failed to get all WHOOP data", extra={"error": str(e)})
            return result

    async def close(self) -> None:
        """Закрытие HTTP клиента."""
        await self.client.aclose()

