"""Парсер экспортированных данных WHOOP из CSV файлов."""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WhoopExportParser:
    """Парсер экспортированных данных WHOOP."""

    def __init__(self, export_dir: str | Path):
        """
        Инициализация парсера.

        Args:
            export_dir: Путь к директории с CSV файлами
        """
        self.export_dir = Path(export_dir)
        if not self.export_dir.exists():
            raise ValueError(f"Export directory not found: {export_dir}")

    def parse_physiological_cycles(self) -> list[dict[str, Any]]:
        """
        Парсинг physiological_cycles.csv.

        Returns:
            Список словарей с данными циклов
        """
        csv_path = self.export_dir / "physiological_cycles.csv"
        if not csv_path.exists():
            logger.warning(f"File not found: {csv_path}")
            return []

        cycles = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cycle = self._parse_cycle_row(row)
                    if cycle:
                        cycles.append(cycle)
            logger.info(f"Parsed {len(cycles)} physiological cycles")
            return cycles
        except Exception as e:
            logger.error(f"Failed to parse physiological_cycles.csv: {e}")
            return []

    def parse_sleeps(self) -> list[dict[str, Any]]:
        """
        Парсинг sleeps.csv.

        Returns:
            Список словарей с данными сна
        """
        csv_path = self.export_dir / "sleeps.csv"
        if not csv_path.exists():
            logger.warning(f"File not found: {csv_path}")
            return []

        sleeps = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sleep = self._parse_sleep_row(row)
                    if sleep:
                        sleeps.append(sleep)
            logger.info(f"Parsed {len(sleeps)} sleep records")
            return sleeps
        except Exception as e:
            logger.error(f"Failed to parse sleeps.csv: {e}")
            return []

    def parse_workouts(self) -> list[dict[str, Any]]:
        """
        Парсинг workouts.csv.

        Returns:
            Список словарей с данными тренировок
        """
        csv_path = self.export_dir / "workouts.csv"
        if not csv_path.exists():
            logger.warning(f"File not found: {csv_path}")
            return []

        workouts = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    workout = self._parse_workout_row(row)
                    if workout:
                        workouts.append(workout)
            logger.info(f"Parsed {len(workouts)} workout records")
            return workouts
        except Exception as e:
            logger.error(f"Failed to parse workouts.csv: {e}")
            return []

    def parse_journal_entries(self) -> list[dict[str, Any]]:
        """
        Парсинг journal_entries.csv.

        Returns:
            Список словарей с журнальными записями
        """
        csv_path = self.export_dir / "journal_entries.csv"
        if not csv_path.exists():
            logger.warning(f"File not found: {csv_path}")
            return []

        entries = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    entry = self._parse_journal_row(row)
                    if entry:
                        entries.append(entry)
            logger.info(f"Parsed {len(entries)} journal entries")
            return entries
        except Exception as e:
            logger.error(f"Failed to parse journal_entries.csv: {e}")
            return []

    def parse_all(self) -> dict[str, list[dict[str, Any]]]:
        """
        Парсинг всех CSV файлов.

        Returns:
            Словарь с данными всех типов
        """
        return {
            "cycles": self.parse_physiological_cycles(),
            "sleeps": self.parse_sleeps(),
            "workouts": self.parse_workouts(),
            "journal_entries": self.parse_journal_entries(),
        }

    def _parse_cycle_row(self, row: dict[str, str]) -> dict[str, Any] | None:
        """Парсинг строки physiological_cycles."""
        try:
            cycle = {
                "cycle_start": self._parse_datetime(row.get("Cycle start time", "")),
                "cycle_end": self._parse_datetime(row.get("Cycle end time", "")),
                "timezone": row.get("Cycle timezone", ""),
                "recovery_score": self._parse_float(row.get("Recovery score %", "")),
                "resting_heart_rate": self._parse_float(row.get("Resting heart rate (bpm)", "")),
                "hrv": self._parse_float(row.get("Heart rate variability (ms)", "")),
                "skin_temp": self._parse_float(row.get("Skin temp (celsius)", "")),
                "blood_oxygen": self._parse_float(row.get("Blood oxygen %", "")),
                "day_strain": self._parse_float(row.get("Day Strain", "")),
                "energy_burned": self._parse_float(row.get("Energy burned (cal)", "")),
                "max_hr": self._parse_float(row.get("Max HR (bpm)", "")),
                "avg_hr": self._parse_float(row.get("Average HR (bpm)", "")),
                "sleep_onset": self._parse_datetime(row.get("Sleep onset", "")),
                "wake_onset": self._parse_datetime(row.get("Wake onset", "")),
                "sleep_performance": self._parse_float(row.get("Sleep performance %", "")),
                "respiratory_rate": self._parse_float(row.get("Respiratory rate (rpm)", "")),
                "asleep_duration": self._parse_float(row.get("Asleep duration (min)", "")),
                "in_bed_duration": self._parse_float(row.get("In bed duration (min)", "")),
                "light_sleep": self._parse_float(row.get("Light sleep duration (min)", "")),
                "deep_sleep": self._parse_float(row.get("Deep (SWS) duration (min)", "")),
                "rem_sleep": self._parse_float(row.get("REM duration (min)", "")),
                "awake_duration": self._parse_float(row.get("Awake duration (min)", "")),
                "sleep_need": self._parse_float(row.get("Sleep need (min)", "")),
                "sleep_debt": self._parse_float(row.get("Sleep debt (min)", "")),
                "sleep_efficiency": self._parse_float(row.get("Sleep efficiency %", "")),
                "sleep_consistency": self._parse_float(row.get("Sleep consistency %", "")),
            }
            return cycle
        except Exception as e:
            logger.warning(f"Failed to parse cycle row: {e}")
            return None

    def _parse_sleep_row(self, row: dict[str, str]) -> dict[str, Any] | None:
        """Парсинг строки sleeps."""
        try:
            sleep = {
                "cycle_start": self._parse_datetime(row.get("Cycle start time", "")),
                "cycle_end": self._parse_datetime(row.get("Cycle end time", "")),
                "timezone": row.get("Cycle timezone", ""),
                "sleep_onset": self._parse_datetime(row.get("Sleep onset", "")),
                "wake_onset": self._parse_datetime(row.get("Wake onset", "")),
                "sleep_performance": self._parse_float(row.get("Sleep performance %", "")),
                "respiratory_rate": self._parse_float(row.get("Respiratory rate (rpm)", "")),
                "asleep_duration": self._parse_float(row.get("Asleep duration (min)", "")),
                "in_bed_duration": self._parse_float(row.get("In bed duration (min)", "")),
                "light_sleep": self._parse_float(row.get("Light sleep duration (min)", "")),
                "deep_sleep": self._parse_float(row.get("Deep (SWS) duration (min)", "")),
                "rem_sleep": self._parse_float(row.get("REM duration (min)", "")),
                "awake_duration": self._parse_float(row.get("Awake duration (min)", "")),
                "sleep_need": self._parse_float(row.get("Sleep need (min)", "")),
                "sleep_debt": self._parse_float(row.get("Sleep debt (min)", "")),
                "sleep_efficiency": self._parse_float(row.get("Sleep efficiency %", "")),
                "sleep_consistency": self._parse_float(row.get("Sleep consistency %", "")),
                "is_nap": row.get("Nap", "").lower() == "true",
            }
            return sleep
        except Exception as e:
            logger.warning(f"Failed to parse sleep row: {e}")
            return None

    def _parse_workout_row(self, row: dict[str, str]) -> dict[str, Any] | None:
        """Парсинг строки workouts."""
        try:
            workout = {
                "cycle_start": self._parse_datetime(row.get("Cycle start time", "")),
                "cycle_end": self._parse_datetime(row.get("Cycle end time", "")),
                "timezone": row.get("Cycle timezone", ""),
                "workout_start": self._parse_datetime(row.get("Workout start time", "")),
                "workout_end": self._parse_datetime(row.get("Workout end time", "")),
                "duration": self._parse_float(row.get("Duration (min)", "")),
                "activity_strain": self._parse_float(row.get("Activity Strain", "")),
                "energy_burned": self._parse_float(row.get("Energy burned (cal)", "")),
                "max_hr": self._parse_float(row.get("Max HR (bpm)", "")),
                "avg_hr": self._parse_float(row.get("Average HR (bpm)", "")),
                "hr_zone_1": self._parse_float(row.get("HR Zone 1 %", "")),
                "hr_zone_2": self._parse_float(row.get("HR Zone 2 %", "")),
                "hr_zone_3": self._parse_float(row.get("HR Zone 3 %", "")),
                "hr_zone_4": self._parse_float(row.get("HR Zone 4 %", "")),
                "hr_zone_5": self._parse_float(row.get("HR Zone 5 %", "")),
                "gps_enabled": row.get("GPS enabled", "").lower() == "true",
            }
            return workout
        except Exception as e:
            logger.warning(f"Failed to parse workout row: {e}")
            return None

    def _parse_journal_row(self, row: dict[str, str]) -> dict[str, Any] | None:
        """Парсинг строки journal_entries."""
        try:
            entry = {
                "cycle_start": self._parse_datetime(row.get("Cycle start time", "")),
                "cycle_end": self._parse_datetime(row.get("Cycle end time", "")),
                "timezone": row.get("Cycle timezone", ""),
                "question": row.get("Question text", ""),
                "answered_yes": row.get("Answered yes", "").lower() == "true",
                "notes": row.get("Notes", ""),
            }
            return entry
        except Exception as e:
            logger.warning(f"Failed to parse journal row: {e}")
            return None

    def _parse_datetime(self, value: str) -> datetime | None:
        """Парсинг datetime из строки."""
        if not value or value.strip() == "":
            return None
        try:
            # Формат: "2025-11-16 21:25:43"
            return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # Альтернативный формат с timezone
                return datetime.fromisoformat(value.strip().replace("UTC", "").strip())
            except Exception:
                logger.warning(f"Failed to parse datetime: {value}")
                return None

    def _parse_float(self, value: str) -> float | None:
        """Парсинг float из строки."""
        if not value or value.strip() == "":
            return None
        try:
            return float(value.strip())
        except ValueError:
            return None

