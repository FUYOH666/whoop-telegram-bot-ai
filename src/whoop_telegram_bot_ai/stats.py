"""Статистика и аналитика для RAS Bot."""

import logging
from datetime import date, timedelta
from typing import Any

from whoop_telegram_bot_ai.slots import get_all_slot_ids, is_ideal_day

logger = logging.getLogger(__name__)


class StatsCalculator:
    """Калькулятор статистики."""

    def __init__(self, storage: Any, whoop_client: Any = None):
        """
        Инициализация калькулятора.

        Args:
            storage: Экземпляр Storage для доступа к данным
            whoop_client: Экземпляр WhoopClient (опционально)
        """
        self.storage = storage
        self.whoop_client = whoop_client

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

    async def get_context_for_slot(self, slot_id: str, user_id: int | None = None) -> dict[str, Any]:
        """
        Получение контекста для генерации сообщения слота.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            user_id: ID пользователя Telegram (нужен для получения WHOOP данных)

        Returns:
            Словарь с контекстом для LLM:
            {
                "yesterday_status": bool или None,
                "last_7_days_count": int,
                "s1_status": bool (для S6),
                "whoop_recovery": float | None,
                "whoop_sleep": float | None,
                "whoop_strain": float | None,
                "whoop_workouts": int,
                "whoop_recovery_yesterday": float | None (для S1),
                "whoop_sleep_yesterday": float | None (для S2),
                "whoop_strain_today": float | None (для S3-S5),
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

            # Получаем данные WHOOP за сегодня (если доступны)
            if self.whoop_client and user_id:
                try:
                    # Сначала пробуем получить из БД
                    whoop_data = self.storage.get_today_whoop_data()
                    if not whoop_data:
                        # Если данных нет в БД, получаем через API
                        today = date.today()
                        whoop_data_dict = await self.whoop_client.get_all_data(user_id, today)
                        if whoop_data_dict:
                            whoop_data = {
                                "recovery_score": whoop_data_dict.get("recovery_score"),
                                "sleep_duration": whoop_data_dict.get("sleep_duration"),
                                "strain_score": whoop_data_dict.get("strain_score"),
                                "workouts_count": whoop_data_dict.get("workouts_count", 0),
                            }
                    
                    if whoop_data:
                        context["whoop_recovery"] = whoop_data.get("recovery_score")
                        context["whoop_sleep"] = whoop_data.get("sleep_duration")
                        context["whoop_strain"] = whoop_data.get("strain_score")
                        context["whoop_workouts"] = whoop_data.get("workouts_count", 0)
                    else:
                        context["whoop_recovery"] = None
                        context["whoop_sleep"] = None
                        context["whoop_strain"] = None
                        context["whoop_workouts"] = 0
                except Exception as e:
                    logger.warning("Failed to get WHOOP data for S6 context", extra={"error": str(e)})
                    context["whoop_recovery"] = None
                    context["whoop_sleep"] = None
                    context["whoop_strain"] = None
                    context["whoop_workouts"] = 0
            else:
                context["whoop_recovery"] = None
                context["whoop_sleep"] = None
                context["whoop_strain"] = None
                context["whoop_workouts"] = 0
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

            # Получаем WHOOP данные для каждого слота
            if self.whoop_client and user_id:
                try:
                    if slot_id == "S1":
                        # S1: Recovery вчера
                        yesterday_date = date.today() - timedelta(days=1)
                        recovery_data = await self.whoop_client.get_recovery(user_id, yesterday_date)
                        if recovery_data:
                            score = recovery_data.get("score", {})
                            # В v2 API это recovery_score, не recovery_percentage
                            context["whoop_recovery_yesterday"] = score.get("recovery_score") or score.get("recovery_percentage")
                        else:
                            context["whoop_recovery_yesterday"] = None
                    elif slot_id == "S2":
                        # S2: Sleep вчера
                        yesterday_date = date.today() - timedelta(days=1)
                        sleep_data = await self.whoop_client.get_sleep(user_id, yesterday_date)
                        if sleep_data:
                            # WHOOP v2 API: sleep данные в score.stage_summary.total_in_bed_time_milli
                            stage_summary = sleep_data.get("score", {}).get("stage_summary", {})
                            sleep_duration_ms = stage_summary.get("total_in_bed_time_milli", 0)
                            context["whoop_sleep_yesterday"] = sleep_duration_ms / (1000 * 60 * 60) if sleep_duration_ms else None
                        else:
                            context["whoop_sleep_yesterday"] = None
                    elif slot_id in ["S3", "S4", "S5"]:
                        # S3-S5: Strain сегодня (предпочтительно из cycle, fallback на workouts)
                        today = date.today()
                        # Сначала пробуем получить Strain из cycle
                        cycle_data = await self.whoop_client.get_cycle(user_id, today)
                        if cycle_data:
                            strain = cycle_data.get("score", {}).get("strain")
                            if strain is not None:
                                context["whoop_strain_today"] = strain
                            else:
                                # Fallback на workouts
                                workouts = await self.whoop_client.get_workouts(user_id, today)
                                if workouts:
                                    total_strain = sum(
                                        workout.get("score", {}).get("strain", 0)
                                        for workout in workouts
                                    )
                                    context["whoop_strain_today"] = total_strain if total_strain > 0 else None
                                else:
                                    context["whoop_strain_today"] = None
                        else:
                            # Если cycle недоступен, используем workouts
                            workouts = await self.whoop_client.get_workouts(user_id, today)
                            if workouts:
                                total_strain = sum(
                                    workout.get("score", {}).get("strain", 0)
                                    for workout in workouts
                                )
                                context["whoop_strain_today"] = total_strain if total_strain > 0 else None
                            else:
                                context["whoop_strain_today"] = None
                except Exception as e:
                    logger.warning(f"Failed to get WHOOP data for {slot_id} context", extra={"error": str(e)})
                    # Устанавливаем None для всех WHOOP полей этого слота
                    if slot_id == "S1":
                        context["whoop_recovery_yesterday"] = None
                    elif slot_id == "S2":
                        context["whoop_sleep_yesterday"] = None
                    elif slot_id in ["S3", "S4", "S5"]:
                        context["whoop_strain_today"] = None
            else:
                # WHOOP не настроен или user_id не указан
                if slot_id == "S1":
                    context["whoop_recovery_yesterday"] = None
                elif slot_id == "S2":
                    context["whoop_sleep_yesterday"] = None
                elif slot_id in ["S3", "S4", "S5"]:
                    context["whoop_strain_today"] = None

        return context

