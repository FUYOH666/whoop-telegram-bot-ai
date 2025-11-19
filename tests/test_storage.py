"""Тесты для storage.py."""

import tempfile
from pathlib import Path

import pytest

from whoop_telegram_bot_ai.storage import Storage


@pytest.fixture
def temp_db():
    """Создание временной БД для тестов."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def storage(temp_db):
    """Создание экземпляра Storage для тестов."""
    return Storage(db_path=temp_db)


def test_save_response(storage):
    """Тест сохранения ответа."""
    storage.save_response("S1", "success")
    responses = storage.get_day_responses()
    assert "S1" in responses
    assert responses["S1"] == "success"


def test_get_slot_statistics(storage):
    """Тест получения статистики по слоту."""
    # Сохраняем несколько ответов
    storage.save_response("S1", "success")
    storage.save_response("S1", "success")
    storage.save_response("S1", "skip")

    stats = storage.get_slot_statistics("S1", days=7)
    assert stats["total"] == 3
    assert stats["successful"] == 2
    assert stats["percentage"] == pytest.approx(66.7, abs=0.1)


def test_get_recent_responses(storage):
    """Тест получения последних ответов."""
    storage.save_response("S1", "success")
    storage.save_response("S1", "skip")
    storage.save_response("S1", "success")

    recent = storage.get_recent_responses("S1", limit=2)
    assert len(recent) == 2
    assert recent[0]["button_choice"] == "success"


def test_get_ideal_days_count(storage):
    """Тест подсчета эталонных дней."""
    # Создаем эталонный день: S1-S5 успешны, S6 идеален
    from datetime import date, timedelta

    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # Симулируем успешные ответы для S1-S5
    # Используем прямые SQL запросы для установки даты
    import sqlite3

    with sqlite3.connect(storage.db_path) as conn:
        cursor = conn.cursor()
        for slot_id in ["S1", "S2", "S3", "S4", "S5"]:
            cursor.execute(
                """
                INSERT INTO slot_responses (date, slot_id, button_choice, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (yesterday, slot_id, "success", "2024-01-01T12:00:00"),
            )
        # S6 с идеальным ответом
        cursor.execute(
            """
            INSERT INTO slot_responses (date, slot_id, button_choice, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (yesterday, "S6", "ideal", "2024-01-01T21:00:00"),
        )
        conn.commit()

    ideal_count = storage.get_ideal_days_count(days=7)
    assert ideal_count >= 1


def test_is_ideal_day_logic(storage):
    """Тест логики определения эталонного дня."""
    # Тест с 4 успешными из 5 и идеальным S6
    responses = {
        "S1": "success",
        "S2": "success",
        "S3": "success",
        "S4": "success",
        "S5": "skip",  # Один пропущен
        "S6": "ideal",
    }
    assert storage._is_ideal_day(responses) is True

    # Тест с менее чем 4 успешными
    responses_bad = {
        "S1": "success",
        "S2": "success",
        "S3": "skip",
        "S4": "skip",
        "S5": "skip",
        "S6": "ideal",
    }
    assert storage._is_ideal_day(responses_bad) is False

    # Тест без идеального S6
    responses_no_s6 = {
        "S1": "success",
        "S2": "success",
        "S3": "success",
        "S4": "success",
        "S5": "success",
        "S6": "normal",  # Не идеальный
    }
    assert storage._is_ideal_day(responses_no_s6) is False

