"""Статистика и аналитика для RAS Bot."""

import logging
from datetime import date, timedelta
from typing import Any

from ras_bot.slots import get_all_slot_ids, is_ideal_day

logger = logging.getLogger(__name__)


class StatsCalculator:
    """Калькулятор статистики."""

    def __init__(self, storage: Any):
        """
        Инициализация калькулятора.

        Args:
            storage: Экземпляр Storage для доступа к данным
        """
        self.storage = storage

    def calculate_statistics(self, days: int = 7) -> dict[str, Any]:
        """
        Расчет статистики за указанный период.

        Args:
            days: Количество дней для анализа

        Returns:
            Словарь со статистикой:
            {
                "period_days": количество дней,
                "slots": {
                    "S1": {"total": 7, "successful": 6, "percentage": 85.7},
                    ...
                },
                "ideal_days": 4,
                "weakest_slot": "S4"
            }
        """
        slot_ids = get_all_slot_ids()
        slots_stats = {}

        for slot_id in slot_ids:
            stats = self.storage.get_slot_statistics(slot_id, days)
            slots_stats[slot_id] = stats

        ideal_days = self.storage.get_ideal_days_count(days)
        weakest_slot = self._get_weakest_slot(slots_stats)

        return {
            "period_days": days,
            "slots": slots_stats,
            "ideal_days": ideal_days,
            "weakest_slot": weakest_slot,
        }

    def _get_weakest_slot(self, slots_stats: dict[str, Any]) -> str | None:
        """
        Определение самого слабого слота (наименьший процент успешных выполнений).

        Args:
            slots_stats: Словарь со статистикой по слотам

        Returns:
            Идентификатор самого слабого слота или None если данных нет
        """
        # Исключаем S6 из анализа слабого звена, так как у него другая логика
        s1_s5_slots = ["S1", "S2", "S3", "S4", "S5"]

        weakest_slot = None
        min_percentage = 100.0

        for slot_id in s1_s5_slots:
            if slot_id in slots_stats:
                stats = slots_stats[slot_id]
                if stats["total"] > 0:
                    percentage = stats["percentage"]
                    if percentage < min_percentage:
                        min_percentage = percentage
                        weakest_slot = slot_id

        return weakest_slot

    def format_stats_message(self, stats: dict[str, Any]) -> str:
        """
        Форматирование статистики для отправки пользователю.

        Args:
            stats: Словарь со статистикой от calculate_statistics

        Returns:
            Отформатированное сообщение со статистикой
        """
        period_days = stats["period_days"]
        slots_stats = stats["slots"]
        ideal_days = stats["ideal_days"]
        weakest_slot = stats["weakest_slot"]

        # Названия слотов для красивого вывода
        slot_names = {
            "S1": "Утро тела",
            "S2": "Опора 'я есть'",
            "S3": "Фокус-квант",
            "S4": "Шаг к деньгам",
            "S5": "Закат/присутствие",
            "S6": "Оценка дня",
        }

        lines = [f"📊 Статистика за {period_days} дней:\n"]

        # Статистика по каждому слоту
        for slot_id in ["S1", "S2", "S3", "S4", "S5"]:
            if slot_id in slots_stats:
                slot_stat = slots_stats[slot_id]
                name = slot_names.get(slot_id, slot_id)
                total = slot_stat["total"]
                successful = slot_stat["successful"]
                percentage = slot_stat["percentage"]

                if total > 0:
                    bar_length = int(percentage / 10)
                    bar = "█" * bar_length + "░" * (10 - bar_length)
                    lines.append(
                        f"{name}: {successful}/{total} ({percentage:.1f}%) {bar}"
                    )
                else:
                    lines.append(f"{name}: нет данных")

        # Статистика эталонных дней
        lines.append(f"\n✨ Эталонных дней: {ideal_days}/{period_days}")

        # Слабое звено
        if weakest_slot:
            weakest_name = slot_names.get(weakest_slot, weakest_slot)
            weakest_percentage = slots_stats[weakest_slot]["percentage"]
            lines.append(
                f"\n💡 Слабое звено: {weakest_name} ({weakest_percentage:.1f}%)"
            )

        return "\n".join(lines)

    def get_context_for_slot(self, slot_id: str) -> dict[str, Any]:
        """
        Получение контекста для генерации сообщения слота.

        Args:
            slot_id: Идентификатор слота (S1-S6)

        Returns:
            Словарь с контекстом для LLM:
            {
                "yesterday_status": bool или None,
                "last_7_days_count": int,
                "s1_status": bool (для S6),
                ...
            }
        """
        context: dict[str, Any] = {}

        # Получаем вчерашние ответы
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        yesterday_responses = self.storage.get_day_responses(yesterday)

        if slot_id == "S6":
            # Для S6 нужны статусы всех предыдущих слотов
            today_responses = self.storage.get_day_responses()
            for i in range(1, 6):
                s_id = f"S{i}"
                if s_id in today_responses:
                    button_choice = today_responses[s_id]
                    # Определяем успешность по кнопке
                    context[f"s{i}_status"] = (
                        "success" in button_choice.lower()
                        or "✅" in button_choice
                        or "🚀" in button_choice
                        or "💰" in button_choice
                        or "🧘" in button_choice
                        or "🌅" in button_choice
                        or "был" in button_choice.lower()
                        or "сделал" in button_choice.lower()
                        or "была" in button_choice.lower()
                    )
                else:
                    context[f"s{i}_status"] = False
        else:
            # Для остальных слотов нужен статус вчерашнего дня
            if slot_id in yesterday_responses:
                button_choice = yesterday_responses[slot_id]
                context["yesterday_status"] = (
                    "success" in button_choice.lower()
                    or "✅" in button_choice
                    or "🚀" in button_choice
                    or "💰" in button_choice
                    or "🧘" in button_choice
                    or "🌅" in button_choice
                    or "был" in button_choice.lower()
                    or "сделал" in button_choice.lower()
                    or "была" in button_choice.lower()
                )
            else:
                context["yesterday_status"] = None

            # Количество выполнений за последние 7 дней
            stats = self.storage.get_slot_statistics(slot_id, 7)
            context["last_7_days_count"] = stats["successful"]

        return context

