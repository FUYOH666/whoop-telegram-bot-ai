# Аналитика данных WHOOP

Документация по новым модулям для анализа экспортированных данных WHOOP.

## Созданные модули

### 1. `whoop_export_parser.py`
Парсер экспортированных CSV файлов WHOOP.

**Функции:**
- `parse_physiological_cycles()` - парсинг physiological_cycles.csv
- `parse_sleeps()` - парсинг sleeps.csv
- `parse_workouts()` - парсинг workouts.csv
- `parse_journal_entries()` - парсинг journal_entries.csv
- `parse_all()` - парсинг всех файлов сразу

**Использование:**
```python
from whoop_telegram_bot_ai.whoop_export_parser import WhoopExportParser

parser = WhoopExportParser("my_whoop_data_2025_11_17")
data = parser.parse_all()
```

### 2. `analytics.py`
Аналитика данных WHOOP - вычисление метрик и статистики.

**Основные методы:**
- `get_weekly_stats(start_date, end_date)` - статистика за период
- `get_patterns()` - анализ паттернов и корреляций

**Возвращаемые метрики:**
- Recovery статистика (avg, min, max, trend, HRV, RHR)
- Sleep статистика (duration, efficiency, consistency, phases)
- Strain статистика (avg, max)
- Workout статистика (count, avg_strain, total_energy)
- Caffeine статистика (days_with, days_without)
- Тренды (recovery, HRV)

**Использование:**
```python
from whoop_telegram_bot_ai.analytics import WhoopAnalytics

analytics = WhoopAnalytics(cycles, sleeps, workouts, journal_entries)
stats = analytics.get_weekly_stats()
patterns = analytics.get_patterns()
```

### 3. `weekly_report.py`
Генератор еженедельных аналитических отчетов через LLM.

**Основные методы:**
- `generate_weekly_report(start_date, end_date)` - генерация отчета

**Структура отчета:**
1. Краткое резюме
2. Что работает хорошо?
3. Где есть возможности для улучшения?
4. Какие паттерны заметны?
5. Конкретные рекомендации на следующую неделю

**Использование:**
```python
from whoop_telegram_bot_ai.weekly_report import WeeklyReportGenerator

generator = WeeklyReportGenerator(analytics, llm_client)
report = await generator.generate_weekly_report()
```

### 4. `pattern_analyzer.py`
Анализатор паттернов и корреляций между метриками.

**Основные методы:**
- `analyze_patterns()` - анализ паттернов через LLM

**Анализируемые паттерны:**
- Recovery ↔ HRV корреляция
- Recovery ↔ Deep sleep корреляция
- Кофеин ↔ Sleep efficiency влияние
- Workout timing анализ

**Использование:**
```python
from whoop_telegram_bot_ai.pattern_analyzer import PatternAnalyzer

analyzer = PatternAnalyzer(analytics, llm_client)
analysis = await analyzer.analyze_patterns()
```

### 5. `recommendations.py`
Система персонализированных рекомендаций на основе паттернов.

**Основные методы:**
- `generate_recommendations()` - генерация рекомендаций

**Типы рекомендаций:**
1. Что делать прямо сейчас для улучшения Recovery?
2. Как оптимизировать сон сегодня?
3. Когда лучше планировать следующую тренировку?
4. Какие ритуалы помогут восстановлению?

**Использование:**
```python
from whoop_telegram_bot_ai.recommendations import RecommendationsGenerator

generator = RecommendationsGenerator(analytics, llm_client)
recommendations = await generator.generate_recommendations()
```

### 6. `predictions.py`
Предсказательная аналитика для Recovery и других метрик.

**Основные методы:**
- `predict_recovery()` - предсказание Recovery на завтра

**Что предсказывает:**
- Ожидаемый уровень Recovery на завтра
- Рекомендации для улучшения Recovery
- Оптимизация сна сегодня
- Планирование на завтра

**Использование:**
```python
from whoop_telegram_bot_ai.predictions import RecoveryPredictor

predictor = RecoveryPredictor(analytics, llm_client)
prediction = await predictor.predict_recovery()
```

## Интеграция в бота

Для интеграции этих модулей в бота нужно:

1. Добавить команды в `bot.py`:
   - `/weekly_report` - еженедельный отчет
   - `/analyze_patterns` - анализ паттернов
   - `/recommendations` - персонализированные рекомендации
   - `/predict_recovery` - предсказание Recovery

2. Добавить планировщик для автоматической отправки еженедельных отчетов (каждое воскресенье)

3. Расширить Storage для хранения экспортированных данных (опционально)

## Примеры использования

### Полный цикл анализа данных

```python
from whoop_telegram_bot_ai.whoop_export_parser import WhoopExportParser
from whoop_telegram_bot_ai.analytics import WhoopAnalytics
from whoop_telegram_bot_ai.weekly_report import WeeklyReportGenerator
from whoop_telegram_bot_ai.config import Config
from whoop_telegram_bot_ai.llm_client import LLMClient

# Парсинг данных
parser = WhoopExportParser("my_whoop_data_2025_11_17")
data = parser.parse_all()

# Создание аналитики
analytics = WhoopAnalytics(
    data["cycles"],
    data["sleeps"],
    data["workouts"],
    data["journal_entries"]
)

# Генерация отчета
config = Config()
llm_client = LLMClient(config)
report_generator = WeeklyReportGenerator(analytics, llm_client)
report = await report_generator.generate_weekly_report()
```

## Следующие шаги

1. Интеграция команд в бота
2. Добавление автоматической отправки еженедельных отчетов
3. Расширение Storage для хранения экспортированных данных
4. Добавление экспорта данных с анализом (CSV/JSON/PDF)
5. Улучшение предсказательной модели на основе большего объема данных

