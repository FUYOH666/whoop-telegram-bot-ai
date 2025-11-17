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

    path: str = "ras_bot.db"

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


class SlotConfig:
    """Конфигурация одного слота."""

    def __init__(self, slot_id: str, config: dict[str, Any]):
        """
        Инициализация конфигурации слота.

        Args:
            slot_id: Идентификатор слота (S1-S6)
            config: Словарь с конфигурацией из YAML
        """
        self.slot_id = slot_id
        self.name = config.get("name", "")
        self.time = config.get("time", "00:00")
        self.description = config.get("description", "")
        self.user_prompt_template = config.get("user_prompt_template", "")
        self.fallback_message = config.get("fallback_message", "")


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
        for slot_id, slot_data in slots_config.items():
            self.slots[slot_id] = SlotConfig(slot_id, slot_data)

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

