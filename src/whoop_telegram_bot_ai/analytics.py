"""Аналитика данных WHOOP - вычисление метрик и статистики."""

import logging
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class WhoopAnalytics:
    """Класс для аналитики данных WHOOP."""

    def __init__(self, cycles: list[dict[str, Any]], sleeps: list[dict[str, Any]], workouts: list[dict[str, Any]], journal_entries: list[dict[str, Any]]):
        """
        Инициализация аналитики.

        Args:
            cycles: Список данных циклов
            sleeps: Список данных сна
            workouts: Список данных тренировок
            journal_entries: Список журнальных записей
        """
        self.cycles = cycles
        self.sleeps = sleeps
        self.workouts = workouts
        self.journal_entries = journal_entries

    def get_weekly_stats(self, start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
        """
        Получение статистики за неделю.

        Args:
            start_date: Начальная дата (по умолчанию 7 дней назад)
            end_date: Конечная дата (по умолчанию сегодня)

        Returns:
            Словарь со статистикой
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        # Фильтруем данные по датам
        filtered_cycles = self._filter_by_date_range(self.cycles, start_date, end_date, "cycle_start")
        filtered_sleeps = self._filter_by_date_range(self.sleeps, start_date, end_date, "sleep_onset")
        filtered_workouts = self._filter_by_date_range(self.workouts, start_date, end_date, "workout_start")
        filtered_journal = self._filter_by_date_range(self.journal_entries, start_date, end_date, "cycle_start")

        # Вычисляем метрики
        stats = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days,
            },
            "recovery": self._calculate_recovery_stats(filtered_cycles),
            "sleep": self._calculate_sleep_stats(filtered_sleeps),
            "strain": self._calculate_strain_stats(filtered_cycles),
            "workouts": self._calculate_workout_stats(filtered_workouts),
            "caffeine": self._calculate_caffeine_stats(filtered_journal),
            "trends": self._calculate_trends(filtered_cycles),
        }

        return stats

    def get_patterns(self) -> dict[str, Any]:
        """
        Анализ паттернов и корреляций.

        Returns:
            Словарь с обнаруженными паттернами
        """
        patterns = {
            "recovery_patterns": self._analyze_recovery_patterns(),
            "sleep_patterns": self._analyze_sleep_patterns(),
            "caffeine_impact": self._analyze_caffeine_impact(),
            "workout_timing": self._analyze_workout_timing(),
            "correlations": self._analyze_correlations(),
        }
        return patterns

    def _filter_by_date_range(
        self, data: list[dict[str, Any]], start_date: date, end_date: date, date_field: str
    ) -> list[dict[str, Any]]:
        """Фильтрация данных по диапазону дат."""
        filtered = []
        for item in data:
            dt = item.get(date_field)
            if dt is None:
                continue
            if isinstance(dt, datetime):
                item_date = dt.date()
            elif isinstance(dt, date):
                item_date = dt
            else:
                continue

            if start_date <= item_date <= end_date:
                filtered.append(item)
        return filtered

    def _calculate_recovery_stats(self, cycles: list[dict[str, Any]]) -> dict[str, Any]:
        """Вычисление статистики Recovery."""
        recovery_scores = [c["recovery_score"] for c in cycles if c.get("recovery_score") is not None]
        hrv_values = [c["hrv"] for c in cycles if c.get("hrv") is not None]
        rhr_values = [c["resting_heart_rate"] for c in cycles if c.get("resting_heart_rate") is not None]

        if not recovery_scores:
            return {"avg": None, "min": None, "max": None, "trend": None}

        avg_recovery = sum(recovery_scores) / len(recovery_scores)
        min_recovery = min(recovery_scores)
        max_recovery = max(recovery_scores)

        # Определяем тренд (рост/падение)
        if len(recovery_scores) >= 2:
            first_half = recovery_scores[: len(recovery_scores) // 2]
            second_half = recovery_scores[len(recovery_scores) // 2 :]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            trend = "up" if avg_second > avg_first else "down" if avg_second < avg_first else "stable"
        else:
            trend = None

        return {
            "avg": round(avg_recovery, 1),
            "min": round(min_recovery, 1),
            "max": round(max_recovery, 1),
            "trend": trend,
            "avg_hrv": round(sum(hrv_values) / len(hrv_values), 1) if hrv_values else None,
            "avg_rhr": round(sum(rhr_values) / len(rhr_values), 1) if rhr_values else None,
        }

    def _calculate_sleep_stats(self, sleeps: list[dict[str, Any]]) -> dict[str, Any]:
        """Вычисление статистики сна."""
        # Фильтруем только ночной сон (не дневной)
        night_sleeps = [s for s in sleeps if not s.get("is_nap", False)]

        if not night_sleeps:
            return {"avg_duration": None, "avg_efficiency": None, "avg_consistency": None}

        durations = [s["asleep_duration"] for s in night_sleeps if s.get("asleep_duration") is not None]
        efficiencies = [s["sleep_efficiency"] for s in night_sleeps if s.get("sleep_efficiency") is not None]
        consistencies = [s["sleep_consistency"] for s in night_sleeps if s.get("sleep_consistency") is not None]
        deep_sleeps = [s["deep_sleep"] for s in night_sleeps if s.get("deep_sleep") is not None]
        rem_sleeps = [s["rem_sleep"] for s in night_sleeps if s.get("rem_sleep") is not None]

        return {
            "avg_duration_hours": round(sum(durations) / len(durations) / 60, 1) if durations else None,
            "avg_efficiency": round(sum(efficiencies) / len(efficiencies), 1) if efficiencies else None,
            "avg_consistency": round(sum(consistencies) / len(consistencies), 1) if consistencies else None,
            "avg_deep_sleep": round(sum(deep_sleeps) / len(deep_sleeps), 1) if deep_sleeps else None,
            "avg_rem_sleep": round(sum(rem_sleeps) / len(rem_sleeps), 1) if rem_sleeps else None,
        }

    def _calculate_strain_stats(self, cycles: list[dict[str, Any]]) -> dict[str, Any]:
        """Вычисление статистики Strain."""
        strains = [c["day_strain"] for c in cycles if c.get("day_strain") is not None]

        if not strains:
            return {"avg": None, "max": None}

        return {
            "avg": round(sum(strains) / len(strains), 1),
            "max": round(max(strains), 1),
        }

    def _calculate_workout_stats(self, workouts: list[dict[str, Any]]) -> dict[str, Any]:
        """Вычисление статистики тренировок."""
        if not workouts:
            return {"count": 0, "avg_strain": None, "total_energy": None}

        strains = [w["activity_strain"] for w in workouts if w.get("activity_strain") is not None]
        energies = [w["energy_burned"] for w in workouts if w.get("energy_burned") is not None]

        return {
            "count": len(workouts),
            "avg_strain": round(sum(strains) / len(strains), 1) if strains else None,
            "total_energy": round(sum(energies), 0) if energies else None,
        }

    def _calculate_caffeine_stats(self, journal_entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Вычисление статистики кофеина."""
        caffeine_entries = [e for e in journal_entries if "caffeine" in e.get("question", "").lower()]

        if not caffeine_entries:
            return {"days_with": 0, "days_without": 0, "total_days": 0}

        days_with = sum(1 for e in caffeine_entries if e.get("answered_yes", False))
        days_without = len(caffeine_entries) - days_with

        return {
            "days_with": days_with,
            "days_without": days_without,
            "total_days": len(caffeine_entries),
        }

    def _calculate_trends(self, cycles: list[dict[str, Any]]) -> dict[str, Any]:
        """Вычисление трендов."""
        if len(cycles) < 2:
            return {"recovery": None, "hrv": None}

        recovery_scores = [c["recovery_score"] for c in cycles if c.get("recovery_score") is not None]
        hrv_values = [c["hrv"] for c in cycles if c.get("hrv") is not None]

        recovery_trend = None
        if len(recovery_scores) >= 2:
            first_half = recovery_scores[: len(recovery_scores) // 2]
            second_half = recovery_scores[len(recovery_scores) // 2 :]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            recovery_trend = "up" if avg_second > avg_first else "down" if avg_second < avg_first else "stable"

        hrv_trend = None
        if len(hrv_values) >= 2:
            first_half = hrv_values[: len(hrv_values) // 2]
            second_half = hrv_values[len(hrv_values) // 2 :]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            hrv_trend = "up" if avg_second > avg_first else "down" if avg_second < avg_first else "stable"

        return {
            "recovery": recovery_trend,
            "hrv": hrv_trend,
        }

    def _analyze_recovery_patterns(self) -> dict[str, Any]:
        """Анализ паттернов Recovery."""
        high_recovery = [c for c in self.cycles if c.get("recovery_score") is not None and c.get("recovery_score", 0) >= 70]
        low_recovery = [c for c in self.cycles if c.get("recovery_score") is not None and c.get("recovery_score", 0) < 50]

        high_recovery_hrv = [c["hrv"] for c in high_recovery if c.get("hrv") is not None]
        low_recovery_hrv = [c["hrv"] for c in low_recovery if c.get("hrv") is not None]

        high_recovery_deep = [c["deep_sleep"] for c in high_recovery if c.get("deep_sleep") is not None]
        low_recovery_deep = [c["deep_sleep"] for c in low_recovery if c.get("deep_sleep") is not None]

        return {
            "high_recovery_count": len(high_recovery),
            "low_recovery_count": len(low_recovery),
            "high_recovery_avg_hrv": round(sum(high_recovery_hrv) / len(high_recovery_hrv), 1) if high_recovery_hrv else None,
            "low_recovery_avg_hrv": round(sum(low_recovery_hrv) / len(low_recovery_hrv), 1) if low_recovery_hrv else None,
            "high_recovery_avg_deep": round(sum(high_recovery_deep) / len(high_recovery_deep), 1) if high_recovery_deep else None,
            "low_recovery_avg_deep": round(sum(low_recovery_deep) / len(low_recovery_deep), 1) if low_recovery_deep else None,
        }

    def _analyze_sleep_patterns(self) -> dict[str, Any]:
        """Анализ паттернов сна."""
        night_sleeps = [s for s in self.sleeps if not s.get("is_nap", False)]
        if not night_sleeps:
            return {}

        sleep_debts = [s["sleep_debt"] for s in night_sleeps if s.get("sleep_debt") is not None]
        efficiencies = [s["sleep_efficiency"] for s in night_sleeps if s.get("sleep_efficiency") is not None]

        return {
            "avg_sleep_debt": round(sum(sleep_debts) / len(sleep_debts), 0) if sleep_debts else None,
            "avg_efficiency": round(sum(efficiencies) / len(efficiencies), 1) if efficiencies else None,
        }

    def _analyze_caffeine_impact(self) -> dict[str, Any]:
        """Анализ влияния кофеина."""
        # Группируем дни с кофеином и без
        caffeine_days = set()
        no_caffeine_days = set()

        for entry in self.journal_entries:
            if "caffeine" not in entry.get("question", "").lower():
                continue
            cycle_start = entry.get("cycle_start")
            if cycle_start is None:
                continue
            if isinstance(cycle_start, datetime):
                day = cycle_start.date()
            else:
                day = cycle_start

            if entry.get("answered_yes", False):
                caffeine_days.add(day)
            else:
                no_caffeine_days.add(day)

        # Находим соответствующие данные сна
        caffeine_sleeps = []
        no_caffeine_sleeps = []

        for sleep in self.sleeps:
            if sleep.get("is_nap", False):
                continue
            sleep_onset = sleep.get("sleep_onset")
            if sleep_onset is None:
                continue
            if isinstance(sleep_onset, datetime):
                day = sleep_onset.date()
            else:
                day = sleep_onset

            if day in caffeine_days:
                caffeine_sleeps.append(sleep)
            elif day in no_caffeine_days:
                no_caffeine_sleeps.append(sleep)

        caffeine_efficiencies = [s["sleep_efficiency"] for s in caffeine_sleeps if s.get("sleep_efficiency") is not None]
        no_caffeine_efficiencies = [s["sleep_efficiency"] for s in no_caffeine_sleeps if s.get("sleep_efficiency") is not None]

        return {
            "caffeine_days_count": len(caffeine_days),
            "no_caffeine_days_count": len(no_caffeine_days),
            "caffeine_avg_efficiency": round(sum(caffeine_efficiencies) / len(caffeine_efficiencies), 1) if caffeine_efficiencies else None,
            "no_caffeine_avg_efficiency": round(sum(no_caffeine_efficiencies) / len(no_caffeine_efficiencies), 1) if no_caffeine_efficiencies else None,
        }

    def _analyze_workout_timing(self) -> dict[str, Any]:
        """Анализ времени тренировок."""
        if not self.workouts:
            return {}

        morning_workouts = []
        evening_workouts = []

        for workout in self.workouts:
            workout_start = workout.get("workout_start")
            if workout_start is None:
                continue
            if isinstance(workout_start, datetime):
                hour = workout_start.hour
            else:
                continue

            if 6 <= hour < 12:
                morning_workouts.append(workout)
            elif 17 <= hour < 22:
                evening_workouts.append(workout)

        return {
            "morning_count": len(morning_workouts),
            "evening_count": len(evening_workouts),
        }

    def _analyze_correlations(self) -> dict[str, Any]:
        """Анализ корреляций между метриками."""
        # Простой анализ корреляций на основе группировки
        correlations = {}

        # Recovery ↔ HRV
        high_hrv_cycles = [c for c in self.cycles if c.get("hrv") is not None and c.get("hrv", 0) > 50]
        low_hrv_cycles = [c for c in self.cycles if c.get("hrv") is not None and c.get("hrv", 0) < 45]

        high_hrv_recovery = [c["recovery_score"] for c in high_hrv_cycles if c.get("recovery_score") is not None]
        low_hrv_recovery = [c["recovery_score"] for c in low_hrv_cycles if c.get("recovery_score") is not None]

        if high_hrv_recovery and low_hrv_recovery:
            correlations["hrv_recovery"] = {
                "high_hrv_avg_recovery": round(sum(high_hrv_recovery) / len(high_hrv_recovery), 1),
                "low_hrv_avg_recovery": round(sum(low_hrv_recovery) / len(low_hrv_recovery), 1),
            }

        return correlations

