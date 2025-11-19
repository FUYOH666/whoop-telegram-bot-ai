"""Конфигурация RAS Bot - загрузка YAML и переменных окружения."""

import logging
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Загружаем переменные окружения из .env файла
load_dotenv()

logger = logging.getLogger(__name__)


class OpenRouterConfig(BaseSettings):
    """Конфигурация OpenRouter API."""

    api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    model: str = "anthropic/claude-3.5-sonnet"
    temperature: float = 0.7
    max_tokens: int = 150
    timeout: float = 30.0
    api_key: str = Field(..., alias="OPENROUTER_API_KEY")

    model_config = SettingsConfigDict(env_prefix="OPENROUTER_", case_sensitive=False)


class DatabaseConfig(BaseSettings):
    """Конфигурация базы данных."""

    path: str = "whoop_telegram_bot_ai.db"

    model_config = SettingsConfigDict(env_prefix="DATABASE_", case_sensitive=False)


class LoggingConfig(BaseSettings):
    """Конфигурация логирования."""

    level: str = "INFO"
    format: str = "json"

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Валидация уровня логирования."""
        valid_levels = ["DEBUG", "INFO", "ERROR"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    model_config = SettingsConfigDict(env_prefix="LOG_", case_sensitive=False)


class WhoopConfig:
    """Конфигурация WHOOP API."""

    def __init__(self, config: dict[str, Any]):
        """
        Инициализация конфигурации WHOOP.

        Args:
            config: Словарь с конфигурацией из YAML
        """
        self.api_url = config.get("api_url", "https://api.prod.whoop.com/developer/v1")
        self.oauth_url = config.get("oauth_url", "https://api.prod.whoop.com/oauth/oauth2/auth")
        self.token_url = config.get("token_url", "https://api.prod.whoop.com/oauth/oauth2/token")
        self.redirect_uri = config.get("redirect_uri", "https://t.me/RAS_AI_bot?start=whoop_auth")
        self.scopes = config.get("scopes", ["read:recovery", "read:sleep", "read:workout", "read:profile"])

        # Загружаем client_id и client_secret из переменных окружения (опционально)
        from pydantic_settings import BaseSettings

        class WhoopCredentials(BaseSettings):
            client_id: str | None = Field(default=None, alias="WHOOP_CLIENT_ID")
            client_secret: str | None = Field(default=None, alias="WHOOP_CLIENT_SECRET")
            model_config = SettingsConfigDict(case_sensitive=False)

        try:
            credentials = WhoopCredentials()
            self.client_id = credentials.client_id
            self.client_secret = credentials.client_secret
        except Exception:
            # Если переменные окружения не заданы, это нормально (WHOOP опционален)
            self.client_id = None
            self.client_secret = None

    @property
    def is_configured(self) -> bool:
        """Проверка, настроена ли конфигурация WHOOP."""
        return self.client_id is not None and self.client_secret is not None


class WhoopMonitoringConfig:
    """Конфигурация мониторинга WHOOP в реальном времени."""

    def __init__(self, config: dict[str, Any]):
        """
        Инициализация конфигурации мониторинга.

        Args:
            config: Словарь с конфигурацией из YAML
        """
        self.enabled = config.get("enabled", True)
        self.check_interval_minutes = config.get("check_interval_minutes", 30)
        self.active_hours = config.get("active_hours", {})
        self.start_time = self.active_hours.get("start", "08:00")
        self.end_time = self.active_hours.get("end", "00:00")
        self.stress_threshold = config.get("stress_threshold", 12.0)
        self.notification_cooldown_hours = config.get("notification_cooldown_hours", 2.0)
        self.recovery_thresholds = config.get("recovery_thresholds", {})
        self.recovery_low = self.recovery_thresholds.get("low", 50)
        self.recovery_high = self.recovery_thresholds.get("high", 70)
        self.stress_advice_prompt = config.get("stress_advice_prompt", "")


class SlotConfig:
    """Конфигурация одного слота."""

    def __init__(self, slot_id: str, config: dict[str, Any], default_max_tokens: int = 150):
        """
        Инициализация конфигурации слота.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            config: Словарь с конфигурацией из YAML
            default_max_tokens: Значение max_tokens по умолчанию из openrouter конфигурации
        """
        self.slot_id = slot_id
        self.name = config.get("name", "")
        self.time = config.get("time", "00:00")
        self.description = config.get("description", "")
        self.user_prompt_template = config.get("user_prompt_template", "")
        self.fallback_message = config.get("fallback_message", "")
        # Если max_tokens указан для слота, используем его, иначе используем значение по умолчанию
        self.max_tokens = config.get("max_tokens", default_max_tokens)


class IdealDayConfig:
    """Конфигурация логики эталонного дня."""

    def __init__(self, config: dict[str, Any]):
        """
        Инициализация конфигурации эталонного дня.

        Args:
            config: Словарь с конфигурацией из YAML
        """
        self.min_successful_slots = config.get("min_successful_slots", 4)
        self.s6_ideal_button = config.get("s6_ideal_button", "ideal")


class Config:
    """Главный класс конфигурации."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Инициализация конфигурации.

        Args:
            config_path: Путь к файлу config.yaml

        Raises:
            FileNotFoundError: Если файл конфигурации не найден
            ValueError: Если отсутствуют обязательные параметры
        """
        self.config_path = Path(config_path)

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Загружаем YAML
        with open(self.config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Загружаем настройки из env через pydantic-settings
        try:
            self.openrouter = OpenRouterConfig()
            self.database = DatabaseConfig(**yaml_config.get("database", {}))
            self.logging_config = LoggingConfig(**yaml_config.get("logging", {}))
        except Exception as e:
            logger.error("Failed to load configuration from environment", extra={"error": str(e)})
            raise ValueError(
                "Missing required environment variables. "
                "Please check TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY in .env file"
            ) from e

        # Загружаем конфигурацию WHOOP (опционально)
        whoop_yaml = yaml_config.get("whoop", {})
        self.whoop = WhoopConfig(whoop_yaml)
        if not self.whoop.is_configured:
            logger.info("WHOOP API not configured (client_id/client_secret not set). WHOOP features will be disabled.")

        # Загружаем конфигурацию мониторинга WHOOP
        whoop_monitoring_yaml = yaml_config.get("whoop_monitoring", {})
        self.whoop_monitoring = WhoopMonitoringConfig(whoop_monitoring_yaml)

        # Загружаем Telegram Bot Token из env
        from pydantic_settings import BaseSettings

        class TelegramConfig(BaseSettings):
            bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
            model_config = SettingsConfigDict(case_sensitive=False)

        try:
            telegram_config = TelegramConfig()
            self.telegram_bot_token = telegram_config.bot_token
        except Exception as e:
            logger.error("Failed to load Telegram bot token", extra={"error": str(e)})
            raise ValueError(
                "Missing TELEGRAM_BOT_TOKEN in environment variables. "
                "Please check your .env file"
            ) from e

        # Загружаем системный промпт
        self.system_prompt = yaml_config.get("system_prompt", "")

        # Загружаем конфигурацию слотов
        slots_config = yaml_config.get("slots", {})
        self.slots: dict[str, SlotConfig] = {}
        default_max_tokens = self.openrouter.max_tokens
        for slot_id, slot_data in slots_config.items():
            self.slots[slot_id] = SlotConfig(slot_id, slot_data, default_max_tokens)

        # Загружаем конфигурацию эталонного дня
        ideal_day_config = yaml_config.get("ideal_day", {})
        self.ideal_day = IdealDayConfig(ideal_day_config)

        # Переопределяем настройки из YAML, если они есть
        openrouter_yaml = yaml_config.get("openrouter", {})
        if openrouter_yaml:
            for key, value in openrouter_yaml.items():
                if hasattr(self.openrouter, key):
                    setattr(self.openrouter, key, value)

        logger.info("Configuration loaded successfully", extra={"config_path": str(config_path)})

    def get_slot_config(self, slot_id: str) -> SlotConfig:
        """
        Получение конфигурации слота.

        Args:
            slot_id: Идентификатор слота (S1-S6)

        Returns:
            Конфигурация слота

        Raises:
            KeyError: Если слот не найден
        """
        if slot_id not in self.slots:
            raise KeyError(f"Slot {slot_id} not found in configuration")
        return self.slots[slot_id]

    def validate(self) -> None:
        """
        Валидация конфигурации.

        Raises:
            ValueError: Если конфигурация невалидна
        """
        errors = []

        # Проверяем обязательные параметры
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")

        if not self.openrouter.api_key:
            errors.append("OPENROUTER_API_KEY is required")

        if not self.system_prompt:
            errors.append("system_prompt is required in config.yaml")

        # Проверяем наличие всех 6 слотов
        expected_slots = ["S1", "S2", "S3", "S4", "S5", "S6"]
        for slot_id in expected_slots:
            if slot_id not in self.slots:
                errors.append(f"Slot {slot_id} is missing in configuration")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error("Configuration validation failed", extra={"errors": errors})
            raise ValueError(error_msg)

        logger.info("Configuration validated successfully")

