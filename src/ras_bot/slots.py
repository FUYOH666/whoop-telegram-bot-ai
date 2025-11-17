"""Логика слотов RAS Bot - определение 6 слотов и эталонного дня."""

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# Определение кнопок для каждого слота
SLOT_BUTTONS: dict[str, list[tuple[str, str]]] = {
    "S1": [
        ("✅ Утро по плану (подъём, завтрак, зал/море)", "success"),
        ("⏭ Сегодня утренний ритуал пропустил", "skip"),
    ],
    "S2": [
        ("🧘 Пауза 'я есть' была", "success"),
        ("💨 Проскочил без паузы", "skip"),
    ],
    "S3": [
        ("🚀 Был фокус-квант над главным проектом", "success"),
        ("🧩 Размазался по задачам", "skip"),
    ],
    "S4": [
        ("💰 Сделал шаг к деньгам/рынку", "success"),
        ("⏭ Пока без шага к деньгам", "skip"),
    ],
    "S5": [
        ("🌅 Был закат/природа/присутствие", "success"),
        ("🏠 Пропустил вечерний ритуал", "skip"),
    ],
    "S6": [
        ("✨ День ближе к эталону", "ideal"),
        ("🙂 Норм, но не цезий", "normal"),
        ("🌀 День ушёл в шум", "noise"),
    ],
}

# Описания слотов
SLOT_DESCRIPTIONS: dict[str, str] = {
    "S1": "Утро тела — подъём, завтрак, зал/море как базовый ритуал",
    "S2": "Опора 'я есть' и намерение — 5–10 минут тишины и практики",
    "S3": "Фокусный квант над главным проектом — 60–90 минут глубокой работы",
    "S4": "Шаг к деньгам / рынку — один конкретный шаг к рынку",
    "S5": "Закат / присутствие / девушка — море, закат, контакт с миром",
    "S6": "Вечерняя интеграция и оценка дня — честный взгляд на день",
}


def get_slot_buttons(slot_id: str) -> InlineKeyboardMarkup:
    """
    Создание inline-клавиатуры для слота.

    Args:
        slot_id: Идентификатор слота (S1-S6)

    Returns:
        InlineKeyboardMarkup с кнопками для слота

    Raises:
        KeyError: Если слот не найден
    """
    if slot_id not in SLOT_BUTTONS:
        raise KeyError(f"Slot {slot_id} not found")

    buttons = []
    for text, callback_data in SLOT_BUTTONS[slot_id]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"slot_{slot_id}_{callback_data}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parse_callback_data(callback_data: str) -> tuple[str, str] | None:
    """
    Парсинг callback_data из inline-кнопки.

    Args:
        callback_data: Данные callback в формате "slot_{slot_id}_{choice}"

    Returns:
        Кортеж (slot_id, button_choice) или None если формат неверный
    """
    if not callback_data.startswith("slot_"):
        return None

    parts = callback_data.split("_")
    if len(parts) != 3:
        return None

    slot_id = parts[1]
    button_choice = parts[2]

    if slot_id not in SLOT_BUTTONS:
        return None

    return (slot_id, button_choice)


def is_successful_response(slot_id: str, button_choice: str) -> bool:
    """
    Проверка, является ли ответ успешным для слота.

    Args:
        slot_id: Идентификатор слота (S1-S6)
        button_choice: Выбранная кнопка (success, skip, ideal, normal, noise)

    Returns:
        True если ответ успешный, False иначе
    """
    if slot_id == "S6":
        # Для S6 успешным считается только "ideal"
        return button_choice == "ideal"
    else:
        # Для S1-S5 успешным считается "success"
        return button_choice == "success"


def is_ideal_day(responses: dict[str, str], min_successful_slots: int = 4) -> bool:
    """
    Проверка, был ли день эталонным.

    Логика:
    - S1-S5: минимум min_successful_slots из 5 должны быть выполнены
    - S6: должна быть выбрана кнопка "ideal"

    Args:
        responses: Словарь {slot_id: button_choice} для дня
        min_successful_slots: Минимальное количество успешных слотов из S1-S5

    Returns:
        True если день эталонный, False иначе
    """
    # Проверяем S1-S5
    s1_s5_slots = ["S1", "S2", "S3", "S4", "S5"]
    successful_count = 0

    for slot_id in s1_s5_slots:
        if slot_id in responses:
            button_choice = responses[slot_id]
            if is_successful_response(slot_id, button_choice):
                successful_count += 1

    # Минимум min_successful_slots из 5 должны быть выполнены
    if successful_count < min_successful_slots:
        return False

    # Проверяем S6
    if "S6" not in responses:
        return False

    return is_successful_response("S6", responses["S6"])


def get_slot_description(slot_id: str) -> str:
    """
    Получение описания слота.

    Args:
        slot_id: Идентификатор слота (S1-S6)

    Returns:
        Описание слота

    Raises:
        KeyError: Если слот не найден
    """
    if slot_id not in SLOT_DESCRIPTIONS:
        raise KeyError(f"Slot {slot_id} not found")
    return SLOT_DESCRIPTIONS[slot_id]


def get_all_slot_ids() -> list[str]:
    """
    Получение списка всех идентификаторов слотов.

    Returns:
        Список идентификаторов слотов ["S1", "S2", "S3", "S4", "S5", "S6"]
    """
    return list(SLOT_BUTTONS.keys())

