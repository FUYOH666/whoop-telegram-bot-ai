"""Предсказательная аналитика для Recovery и других метрик WHOOP."""

import logging
from datetime import date, datetime, timedelta
from typing import Any

from whoop_telegram_bot_ai.analytics import WhoopAnalytics
from whoop_telegram_bot_ai.llm_client import LLMClient

logger = logging.getLogger(__name__)


class RecoveryPredictor:
    """Предиктор Recovery на основе исторических данных."""

    def __init__(self, analytics: WhoopAnalytics, llm_client: LLMClient):
        """
        Инициализация предиктора.

        Args:
            analytics: Экземпляр WhoopAnalytics
            llm_client: Экземпляр LLMClient для генерации предсказаний
        """
        self.analytics = analytics
        self.llm_client = llm_client

    async def predict_recovery(self) -> str:
        """
        Предсказание Recovery на завтра на основе текущих показателей.

        Returns:
            Предсказание и рекомендации
        """
        # Получаем текущие показатели
        today = date.today()
        recent_stats = self.analytics.get_weekly_stats(today - timedelta(days=7), today)
        patterns = self.analytics.get_patterns()

        # Находим последний цикл
        latest_cycle = None
        if self.analytics.cycles:
            latest_cycle = self.analytics.cycles[0]

        # Анализируем исторические паттерны для предсказания
        prediction_data = self._analyze_prediction_patterns(latest_cycle, patterns)

        # Формируем промпт для LLM
        prompt = self._build_prediction_prompt(prediction_data, latest_cycle)

        # Генерируем предсказание через LLM
        try:
            prediction = await self.llm_client._call_openrouter(prompt, max_retries=3, max_tokens=1500)
            return prediction if prediction else self._generate_fallback_prediction(prediction_data)
        except Exception as e:
            logger.error(f"Failed to predict recovery via LLM: {e}")
            return self._generate_fallback_prediction(prediction_data)

    def _analyze_prediction_patterns(self, latest_cycle: dict[str, Any] | None, patterns: dict[str, Any]) -> dict[str, Any]:
        """
        Анализ паттернов для предсказания.

        Args:
            latest_cycle: Последний цикл
            patterns: Обнаруженные паттерны

        Returns:
            Данные для предсказания
        """
        prediction_data = {
            "current_sleep_debt": latest_cycle.get("sleep_debt") if latest_cycle else None,
            "current_hrv": latest_cycle.get("hrv") if latest_cycle else None,
            "current_recovery": latest_cycle.get("recovery_score") if latest_cycle else None,
            "baseline_hrv": None,
            "predicted_recovery": None,
        }

        # Определяем baseline HRV
        recovery_patterns = patterns.get("recovery_patterns", {})
        if recovery_patterns.get("high_recovery_avg_hrv"):
            prediction_data["baseline_hrv"] = recovery_patterns["high_recovery_avg_hrv"]

        # Простое предсказание на основе паттернов
        current_debt = prediction_data["current_sleep_debt"]
        current_hrv = prediction_data["current_hrv"]
        baseline_hrv = prediction_data["baseline_hrv"]

        if current_debt is not None and current_hrv is not None and baseline_hrv is not None:
            # Эвристика: если sleep debt низкий и HRV близок к baseline, Recovery будет высоким
            if current_debt < 50 and current_hrv >= baseline_hrv * 0.9:
                prediction_data["predicted_recovery"] = "high"  # >70%
            elif current_debt > 100 or current_hrv < baseline_hrv * 0.8:
                prediction_data["predicted_recovery"] = "low"  # <50%
            else:
                prediction_data["predicted_recovery"] = "medium"  # 50-70%

        return prediction_data

    def _build_prediction_prompt(self, prediction_data: dict[str, Any], latest_cycle: dict[str, Any] | None) -> str:
        """
        Построение промпта для предсказания.

        Args:
            prediction_data: Данные для предсказания
            latest_cycle: Последний цикл

        Returns:
            Промпт для LLM
        """
        current_debt = prediction_data.get("current_sleep_debt")
        current_hrv = prediction_data.get("current_hrv")
        baseline_hrv = prediction_data.get("baseline_hrv")
        current_recovery = prediction_data.get("current_recovery")
        predicted_level = prediction_data.get("predicted_recovery")

        prompt = f"""На основе исторических данных и текущих показателей:

**Исторические паттерны:**
- Когда Sleep debt < 50min и HRV близок к baseline ({baseline_hrv if baseline_hrv else 'N/A'}ms): Recovery обычно высокий (>70%)
- Когда Sleep debt > 100min или HRV значительно ниже baseline: Recovery обычно низкий (<50%)

**Текущие показатели:**
- Sleep debt: {current_debt if current_debt is not None else 'N/A'} минут
- HRV сегодня: {current_hrv if current_hrv is not None else 'N/A'}ms
- Baseline HRV: {baseline_hrv if baseline_hrv else 'N/A'}ms
- Последний Recovery: {current_recovery if current_recovery is not None else 'N/A'}%

**Предварительная оценка:** Recovery на завтра ожидается {predicted_level if predicted_level else 'средний'}

Создай предсказание и рекомендации:

1. **Предсказание Recovery на завтра** (2-3 предложения)
   - Ожидаемый уровень Recovery
   - Факторы, влияющие на предсказание
   - Уверенность в предсказании

2. **Рекомендации для улучшения Recovery** (4-5 предложений)
   - Что сделать сегодня для улучшения Recovery на завтра?
   - Оптимальные действия для восстановления
   - Ритуалы и практики

3. **Оптимизация сна сегодня** (3-4 предложения)
   - Когда лучше лечь спать?
   - Как подготовиться ко сну?
   - Что поможет улучшить качество сна?

4. **Планирование на завтра** (2-3 предложения)
   - Рекомендации по нагрузке
   - Оптимальное время для активности
   - Что учесть при планировании дня?

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

    def _generate_fallback_prediction(self, prediction_data: dict[str, Any]) -> str:
        """
        Генерация fallback предсказания без LLM.

        Args:
            prediction_data: Данные для предсказания

        Returns:
            Базовое предсказание
        """
        current_debt = prediction_data.get("current_sleep_debt")
        predicted_level = prediction_data.get("predicted_recovery")

        if predicted_level == "high":
            return f"✅ На основе текущих показателей (Sleep debt: {current_debt if current_debt else 'N/A'}min), Recovery на завтра ожидается высоким. Продолжай текущий режим!"
        elif predicted_level == "low":
            return f"⚠️ На основе текущих показателей (Sleep debt: {current_debt if current_debt else 'N/A'}min), Recovery на завтра может быть низким. Рекомендуется увеличить время восстановления и оптимизировать сон."
        else:
            return f"📊 Recovery на завтра ожидается средним. Продолжай отслеживать показатели и оптимизировать режим."

