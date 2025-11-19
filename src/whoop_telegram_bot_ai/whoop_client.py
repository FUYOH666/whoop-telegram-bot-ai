"""Клиент для интеграции с WHOOP API."""

import asyncio
import logging
from datetime import date, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from whoop_telegram_bot_ai.config import WhoopConfig

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

    def _format_datetime(self, target_date: date, start_of_day: bool = True) -> str:
        """
        Форматирование даты в ISO 8601 date-time формат для WHOOP API v2.

        Args:
            target_date: Дата для форматирования
            start_of_day: Если True, возвращает начало дня (00:00:00.000Z), иначе конец дня (23:59:59.999Z)

        Returns:
            Строка в формате ISO 8601 date-time (например, "2025-11-18T00:00:00.000Z")
        """
        if start_of_day:
            dt = datetime.combine(target_date, datetime.min.time())
        else:
            dt = datetime.combine(target_date, datetime.max.time().replace(microsecond=999000))
        
        # Форматируем в ISO 8601 с UTC временной зоной
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

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

            # Логируем полный ответ для отладки
            logger.info(
                "Token exchange response received",
                extra={
                    "response_keys": list(token_data.keys()),
                    "response_preview": {k: str(v)[:50] + "..." if isinstance(v, str) and len(v) > 50 else v for k, v in token_data.items()},
                    "full_response": token_data,  # Сохраняем полный ответ для анализа
                },
            )

            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")  # Может отсутствовать в некоторых случаях
            expires_in = token_data.get("expires_in", 3600)
            
            # Логируем, что именно получили
            logger.info(
                "Token extraction",
                extra={
                    "has_access_token": bool(access_token),
                    "has_refresh_token": bool(refresh_token),
                    "expires_in": expires_in,
                    "all_response_keys": list(token_data.keys()),
                },
            )

            if not access_token:
                logger.error(
                    "Invalid token response structure - no access_token",
                    extra={
                        "response_keys": list(token_data.keys()),
                        "full_response": token_data,
                    },
                )
                raise ValueError(f"Invalid token response from WHOOP. Response keys: {list(token_data.keys())}")

            # Если refresh_token отсутствует в ответе, сохраняем access_token как refresh_token
            # Это позволяет системе попытаться использовать существующий токен при истечении
            # WHOOP API может продлевать токены автоматически при использовании или предоставлять долгоживущие токены
            if not refresh_token:
                logger.info(
                    "No refresh_token in response, will use access_token for token management",
                    extra={
                        "response_keys": list(token_data.keys()),
                        "expires_in": expires_in,
                    },
                )
                # Сохраняем access_token как refresh_token для отслеживания
                # Система будет пытаться использовать существующий токен при истечении
                refresh_token = access_token

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
            ValueError: Если обновление не удалось (требуется переавторизация)
        """
        if not self.config.is_configured:
            raise ValueError("WHOOP API not configured")

        tokens = self.storage.get_whoop_tokens(user_id)
        if not tokens:
            raise ValueError("No tokens found for user")

        refresh_token = tokens["refresh_token"]

        # Если refresh_token равен access_token, значит WHOOP API не предоставил отдельный refresh_token
        # В этом случае возвращаем существующий токен (он может быть еще валиден или долгоживущим)
        if refresh_token == tokens.get("access_token"):
            logger.info(
                "Refresh token equals access token, returning existing token (may be long-lived)",
                extra={"user_id": user_id},
            )
            # Возвращаем существующий токен - WHOOP может использовать долгоживущие токены
            # или продлевать их автоматически при использовании
            return tokens["access_token"]

        try:
            # WHOOP API требует redirect_uri при refresh (согласно OAuth 2.0 best practices)
            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
                "redirect_uri": self.config.redirect_uri,  # Добавляем redirect_uri для надежности
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
                logger.error(
                    "Invalid refresh response structure",
                    extra={"response_keys": list(token_data.keys())},
                )
                raise ValueError("Invalid token response from WHOOP")

            # Обновляем токены в БД
            # Если в ответе есть новый refresh_token, используем его, иначе оставляем старый
            new_refresh_token = token_data.get("refresh_token", refresh_token)
            self.storage.update_whoop_tokens(user_id, access_token, expires_in)
            
            # Если получен новый refresh_token, обновляем его тоже
            if new_refresh_token != refresh_token:
                # Обновляем refresh_token в БД
                self.storage.save_whoop_tokens(user_id, access_token, new_refresh_token, expires_in)

            logger.info("WHOOP access token refreshed", extra={"user_id": user_id})

            return access_token

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to refresh token",
                extra={"status_code": e.response.status_code, "error": e.response.text[:500]},
            )
            # Если refresh не работает, нужно переавторизоваться
            if e.response.status_code in [400, 401]:
                raise ValueError(
                    "Token refresh failed. Please reconnect WHOOP via /whoop_connect"
                ) from e
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

        Raises:
            ValueError: Если токен не найден или refresh не удался
        """
        tokens = self.storage.get_whoop_tokens(user_id)
        if not tokens:
            raise ValueError("No tokens found. Please connect WHOOP first.")

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        
        # Проверяем, не истек ли токен (с запасом в 5 минут)
        expires_at_str = tokens.get("expires_at")
        if expires_at_str:
            try:
                from datetime import datetime
                expires_at = datetime.fromisoformat(expires_at_str)
                now = datetime.now()
                time_until_expiry = (expires_at - now).total_seconds()
                
                # Если токен истекает в течение 5 минут, пытаемся обновить его
                if expires_at <= now or time_until_expiry < 300:
                    logger.info(
                        "Token expires soon, attempting refresh",
                        extra={
                            "user_id": user_id,
                            "expires_at": expires_at_str,
                            "time_until_expiry_seconds": time_until_expiry,
                        },
                    )
                    
                    # Если refresh_token отличается от access_token, пробуем refresh
                    if refresh_token and refresh_token != access_token:
                        try:
                            new_token = await self.refresh_access_token(user_id)
                            logger.info("Token refreshed successfully", extra={"user_id": user_id})
                            return new_token
                        except ValueError as e:
                            logger.warning(
                                "Token refresh failed, will try to use existing token",
                                extra={"user_id": user_id, "error": str(e)},
                            )
                            # Если refresh не работает, пробуем использовать существующий токен
                            # (возможно, он еще валиден или WHOOP продлевает его автоматически)
                            return access_token
                    else:
                        # Если refresh_token отсутствует или равен access_token,
                        # пробуем использовать существующий токен
                        # WHOOP может продлевать токены автоматически или они могут быть долгоживущими
                        logger.info(
                            "No refresh_token available, using existing token",
                            extra={"user_id": user_id, "expires_at": expires_at_str},
                        )
                        return access_token
            except Exception as e:
                logger.warning("Failed to parse expires_at", extra={"error": str(e)})

        return access_token

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

                if response.status_code == 401:
                    # Токен невалиден
                    if attempt < max_retries - 1:
                        # Пробуем обновить токен
                        logger.warning("Token expired, attempting refresh...", extra={"user_id": user_id})
                        try:
                            await self.refresh_access_token(user_id)
                            continue
                        except ValueError as refresh_error:
                            # Если refresh не работает, это означает, что нужна переавторизация
                            logger.error(
                                "Token refresh failed, reconnection required",
                                extra={"user_id": user_id, "error": str(refresh_error)},
                            )
                            raise ValueError(
                                "WHOOP token expired and refresh failed. Please reconnect via /whoop_connect"
                            ) from refresh_error
                    else:
                        # Все попытки исчерпаны
                        raise ValueError(
                            "WHOOP token expired. Please reconnect via /whoop_connect"
                        )

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
        Получение Recovery Score за указанную дату через /v2/recovery endpoint.

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Словарь с данными Recovery или None при ошибке
        """
        if target_date is None:
            target_date = date.today()

        try:
            # WHOOP API v2 требует ISO 8601 date-time формат
            start = self._format_datetime(target_date, start_of_day=True)
            end = self._format_datetime(target_date, start_of_day=False)

            response = await self._make_request(
                user_id, "/v2/recovery", params={"start": start, "end": end}
            )

            # WHOOP v2 возвращает {"records": [...], "next_token": "..."}
            records = response.get("records", [])
            if records:
                return records[0]  # Возвращаем первую запись за день
            return None

        except Exception as e:
            logger.error("Failed to get recovery", extra={"error": str(e), "date": target_date.isoformat()})
            return None

    async def get_sleep(self, user_id: int, target_date: date | None = None) -> dict[str, Any] | None:
        """
        Получение данных сна за указанную дату через /v2/activity/sleep endpoint.

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Словарь с данными сна или None при ошибке
        """
        if target_date is None:
            target_date = date.today()

        try:
            # WHOOP API v2 требует ISO 8601 date-time формат
            start = self._format_datetime(target_date, start_of_day=True)
            end = self._format_datetime(target_date, start_of_day=False)

            response = await self._make_request(
                user_id, "/v2/activity/sleep", params={"start": start, "end": end}
            )

            # WHOOP v2 возвращает {"records": [...], "next_token": "..."}
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
        Получение тренировок за указанную дату через /v2/activity/workout endpoint.

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Список тренировок или пустой список при ошибке
        """
        if target_date is None:
            target_date = date.today()

        try:
            # WHOOP API v2 требует ISO 8601 date-time формат
            start = self._format_datetime(target_date, start_of_day=True)
            end = self._format_datetime(target_date, start_of_day=False)

            response = await self._make_request(
                user_id, "/v2/activity/workout", params={"start": start, "end": end}
            )

            # WHOOP v2 возвращает {"records": [...], "next_token": "..."}
            return response.get("records", [])

        except Exception as e:
            logger.error("Failed to get workouts", extra={"error": str(e), "date": target_date.isoformat()})
            return []

    async def get_cycle(self, user_id: int, target_date: date | None = None) -> dict[str, Any] | None:
        """
        Получение данных цикла (cycle) за указанную дату через /v2/cycle endpoint.
        
        Cycle содержит Strain за день.

        Args:
            user_id: ID пользователя Telegram
            target_date: Дата (по умолчанию сегодня)

        Returns:
            Словарь с данными цикла или None при ошибке
        """
        if target_date is None:
            target_date = date.today()

        try:
            # WHOOP API v2 требует ISO 8601 date-time формат
            start = self._format_datetime(target_date, start_of_day=True)
            end = self._format_datetime(target_date, start_of_day=False)

            response = await self._make_request(
                user_id, "/v2/cycle", params={"start": start, "end": end}
            )

            records = response.get("records", [])
            if records:
                return records[0]  # Возвращаем первую запись за день
            return None

        except Exception as e:
            logger.warning("Failed to get cycle data", extra={"error": str(e), "date": target_date.isoformat()})
            return None

    async def get_all_data(self, user_id: int, target_date: date | None = None) -> dict[str, Any]:
        """
        Получение всех данных WHOOP за указанную дату (агрегация) через v2 API.

        Использует /v2/cycle для получения Strain, /v2/recovery для Recovery,
        /v2/activity/sleep для Sleep, /v2/activity/workout для тренировок.

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
            # Получаем Strain из /v2/cycle (основной источник для Strain за день)
            cycle = await self.get_cycle(user_id, target_date)
            if cycle:
                score = cycle.get("score", {})
                # Strain из cycle (это дневной Strain)
                if "strain" in score:
                    result["strain_score"] = score.get("strain")
                result["raw_data"]["cycle"] = cycle
                logger.info("WHOOP cycle data retrieved", extra={"date": target_date.isoformat(), "strain": result["strain_score"]})
            
            # Получаем Recovery из /v2/recovery
            recovery = await self.get_recovery(user_id, target_date)
            if recovery:
                score = recovery.get("score", {})
                # Recovery score из recovery (в v2 API это recovery_score, не recovery_percentage)
                if "recovery_score" in score:
                    result["recovery_score"] = score.get("recovery_score")
                elif "recovery_percentage" in score:  # Fallback для совместимости
                    result["recovery_score"] = score.get("recovery_percentage")
                result["raw_data"]["recovery"] = recovery

            # Получаем Sleep из /v2/activity/sleep
            sleep = await self.get_sleep(user_id, target_date)
            if sleep:
                score = sleep.get("score", {})
                stage_summary = score.get("stage_summary", {})
                # Продолжительность сна в миллисекундах из stage_summary.total_in_bed_time_milli
                sleep_duration_ms = stage_summary.get("total_in_bed_time_milli", 0)
                if sleep_duration_ms:
                    result["sleep_duration"] = sleep_duration_ms / (1000 * 60 * 60)  # Конвертируем в часы
                result["raw_data"]["sleep"] = sleep

            # Получаем Workouts из /v2/activity/workout для подсчета количества тренировок
            workouts = await self.get_workouts(user_id, target_date)
            result["workouts_count"] = len(workouts)
            result["raw_data"]["workouts"] = workouts

            # Если Strain не получен из cycle, рассчитываем из тренировок как fallback
            if result["strain_score"] is None and workouts:
                total_strain = sum(
                    workout.get("score", {}).get("strain", 0)
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

