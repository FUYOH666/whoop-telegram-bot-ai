"""Тестовый скрипт для проверки всех функций аналитики на реальных данных."""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from whoop_telegram_bot_ai.analytics import WhoopAnalytics
from whoop_telegram_bot_ai.config import Config
from whoop_telegram_bot_ai.llm_client import LLMClient
from whoop_telegram_bot_ai.pattern_analyzer import PatternAnalyzer
from whoop_telegram_bot_ai.predictions import RecoveryPredictor
from whoop_telegram_bot_ai.recommendations import RecommendationsGenerator
from whoop_telegram_bot_ai.weekly_report import WeeklyReportGenerator
from whoop_telegram_bot_ai.whoop_export_parser import WhoopExportParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def main():
    """Главная функция тестирования."""
    logger.info("=" * 80)
    logger.info("Тестирование аналитики WHOOP на реальных данных")
    logger.info("=" * 80)

    # Путь к экспортированным данным
    export_dir = Path("my_whoop_data_2025_11_17")

    if not export_dir.exists():
        logger.error(f"Папка с экспортированными данными не найдена: {export_dir}")
        logger.info("Убедитесь, что папка my_whoop_data_2025_11_17 существует в корне проекта")
        return

    try:
        # 1. Парсинг данных
        logger.info("\n" + "=" * 80)
        logger.info("1. Парсинг экспортированных данных")
        logger.info("=" * 80)

        parser = WhoopExportParser(export_dir)
        data = parser.parse_all()

        logger.info(f"✓ Распарсено циклов: {len(data['cycles'])}")
        logger.info(f"✓ Распарсено записей сна: {len(data['sleeps'])}")
        logger.info(f"✓ Распарсено тренировок: {len(data['workouts'])}")
        logger.info(f"✓ Распарсено журнальных записей: {len(data['journal_entries'])}")

        if not data["cycles"]:
            logger.error("Нет данных циклов для анализа")
            return

        # 2. Создание аналитики
        logger.info("\n" + "=" * 80)
        logger.info("2. Создание аналитики")
        logger.info("=" * 80)

        analytics = WhoopAnalytics(
            data["cycles"],
            data["sleeps"],
            data["workouts"],
            data["journal_entries"],
        )

        # Получаем статистику за неделю
        stats = analytics.get_weekly_stats()
        logger.info(f"✓ Статистика за период: {stats['period']['start']} - {stats['period']['end']}")
        logger.info(f"  Recovery: средний {stats['recovery'].get('avg', 'N/A')}%")
        logger.info(f"  Сон: средняя продолжительность {stats['sleep'].get('avg_duration_hours', 'N/A')}ч")
        logger.info(f"  Strain: средний {stats['strain'].get('avg', 'N/A')}")
        logger.info(f"  Тренировки: {stats['workouts'].get('count', 0)}")

        # Получаем паттерны
        patterns = analytics.get_patterns()
        logger.info("✓ Паттерны проанализированы")

        # 3. Загрузка конфигурации и LLM клиента
        logger.info("\n" + "=" * 80)
        logger.info("3. Инициализация LLM клиента")
        logger.info("=" * 80)

        try:
            config = Config()
            llm_client = LLMClient(config)
            logger.info("✓ LLM клиент инициализирован")
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации LLM клиента: {e}")
            logger.info("Проверьте наличие .env файла с OPENROUTER_API_KEY")
            return

        # 4. Генерация еженедельного отчета
        logger.info("\n" + "=" * 80)
        logger.info("4. Генерация еженедельного отчета")
        logger.info("=" * 80)

        try:
            report_generator = WeeklyReportGenerator(analytics, llm_client)
            report = await report_generator.generate_weekly_report()
            logger.info("✓ Еженедельный отчет сгенерирован")
            logger.info("\n" + "-" * 80)
            logger.info("ЕЖЕНЕДЕЛЬНЫЙ ОТЧЕТ:")
            logger.info("-" * 80)
            print("\n" + report + "\n")
            logger.info("-" * 80)
        except Exception as e:
            logger.error(f"✗ Ошибка генерации еженедельного отчета: {e}", exc_info=True)

        # 5. Анализ паттернов
        logger.info("\n" + "=" * 80)
        logger.info("5. Анализ паттернов")
        logger.info("=" * 80)

        try:
            pattern_analyzer = PatternAnalyzer(analytics, llm_client)
            pattern_analysis = await pattern_analyzer.analyze_patterns()
            logger.info("✓ Анализ паттернов выполнен")
            logger.info("\n" + "-" * 80)
            logger.info("АНАЛИЗ ПАТТЕРНОВ:")
            logger.info("-" * 80)
            print("\n" + pattern_analysis + "\n")
            logger.info("-" * 80)
        except Exception as e:
            logger.error(f"✗ Ошибка анализа паттернов: {e}", exc_info=True)

        # 6. Генерация рекомендаций
        logger.info("\n" + "=" * 80)
        logger.info("6. Генерация рекомендаций")
        logger.info("=" * 80)

        try:
            recommendations_generator = RecommendationsGenerator(analytics, llm_client)
            recommendations = await recommendations_generator.generate_recommendations()
            logger.info("✓ Рекомендации сгенерированы")
            logger.info("\n" + "-" * 80)
            logger.info("РЕКОМЕНДАЦИИ:")
            logger.info("-" * 80)
            print("\n" + recommendations + "\n")
            logger.info("-" * 80)
        except Exception as e:
            logger.error(f"✗ Ошибка генерации рекомендаций: {e}", exc_info=True)

        # 7. Предсказание Recovery
        logger.info("\n" + "=" * 80)
        logger.info("7. Предсказание Recovery")
        logger.info("=" * 80)

        try:
            predictor = RecoveryPredictor(analytics, llm_client)
            prediction = await predictor.predict_recovery()
            logger.info("✓ Предсказание Recovery выполнено")
            logger.info("\n" + "-" * 80)
            logger.info("ПРЕДСКАЗАНИЕ RECOVERY:")
            logger.info("-" * 80)
            print("\n" + prediction + "\n")
            logger.info("-" * 80)
        except Exception as e:
            logger.error(f"✗ Ошибка предсказания Recovery: {e}", exc_info=True)

        logger.info("\n" + "=" * 80)
        logger.info("Тестирование завершено!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

