"""Система персонализированных рекомендаций на основе паттернов WHOOP."""

import logging
from datetime import date, datetime, timedelta
from typing import Any

from whoop_telegram_bot_ai.analytics import WhoopAnalytics
from whoop_telegram_bot_ai.llm_client import LLMClient

logger = logging.getLogger(__name__)


class RecommendationsGenerator:
    """Генератор персонализированных рекомендаций."""

    def __init__(self, analytics: WhoopAnalytics, llm_client: LLMClient):
        """
        Инициализация генератора рекомендаций.

        Args:
            analytics: Экземпляр WhoopAnalytics
            llm_client: Экземпляр LLMClient для генерации рекомендаций
        """
        self.analytics = analytics
        self.llm_client = llm_client

    async def generate_recommendations(self) -> str:
        """
        Генерация персонализированных рекомендаций на основе текущей ситуации.

        Returns:
            Сгенерированные рекомендации
        """
        # Получаем данные за последние 3 дня для анализа тренда
        end_date = date.today()
        start_date = end_date - timedelta(days=3)

        recent_stats = self.analytics.get_weekly_stats(start_date, end_date)
        patterns = self.analytics.get_patterns()

        # Получаем последние данные для контекста
        recent_cycles = [c for c in self.analytics.cycles if self._is_recent(c.get("cycle_start"), days=3)]
        recent_workouts = [w for w in self.analytics.workouts if self._is_recent(w.get("workout_start"), days=7)]

        # Формируем промпт для LLM
        prompt = self._build_recommendations_prompt(recent_stats, patterns, recent_cycles, recent_workouts)

        # Генерируем рекомендации через LLM
        try:
            recommendations = await self.llm_client._call_openrouter(prompt, max_retries=3, max_tokens=1500)
            return recommendations if recommendations else self._generate_fallback_recommendations(recent_stats)
        except Exception as e:
            logger.error(f"Failed to generate recommendations via LLM: {e}")
            return self._generate_fallback_recommendations(recent_stats)

    def _is_recent(self, dt: Any, days: int = 3) -> bool:
        """Проверка, является ли дата недавней."""
        if dt is None:
            return False
        if isinstance(dt, datetime):
            item_date = dt.date()
        elif isinstance(dt, date):
            item_date = dt
        else:
            return False

        return (date.today() - item_date).days <= days

    def _build_recommendations_prompt(
        self,
        recent_stats: dict[str, Any],
        patterns: dict[str, Any],
        recent_cycles: list[dict[str, Any]],
        recent_workouts: list[dict[str, Any]],
    ) -> str:
        """
        Построение промпта для рекомендаций.

        Args:
            recent_stats: Статистика за последние дни
            patterns: Обнаруженные паттерны
            recent_cycles: Последние циклы
            recent_workouts: Последние тренировки

        Returns:
            Промпт для LLM
        """
        recovery = recent_stats.get("recovery", {})
        sleep = recent_stats.get("sleep", {})
        trends = recent_stats.get("trends", {})

        # Вычисляем текущие показатели
        current_recovery = None
        current_sleep_debt = None
        current_hrv = None
        baseline_hrv = None

        if recent_cycles:
            latest_cycle = recent_cycles[0]
            current_recovery = latest_cycle.get("recovery_score")
            current_sleep_debt = latest_cycle.get("sleep_debt")
            current_hrv = latest_cycle.get("hrv")

        # Вычисляем baseline HRV из паттернов
        recovery_patterns = patterns.get("recovery_patterns", {})
        if recovery_patterns.get("high_recovery_avg_hrv"):
            baseline_hrv = recovery_patterns["high_recovery_avg_hrv"]

        # Информация о последней тренировке
        last_workout_days_ago = None
        last_workout_strain = None
        if recent_workouts:
            last_workout = recent_workouts[0]
            workout_start = last_workout.get("workout_start")
            if workout_start:
                if isinstance(workout_start, datetime):
                    days_ago = (date.today() - workout_start.date()).days
                else:
                    days_ago = (date.today() - workout_start).days
                last_workout_days_ago = days_ago
                last_workout_strain = last_workout.get("activity_strain")

        prompt = f"""Текущая ситуация:

**Recovery последние 3 дня:**
- Средний Recovery: {recovery.get('avg', 'N/A')}%
- Тренд: {recovery.get('trend', 'N/A')}
- Текущий Recovery: {current_recovery if current_recovery is not None else 'N/A'}%

**Сон:**
- Sleep debt: {current_sleep_debt if current_sleep_debt is not None else 'N/A'} минут
- Средняя эффективность: {sleep.get('avg_efficiency', 'N/A')}%

**HRV:**
- Текущий HRV: {current_hrv if current_hrv is not None else 'N/A'}ms
- Baseline HRV (при высоком Recovery): {baseline_hrv if baseline_hrv else 'N/A'}ms

**Тренировки:**
- Последняя тренировка: {last_workout_days_ago if last_workout_days_ago is not None else 'N/A'} дней назад
- Strain последней тренировки: {last_workout_strain if last_workout_strain is not None else 'N/A'}

**Тренды:**
- Recovery тренд: {trends.get('recovery', 'N/A')}
- HRV тренд: {trends.get('hrv', 'N/A')}

Создай персонализированную рекомендацию на основе текущей ситуации:

1. **Что делать прямо сейчас для улучшения Recovery?** (3-4 предложения)
   - Немедленные действия
   - Ритуалы восстановления
   - Оптимизация текущего состояния

2. **Как оптимизировать сон сегодня?** (3-4 предложения)
   - Рекомендации по режиму сна
   - Оптимальное время отхода ко сну
   - Подготовка ко сну

3. **Когда лучше планировать следующую тренировку?** (2-3 предложения)
   - Оптимальное время для тренировки
   - Рекомендуемая интенсивность
   - Условия для безопасной нагрузки

4. **Какие ритуалы помогут восстановлению?** (3-4 предложения)
   - Ежедневные практики
   - Долгосрочные стратегии
   - Интеграция в текущий режим

Используй принципы программирования подсознания:
- Позитивные утверждения в настоящем времени
- Визуализация успешного восстановления
- Конкретные образы оптимального состояния
- Связь действий с улучшением показателей

**Важно:**
- Пиши по-русски, тепло и уверенно
- Избегай избыточных эмодзи и форматирования (не используй S1, S2, S3 и т.д.)
- Фокусируйся на здоровье, энергии и восстановлении
- Будь конкретным и практичным в рекомендациях"""

        return prompt

    def _generate_fallback_recommendations(self, recent_stats: dict[str, Any]) -> str:
        """
        Генерация fallback рекомендаций без LLM.

        Args:
            recent_stats: Статистика за последние дни

        Returns:
            Базовые рекомендации
        """
        recovery = recent_stats.get("recovery", {})
        trend = recovery.get("trend", "stable")

        if trend == "down":
            return "⚠️ Recovery показывает тенденцию к снижению. Рекомендуется увеличить время восстановления, оптимизировать сон и снизить нагрузку."
        elif trend == "up":
            return "✅ Recovery показывает положительную тенденцию! Продолжай текущий режим и отслеживай показатели."
        else:
            return "📊 Recovery стабилен. Продолжай отслеживать показатели и оптимизировать режим для лучшего восстановления."

