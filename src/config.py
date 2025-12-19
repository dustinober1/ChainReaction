"""
Configuration management for ChainReaction.

Uses Pydantic Settings for type-safe configuration with environment variable support.
"""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    OLLAMA = "ollama"


class Neo4jSettings(BaseSettings):
    """Neo4j database configuration."""

    model_config = SettingsConfigDict(env_prefix="NEO4J_")

    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password: SecretStr = Field(default="password", description="Neo4j password")
    database: str = Field(default="neo4j", description="Neo4j database name")


class OpenAISettings(BaseSettings):
    """OpenAI API configuration for DSPy and LangGraph."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    api_key: SecretStr = Field(default="not-set", description="OpenAI API key")
    model: str = Field(default="gpt-4-turbo-preview", description="Default model to use")
    temperature: float = Field(default=0.7, description="Temperature for generation", ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, description="Maximum tokens for generation", ge=1)


class OllamaSettings(BaseSettings):
    """Ollama configuration for local LLM inference."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    model: str = Field(default="qwen3:1.7b", description="Default Ollama model to use")
    temperature: float = Field(default=0.7, description="Temperature for generation", ge=0.0, le=2.0)
    num_ctx: int = Field(default=4096, description="Context window size", ge=512)
    timeout: int = Field(default=120, description="Request timeout in seconds", ge=10)


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
    secret_key: SecretStr = Field(default="dev-secret-key", description="Application secret key")
    api_key: SecretStr = Field(default="dev-api-key-12345", description="Default API key for development")

    # LLM Provider selection
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="LLM provider to use (openai or ollama)"
    )

    # Nested settings
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
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

    @property
    def using_ollama(self) -> bool:
        """Check if using Ollama as LLM provider."""
        return self.llm_provider == LLMProvider.OLLAMA

    @property
    def using_openai(self) -> bool:
        """Check if using OpenAI as LLM provider."""
        return self.llm_provider == LLMProvider.OPENAI

    @property
    def current_model(self) -> str:
        """Get the current model name based on provider."""
        if self.using_ollama:
            return self.ollama.model
        return self.openai.model


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns cached settings instance to avoid re-loading from environment.
    """
    return Settings()

