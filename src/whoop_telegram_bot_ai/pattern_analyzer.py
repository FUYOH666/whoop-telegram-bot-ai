"""Анализ паттернов и корреляций между метриками WHOOP."""

import logging
from typing import Any

from whoop_telegram_bot_ai.analytics import WhoopAnalytics
from whoop_telegram_bot_ai.llm_client import LLMClient

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """Анализатор паттернов и корреляций."""

    def __init__(self, analytics: WhoopAnalytics, llm_client: LLMClient):
        """
        Инициализация анализатора.

        Args:
            analytics: Экземпляр WhoopAnalytics
            llm_client: Экземпляр LLMClient для генерации анализа
        """
        self.analytics = analytics
        self.llm_client = llm_client

    async def analyze_patterns(self) -> str:
        """
        Анализ паттернов и корреляций через LLM.

        Returns:
            Сгенерированный анализ паттернов
        """
        # Получаем паттерны
        patterns = self.analytics.get_patterns()

        # Формируем промпт для LLM
        prompt = self._build_pattern_analysis_prompt(patterns)

        # Генерируем анализ через LLM
        try:
            analysis = await self.llm_client._call_openrouter(prompt, max_retries=3, max_tokens=1500)
            return analysis if analysis else self._generate_fallback_analysis(patterns)
        except Exception as e:
            logger.error(f"Failed to analyze patterns via LLM: {e}")
            return self._generate_fallback_analysis(patterns)

    def _build_pattern_analysis_prompt(self, patterns: dict[str, Any]) -> str:
        """
        Построение промпта для анализа паттернов.

        Args:
            patterns: Обнаруженные паттерны

        Returns:
            Промпт для LLM
        """
        recovery_patterns = patterns.get("recovery_patterns", {})
        sleep_patterns = patterns.get("sleep_patterns", {})
        caffeine_impact = patterns.get("caffeine_impact", {})
        correlations = patterns.get("correlations", {})

        prompt = f"""Обнаружены следующие паттерны в твоих данных WHOOP:

**Паттерны Recovery:**
- Дней с высоким Recovery (>=70%): {recovery_patterns.get('high_recovery_count', 0)}
- Дней с низким Recovery (<50%): {recovery_patterns.get('low_recovery_count', 0)}
- Средний HRV при высоком Recovery: {recovery_patterns.get('high_recovery_avg_hrv', 'N/A')}ms
- Средний HRV при низком Recovery: {recovery_patterns.get('low_recovery_avg_hrv', 'N/A')}ms
- Средний Deep sleep при высоком Recovery: {recovery_patterns.get('high_recovery_avg_deep', 'N/A')} минут
- Средний Deep sleep при низком Recovery: {recovery_patterns.get('low_recovery_avg_deep', 'N/A')} минут

**Паттерны сна:**
- Средний Sleep debt: {sleep_patterns.get('avg_sleep_debt', 'N/A')} минут
- Средняя эффективность сна: {sleep_patterns.get('avg_efficiency', 'N/A')}%

**Влияние кофеина:**
- Дней с кофеином: {caffeine_impact.get('caffeine_days_count', 0)}
- Дней без кофеина: {caffeine_impact.get('no_caffeine_days_count', 0)}
- Средняя эффективность сна в дни с кофеином: {caffeine_impact.get('caffeine_avg_efficiency', 'N/A')}%
- Средняя эффективность сна в дни без кофеина: {caffeine_impact.get('no_caffeine_avg_efficiency', 'N/A')}%

**Корреляции:**
"""

        # Добавляем информацию о корреляциях
        if correlations.get("hrv_recovery"):
            hrv_rec = correlations["hrv_recovery"]
            prompt += f"- При высоком HRV (>50ms): средний Recovery {hrv_rec.get('high_hrv_avg_recovery', 'N/A')}%\n"
            prompt += f"- При низком HRV (<45ms): средний Recovery {hrv_rec.get('low_hrv_avg_recovery', 'N/A')}%\n"

        prompt += """
Создай глубокий анализ паттернов:

1. **Какие факторы сильнее всего влияют на твой Recovery?** (4-5 предложений)
   - Что больше всего способствует высокому Recovery?
   - Что приводит к низкому Recovery?
   - Какие метрики наиболее важны?

2. **Что можно оптимизировать?** (4-5 предложений)
   - Где есть потенциал для улучшения?
   - Какие привычки стоит изменить?
   - Какие ритуалы добавить?

3. **Конкретные действия для улучшения показателей** (5-6 предложений)
   - Практические шаги на основе паттернов
   - Оптимальные стратегии восстановления
   - Рекомендации по режиму сна и тренировок

Используй принципы программирования подсознания:
- Позитивные утверждения в настоящем времени
- Визуализация успеха и улучшения
- Конкретные образы оптимального состояния
- Связь действий с результатами

**Важно:**
- Пиши по-русски, тепло и уверенно
- Избегай избыточных эмодзи и форматирования (не используй S1, S2, S3 и т.д.)
- Фокусируйся на здоровье, энергии и восстановлении
- Будь конкретным и практичным в рекомендациях"""

        return prompt

    def _generate_fallback_analysis(self, patterns: dict[str, Any]) -> str:
        """
        Генерация fallback анализа без LLM.

        Args:
            patterns: Обнаруженные паттерны

        Returns:
            Базовый анализ
        """
        recovery_patterns = patterns.get("recovery_patterns", {})
        caffeine_impact = patterns.get("caffeine_impact", {})

        analysis = f"""📊 Анализ паттернов:

**Recovery:**
- Высокий Recovery (>=70%): {recovery_patterns.get('high_recovery_count', 0)} дней
- Низкий Recovery (<50%): {recovery_patterns.get('low_recovery_count', 0)} дней

**Кофеин:**
- Дней с кофеином: {caffeine_impact.get('caffeine_days_count', 0)}
- Эффективность сна с кофеином: {caffeine_impact.get('caffeine_avg_efficiency', 'N/A')}%
- Эффективность сна без кофеина: {caffeine_impact.get('no_caffeine_avg_efficiency', 'N/A')}%

Продолжай отслеживать паттерны для оптимизации показателей!"""
        return analysis

