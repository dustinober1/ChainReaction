"""
LLM Provider Abstraction.

Provides a unified interface for different LLM backends (OpenAI, Ollama).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import httpx
import structlog

from src.config import get_settings, LLMProvider

logger = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] | None = None
    raw_response: dict[str, Any] | None = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Check if the provider is available."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(self):
        """Initialize the OpenAI provider."""
        settings = get_settings()
        self.api_key = settings.openai.api_key.get_secret_value()
        self.model = settings.openai.model
        self.default_temperature = settings.openai.temperature
        self.default_max_tokens = settings.openai.max_tokens
        self.base_url = "https://api.openai.com/v1"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a response using OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature or self.default_temperature,
                    "max_tokens": max_tokens or self.default_max_tokens,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage")

        logger.info(
            "OpenAI generation complete",
            model=self.model,
            tokens=usage.get("total_tokens") if usage else None,
        )

        return LLMResponse(
            content=content,
            model=self.model,
            provider="openai",
            usage=usage,
            raw_response=data,
        )

    async def check_health(self) -> bool:
        """Check if OpenAI API is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "openai"


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider."""

    def __init__(self):
        """Initialize the Ollama provider."""
        settings = get_settings()
        self.base_url = settings.ollama.base_url
        self.model = settings.ollama.model
        self.default_temperature = settings.ollama.temperature
        self.num_ctx = settings.ollama.num_ctx
        self.timeout = settings.ollama.timeout

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a response using Ollama API."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature or self.default_temperature,
                        "num_ctx": self.num_ctx,
                        "num_predict": max_tokens or 2048,
                    },
                },
                timeout=float(self.timeout),
            )
            response.raise_for_status()
            data = response.json()

        content = data.get("response", "")
        
        # Calculate approximate token usage
        usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }

        logger.info(
            "Ollama generation complete",
            model=self.model,
            tokens=usage["total_tokens"],
            eval_duration=data.get("eval_duration"),
        )

        return LLMResponse(
            content=content,
            model=self.model,
            provider="ollama",
            usage=usage,
            raw_response=data,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a response using Ollama chat API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature or self.default_temperature,
                        "num_ctx": self.num_ctx,
                        "num_predict": max_tokens or 2048,
                    },
                },
                timeout=float(self.timeout),
            )
            response.raise_for_status()
            data = response.json()

        content = data.get("message", {}).get("content", "")
        
        usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }

        return LLMResponse(
            content=content,
            model=self.model,
            provider="ollama",
            usage=usage,
            raw_response=data,
        )

    async def check_health(self) -> bool:
        """Check if Ollama server is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available Ollama models."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error("Failed to list Ollama models", error=str(e))
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama library."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": False},
                    timeout=300.0,  # Models can take a while to download
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error("Failed to pull Ollama model", model=model_name, error=str(e))
            return False

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "ollama"


def get_llm_provider() -> BaseLLMProvider:
    """
    Get the configured LLM provider.

    Returns the appropriate provider based on settings.
    """
    settings = get_settings()

    if settings.llm_provider == LLMProvider.OLLAMA:
        logger.info("Using Ollama provider", model=settings.ollama.model)
        return OllamaProvider()
    else:
        logger.info("Using OpenAI provider", model=settings.openai.model)
        return OpenAIProvider()


async def check_llm_availability() -> dict[str, Any]:
    """
    Check availability of configured LLM provider.

    Returns status information about the LLM provider.
    """
    settings = get_settings()
    provider = get_llm_provider()

    result = {
        "provider": provider.provider_name,
        "model": settings.current_model,
        "available": False,
        "error": None,
    }

    try:
        result["available"] = await provider.check_health()
        if not result["available"]:
            result["error"] = f"{provider.provider_name} is not responding"
    except Exception as e:
        result["error"] = str(e)

    # Additional info for Ollama
    if isinstance(provider, OllamaProvider) and result["available"]:
        result["available_models"] = await provider.list_models()

    return result
