"""Тесты для stats.py."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ras_bot.stats import StatsCalculator
from ras_bot.storage import Storage


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


@pytest.fixture
def stats_calculator(storage):
    """Создание экземпляра StatsCalculator для тестов."""
    return StatsCalculator(storage)


def test_calculate_statistics(stats_calculator, storage):
    """Тест расчета статистики."""
    # Добавляем тестовые данные
    storage.save_response("S1", "success")
    storage.save_response("S1", "success")
    storage.save_response("S1", "skip")
    storage.save_response("S2", "success")

    stats = stats_calculator.calculate_statistics(days=7)
    assert "slots" in stats
    assert "ideal_days" in stats
    assert "weakest_slot" in stats
    assert stats["period_days"] == 7


def test_format_stats_message(stats_calculator, storage):
    """Тест форматирования сообщения статистики."""
    # Добавляем тестовые данные
    storage.save_response("S1", "success")
    storage.save_response("S2", "success")

    stats = stats_calculator.calculate_statistics(days=7)
    message = stats_calculator.format_stats_message(stats)

    assert "Статистика" in message
    assert "дней" in message


def test_get_weakest_slot(stats_calculator, storage):
    """Тест определения слабого звена."""
    # S1: 100% успешных
    storage.save_response("S1", "success")
    storage.save_response("S1", "success")

    # S2: 50% успешных
    storage.save_response("S2", "success")
    storage.save_response("S2", "skip")

    stats = stats_calculator.calculate_statistics(days=7)
    weakest = stats["weakest_slot"]

    # Слабое звено должно быть S2
    assert weakest == "S2"


def test_get_context_for_slot(stats_calculator, storage):
    """Тест получения контекста для слота."""
    # Добавляем вчерашние данные
    from datetime import date, timedelta
    import sqlite3

    yesterday = (date.today() - timedelta(days=1)).isoformat()

    with sqlite3.connect(storage.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO slot_responses (date, slot_id, button_choice, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (yesterday, "S1", "success", "2024-01-01T12:00:00"),
        )
        conn.commit()

    # Контекст для S1 должен содержать yesterday_status
    context = stats_calculator.get_context_for_slot("S1")
    assert "yesterday_status" in context or "last_7_days_count" in context

    # Контекст для S6 должен содержать статусы всех слотов
    context_s6 = stats_calculator.get_context_for_slot("S6")
    # Проверяем наличие хотя бы одного статуса слота
    assert any(key.startswith("s") and key.endswith("_status") for key in context_s6.keys())

