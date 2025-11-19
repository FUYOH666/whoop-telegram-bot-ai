"""Тесты для slots.py."""

import pytest

from whoop_telegram_bot_ai.slots import (
    get_all_slot_ids,
    get_slot_buttons,
    get_slot_description,
    is_ideal_day,
    is_successful_response,
    parse_callback_data,
)


def test_get_all_slot_ids():
    """Тест получения всех идентификаторов слотов."""
    slot_ids = get_all_slot_ids()
    assert len(slot_ids) == 6
    assert "S1" in slot_ids
    assert "S6" in slot_ids


def test_get_slot_buttons():
    """Тест создания кнопок для слота."""
    keyboard = get_slot_buttons("S1")
    assert keyboard is not None
    assert len(keyboard.inline_keyboard) == 2  # Две кнопки для S1

    keyboard_s6 = get_slot_buttons("S6")
    assert len(keyboard_s6.inline_keyboard) == 3  # Три кнопки для S6


def test_parse_callback_data():
    """Тест парсинга callback_data."""
    # Валидный callback
    result = parse_callback_data("slot_S1_success")
    assert result == ("S1", "success")

    # Невалидный формат
    assert parse_callback_data("invalid_format") is None
    assert parse_callback_data("slot_S1") is None  # Неполный формат


def test_is_successful_response():
    """Тест определения успешного ответа."""
    # Для S1-S5 успешным считается "success"
    assert is_successful_response("S1", "success") is True
    assert is_successful_response("S1", "skip") is False

    # Для S6 успешным считается только "ideal"
    assert is_successful_response("S6", "ideal") is True
    assert is_successful_response("S6", "normal") is False
    assert is_successful_response("S6", "noise") is False


def test_is_ideal_day():
    """Тест логики определения эталонного дня."""
    # Эталонный день: 4 из 5 успешны + идеальный S6
    ideal_responses = {
        "S1": "success",
        "S2": "success",
        "S3": "success",
        "S4": "success",
        "S5": "skip",  # Один пропущен, но это OK
        "S6": "ideal",
    }
    assert is_ideal_day(ideal_responses, min_successful_slots=4) is True

    # Не эталонный: менее 4 успешных
    bad_responses = {
        "S1": "success",
        "S2": "success",
        "S3": "skip",
        "S4": "skip",
        "S5": "skip",
        "S6": "ideal",
    }
    assert is_ideal_day(bad_responses, min_successful_slots=4) is False

    # Не эталонный: S6 не идеален
    no_ideal_s6 = {
        "S1": "success",
        "S2": "success",
        "S3": "success",
        "S4": "success",
        "S5": "success",
        "S6": "normal",  # Не идеальный
    }
    assert is_ideal_day(no_ideal_s6, min_successful_slots=4) is False


def test_get_slot_description():
    """Тест получения описания слота."""
    desc = get_slot_description("S1")
    assert len(desc) > 0
    assert "Утро" in desc or "утро" in desc.lower()

    with pytest.raises(KeyError):
        get_slot_description("S99")  # Несуществующий слот

