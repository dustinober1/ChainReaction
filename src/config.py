"""
Configuration management for ChainReaction.

Uses Pydantic Settings for type-safe configuration with environment variable support.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseSettings):
    """Neo4j database configuration."""

    model_config = SettingsConfigDict(env_prefix="NEO4J_")

    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password: SecretStr = Field(description="Neo4j password")
    database: str = Field(default="neo4j", description="Neo4j database name")


class OpenAISettings(BaseSettings):
    """OpenAI API configuration for DSPy and LangGraph."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    api_key: SecretStr = Field(description="OpenAI API key")
    model: str = Field(default="gpt-4-turbo-preview", description="Default model to use")


class NewsAPISettings(BaseSettings):
    """External news API configuration."""

    tavily_api_key: SecretStr | None = Field(default=None, description="Tavily API key")
    news_api_key: SecretStr | None = Field(default=None, description="NewsAPI key")


class MonitoringSettings(BaseSettings):
    """Scout Agent monitoring configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    monitor_interval: int = Field(
        default=300, description="Monitoring interval in seconds", ge=60, le=3600
    )
    max_events_per_cycle: int = Field(
        default=50, description="Maximum events to process per cycle", ge=1, le=500
    )
    confidence_threshold: float = Field(
        default=0.7, description="Minimum confidence for risk extraction", ge=0.0, le=1.0
    )


class APISettings(BaseSettings):
    """API server configuration."""

    model_config = SettingsConfigDict(env_prefix="API_")

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port", ge=1, le=65535)
    reload: bool = Field(default=True, description="Enable auto-reload in development")


class Settings(BaseSettings):
    """Root settings class combining all configuration sections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", description="Application environment"
    )
    app_debug: bool = Field(default=True, description="Enable debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    secret_key: SecretStr = Field(description="Application secret key")

    # Nested settings
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    news_api: NewsAPISettings = Field(default_factory=NewsAPISettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    api: APISettings = Field(default_factory=APISettings)

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns cached settings instance to avoid re-loading from environment.
    """
    return Settings()
