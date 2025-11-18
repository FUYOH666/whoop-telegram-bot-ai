"""Хранилище данных для RAS Bot - SQLite база данных."""

import sqlite3
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Storage:
    """Управление SQLite базой данных для хранения ответов пользователя."""

    def __init__(self, db_path: str = "ras_bot.db"):
        """
        Инициализация хранилища.

        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self) -> None:
        """Инициализация схемы базы данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS slot_responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        slot_id TEXT NOT NULL,
                        button_choice TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_date_slot 
                    ON slot_responses(date, slot_id)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_date 
                    ON slot_responses(date)
                    """
                )
                # Таблица для хранения WHOOP токенов
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS whoop_tokens (
                        user_id INTEGER PRIMARY KEY,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                # Таблица для хранения данных WHOOP
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS whoop_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        recovery_score REAL,
                        sleep_duration REAL,
                        strain_score REAL,
                        workouts_count INTEGER,
                        raw_data TEXT,
                        updated_at TEXT NOT NULL,
                        UNIQUE(date)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_whoop_data_date 
                    ON whoop_data(date)
                    """
                )
                conn.commit()
                logger.info("Database initialized successfully", extra={"db_path": str(self.db_path)})
        except sqlite3.Error as e:
            logger.error("Failed to initialize database", extra={"error": str(e)})
            raise

    def save_response(self, slot_id: str, button_choice: str) -> None:
        """
        Сохранение ответа пользователя на слот.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            button_choice: Выбранная кнопка пользователя
        """
        today = date.today().isoformat()
        timestamp = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO slot_responses (date, slot_id, button_choice, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (today, slot_id, button_choice, timestamp),
                )
                conn.commit()
                logger.info(
                    "Response saved",
                    extra={
                        "slot_id": slot_id,
                        "button_choice": button_choice,
                        "date": today,
                    },
                )
        except sqlite3.Error as e:
            logger.error("Failed to save response", extra={"error": str(e), "slot_id": slot_id})
            raise

    def get_slot_statistics(self, slot_id: str, days: int = 7) -> dict:
        """
        Получение статистики по конкретному слоту за указанный период.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            days: Количество дней для анализа

        Returns:
            Словарь со статистикой:
            {
                "total": общее количество ответов,
                "successful": количество успешных выполнений,
                "percentage": процент успешных выполнений
            }
        """
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - days + 1)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Получаем все ответы за период
                cursor.execute(
                    """
                    SELECT button_choice, COUNT(*) as count
                    FROM slot_responses
                    WHERE slot_id = ? AND date >= ? AND date <= ?
                    GROUP BY button_choice
                    """,
                    (slot_id, start_date.isoformat(), end_date.isoformat()),
                )

                rows = cursor.fetchall()
                total = sum(row["count"] for row in rows)

                # Определяем успешные ответы (для каждого слота своя логика)
                # Для S1-S5: кнопки с "✅" или "🚀" или "💰" или "🧘" или "🌅" считаются успешными
                # Для S6: кнопка "ideal" считается успешной
                successful = 0
                for row in rows:
                    choice = row["button_choice"]
                    if slot_id == "S6":
                        if choice == "ideal":
                            successful += row["count"]
                    else:
                        # Для S1-S5 успешные кнопки содержат определенные эмодзи или ключевые слова
                        if any(
                            marker in choice.lower()
                            for marker in ["✅", "🚀", "💰", "🧘", "🌅", "был", "сделал", "была"]
                        ):
                            successful += row["count"]

                percentage = (successful / total * 100) if total > 0 else 0.0

                return {
                    "total": total,
                    "successful": successful,
                    "percentage": round(percentage, 1),
                }
        except sqlite3.Error as e:
            logger.error(
                "Failed to get slot statistics",
                extra={"error": str(e), "slot_id": slot_id, "days": days},
            )
            return {"total": 0, "successful": 0, "percentage": 0.0}

    def get_day_responses(self, target_date: Optional[str] = None) -> dict:
        """
        Получение всех ответов за указанный день.

        Args:
            target_date: Дата в формате YYYY-MM-DD. Если None, используется сегодняшняя дата.

        Returns:
            Словарь {slot_id: button_choice} для всех слотов за день
        """
        if target_date is None:
            target_date = date.today().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT slot_id, button_choice
                    FROM slot_responses
                    WHERE date = ?
                    ORDER BY timestamp DESC
                    """,
                    (target_date,),
                )

                rows = cursor.fetchall()
                # Берем последний ответ для каждого слота за день
                responses = {}
                for row in rows:
                    slot_id = row["slot_id"]
                    if slot_id not in responses:
                        responses[slot_id] = row["button_choice"]

                return responses
        except sqlite3.Error as e:
            logger.error(
                "Failed to get day responses",
                extra={"error": str(e), "date": target_date},
            )
            return {}

    def get_recent_responses(self, slot_id: str, limit: int = 5) -> list[dict]:
        """
        Получение последних N ответов по конкретному слоту.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            limit: Количество последних ответов

        Returns:
            Список словарей с информацией об ответах:
            [{"date": "2024-01-01", "button_choice": "✅", "timestamp": "..."}, ...]
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT date, button_choice, timestamp
                    FROM slot_responses
                    WHERE slot_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (slot_id, limit),
                )

                rows = cursor.fetchall()
                return [
                    {
                        "date": row["date"],
                        "button_choice": row["button_choice"],
                        "timestamp": row["timestamp"],
                    }
                    for row in rows
                ]
        except sqlite3.Error as e:
            logger.error(
                "Failed to get recent responses",
                extra={"error": str(e), "slot_id": slot_id, "limit": limit},
            )
            return []

    def get_ideal_days_count(self, days: int = 30) -> int:
        """
        Подсчет количества эталонных дней за указанный период.

        Args:
            days: Количество дней для анализа

        Returns:
            Количество эталонных дней
        """
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - days + 1)

        ideal_count = 0

        try:
            # Проверяем каждый день в периоде
            current_date = start_date
            while current_date <= end_date:
                day_responses = self.get_day_responses(current_date.isoformat())
                if self._is_ideal_day(day_responses):
                    ideal_count += 1
                current_date = date.fromordinal(current_date.toordinal() + 1)

            return ideal_count
        except Exception as e:
            logger.error(
                "Failed to get ideal days count",
                extra={"error": str(e), "days": days},
            )
            return 0

    def _is_ideal_day(self, responses: dict) -> bool:
        """
        Проверка, был ли день эталонным.

        Логика:
        - S1-S5: минимум 4 из 5 должны быть выполнены
        - S6: должна быть выбрана кнопка "ideal"

        Args:
            responses: Словарь {slot_id: button_choice} для дня

        Returns:
            True если день эталонный, False иначе
        """
        # Проверяем S1-S5
        s1_s5_slots = ["S1", "S2", "S3", "S4", "S5"]
        successful_slots = 0

        for slot_id in s1_s5_slots:
            if slot_id in responses:
                choice = responses[slot_id].lower()
                # Успешные кнопки содержат определенные маркеры
                if any(
                    marker in choice
                    for marker in ["✅", "🚀", "💰", "🧘", "🌅", "был", "сделал", "была"]
                ):
                    successful_slots += 1

        # Минимум 4 из 5 должны быть выполнены
        if successful_slots < 4:
            return False

        # Проверяем S6
        if "S6" not in responses:
            return False

        s6_choice = responses["S6"].lower()
        return "эталон" in s6_choice or "ideal" in s6_choice

    def save_whoop_tokens(
        self, user_id: int, access_token: str, refresh_token: str, expires_in: int
    ) -> None:
        """
        Сохранение WHOOP токенов для пользователя.

        Args:
            user_id: ID пользователя Telegram
            access_token: Access token от WHOOP
            refresh_token: Refresh token от WHOOP
            expires_in: Время жизни токена в секундах
        """
        expires_at = datetime.fromtimestamp(datetime.now().timestamp() + expires_in).isoformat()
        updated_at = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO whoop_tokens 
                    (user_id, access_token, refresh_token, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, access_token, refresh_token, expires_at, updated_at),
                )
                conn.commit()
                logger.info("WHOOP tokens saved", extra={"user_id": user_id})
        except sqlite3.Error as e:
            logger.error("Failed to save WHOOP tokens", extra={"error": str(e), "user_id": user_id})
            raise

    def get_whoop_tokens(self, user_id: int) -> dict | None:
        """
        Получение WHOOP токенов для пользователя.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Словарь с токенами или None если токены не найдены:
            {
                "access_token": str,
                "refresh_token": str,
                "expires_at": str (ISO format),
                "updated_at": str (ISO format)
            }
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT access_token, refresh_token, expires_at, updated_at
                    FROM whoop_tokens
                    WHERE user_id = ?
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "access_token": row["access_token"],
                        "refresh_token": row["refresh_token"],
                        "expires_at": row["expires_at"],
                        "updated_at": row["updated_at"],
                    }
                return None
        except sqlite3.Error as e:
            logger.error("Failed to get WHOOP tokens", extra={"error": str(e), "user_id": user_id})
            return None

    def update_whoop_tokens(
        self, user_id: int, access_token: str, expires_in: int
    ) -> None:
        """
        Обновление access_token для пользователя (при refresh).

        Args:
            user_id: ID пользователя Telegram
            access_token: Новый access token
            expires_in: Время жизни токена в секундах
        """
        expires_at = datetime.fromtimestamp(datetime.now().timestamp() + expires_in).isoformat()
        updated_at = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE whoop_tokens
                    SET access_token = ?, expires_at = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (access_token, expires_at, updated_at, user_id),
                )
                conn.commit()
                logger.info("WHOOP tokens updated", extra={"user_id": user_id})
        except sqlite3.Error as e:
            logger.error("Failed to update WHOOP tokens", extra={"error": str(e), "user_id": user_id})
            raise

    def save_whoop_data(
        self,
        target_date: str,
        recovery_score: float | None = None,
        sleep_duration: float | None = None,
        strain_score: float | None = None,
        workouts_count: int | None = None,
        raw_data: dict | None = None,
    ) -> None:
        """
        Сохранение данных WHOOP за указанную дату.

        Args:
            target_date: Дата в формате YYYY-MM-DD
            recovery_score: Recovery Score (0-100)
            sleep_duration: Продолжительность сна в часах
            strain_score: Strain Score
            workouts_count: Количество тренировок
            raw_data: Сырые данные в формате JSON (опционально)
        """
        updated_at = datetime.now().isoformat()
        raw_data_json = None
        if raw_data:
            import json
            raw_data_json = json.dumps(raw_data)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO whoop_data 
                    (date, recovery_score, sleep_duration, strain_score, workouts_count, raw_data, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_date,
                        recovery_score,
                        sleep_duration,
                        strain_score,
                        workouts_count,
                        raw_data_json,
                        updated_at,
                    ),
                )
                conn.commit()
                logger.info("WHOOP data saved", extra={"date": target_date})
        except sqlite3.Error as e:
            logger.error("Failed to save WHOOP data", extra={"error": str(e), "date": target_date})
            raise

    def get_today_whoop_data(self) -> dict | None:
        """
        Получение данных WHOOP за сегодня.

        Returns:
            Словарь с данными или None если данных нет:
            {
                "recovery_score": float | None,
                "sleep_duration": float | None,
                "strain_score": float | None,
                "workouts_count": int | None,
                "raw_data": dict | None
            }
        """
        today = date.today().isoformat()
        return self.get_whoop_data(today)

    def get_whoop_data(self, target_date: str) -> dict | None:
        """
        Получение данных WHOOP за указанную дату.

        Args:
            target_date: Дата в формате YYYY-MM-DD

        Returns:
            Словарь с данными или None если данных нет
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT recovery_score, sleep_duration, strain_score, workouts_count, raw_data
                    FROM whoop_data
                    WHERE date = ?
                    """,
                    (target_date,),
                )
                row = cursor.fetchone()
                if row:
                    result = {
                        "recovery_score": row["recovery_score"],
                        "sleep_duration": row["sleep_duration"],
                        "strain_score": row["strain_score"],
                        "workouts_count": row["workouts_count"],
                        "raw_data": None,
                    }
                    if row["raw_data"]:
                        import json
                        try:
                            result["raw_data"] = json.loads(row["raw_data"])
                        except json.JSONDecodeError:
                            pass
                    return result
                return None
        except sqlite3.Error as e:
            logger.error("Failed to get WHOOP data", extra={"error": str(e), "date": target_date})
            return None

