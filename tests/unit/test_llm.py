"""
Unit Tests for LLM Provider Module.

Tests for OpenAI and Ollama provider implementations.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from src.config import LLMProvider
from src.llm.provider import (
    LLMResponse,
    OpenAIProvider,
    OllamaProvider,
    get_llm_provider,
    check_llm_availability,
)


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_response(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Test response",
            model="gpt-4",
            provider="openai",
            usage={"total_tokens": 100},
        )
        
        assert response.content == "Test response"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 100

    def test_response_without_usage(self):
        """Test response without usage data."""
        response = LLMResponse(
            content="Test",
            model="llama3.2",
            provider="ollama",
        )
        
        assert response.usage is None
        assert response.raw_response is None


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    @pytest.fixture
    def provider(self):
        """Create OpenAI provider with mocked settings."""
        with patch("src.llm.provider.get_settings") as mock_settings:
            mock_settings.return_value.openai.api_key.get_secret_value.return_value = "test-key"
            mock_settings.return_value.openai.model = "gpt-4"
            mock_settings.return_value.openai.temperature = 0.7
            mock_settings.return_value.openai.max_tokens = 2048
            return OpenAIProvider()

    def test_provider_name(self, provider):
        """Test provider name property."""
        assert provider.provider_name == "openai"

    def test_provider_configuration(self, provider):
        """Test provider is configured correctly."""
        assert provider.model == "gpt-4"
        assert provider.default_temperature == 0.7
        assert provider.default_max_tokens == 2048

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        mock_response = {
            "choices": [{"message": {"content": "Generated text"}}],
            "usage": {"total_tokens": 50},
        }
        
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            MockClient.return_value.__aenter__.return_value = mock_client
            
            response = await provider.generate("Test prompt")
            
            assert response.content == "Generated text"
            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test health check when API is available."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value.status_code = 200
            MockClient.return_value.__aenter__.return_value = mock_client
            
            result = await provider.check_health()
            
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider):
        """Test health check when API is unavailable."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection error")
            MockClient.return_value.__aenter__.return_value = mock_client
            
            result = await provider.check_health()
            
            assert result is False


class TestOllamaProvider:
    """Tests for Ollama provider."""

    @pytest.fixture
    def provider(self):
        """Create Ollama provider with mocked settings."""
        with patch("src.llm.provider.get_settings") as mock_settings:
            mock_settings.return_value.ollama.base_url = "http://localhost:11434"
            mock_settings.return_value.ollama.model = "llama3.2"
            mock_settings.return_value.ollama.temperature = 0.7
            mock_settings.return_value.ollama.num_ctx = 4096
            mock_settings.return_value.ollama.timeout = 120
            return OllamaProvider()

    def test_provider_name(self, provider):
        """Test provider name property."""
        assert provider.provider_name == "ollama"

    def test_provider_configuration(self, provider):
        """Test provider is configured correctly."""
        assert provider.model == "llama3.2"
        assert provider.base_url == "http://localhost:11434"
        assert provider.num_ctx == 4096

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        mock_response = {
            "response": "Generated text from Ollama",
            "prompt_eval_count": 20,
            "eval_count": 30,
        }
        
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            MockClient.return_value.__aenter__.return_value = mock_client
            
            response = await provider.generate("Test prompt")
            
            assert response.content == "Generated text from Ollama"
            assert response.provider == "ollama"
            assert response.usage["total_tokens"] == 50

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider):
        """Test generation with system prompt."""
        mock_response = {
            "response": "Response with system prompt",
            "prompt_eval_count": 30,
            "eval_count": 20,
        }
        
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            MockClient.return_value.__aenter__.return_value = mock_client
            
            response = await provider.generate(
                "Test prompt",
                system_prompt="You are a helpful assistant",
            )
            
            assert response.content == "Response with system prompt"

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test health check when Ollama is available."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value.status_code = 200
            MockClient.return_value.__aenter__.return_value = mock_client
            
            result = await provider.check_health()
            
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider):
        """Test health check when Ollama is unavailable."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            MockClient.return_value.__aenter__.return_value = mock_client
            
            result = await provider.check_health()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """Test listing available models."""
        mock_response = {
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
            ]
        }
        
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.status_code = 200
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response_obj
            MockClient.return_value.__aenter__.return_value = mock_client
            
            models = await provider.list_models()
            
            assert len(models) == 2
            assert "llama3.2" in models
            assert "mistral" in models

    @pytest.mark.asyncio
    async def test_list_models_failure(self, provider):
        """Test listing models when Ollama is unavailable."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection error")
            MockClient.return_value.__aenter__.return_value = mock_client
            
            models = await provider.list_models()
            
            assert models == []


class TestGetLLMProvider:
    """Tests for provider factory function."""

    def test_get_openai_provider(self):
        """Test getting OpenAI provider."""
        with patch("src.llm.provider.get_settings") as mock_settings:
            mock_settings.return_value.llm_provider = LLMProvider.OPENAI
            mock_settings.return_value.openai.api_key.get_secret_value.return_value = "test"
            mock_settings.return_value.openai.model = "gpt-4"
            mock_settings.return_value.openai.temperature = 0.7
            mock_settings.return_value.openai.max_tokens = 2048
            
            provider = get_llm_provider()
            
            assert isinstance(provider, OpenAIProvider)

    def test_get_ollama_provider(self):
        """Test getting Ollama provider."""
        with patch("src.llm.provider.get_settings") as mock_settings:
            mock_settings.return_value.llm_provider = LLMProvider.OLLAMA
            mock_settings.return_value.ollama.base_url = "http://localhost:11434"
            mock_settings.return_value.ollama.model = "llama3.2"
            mock_settings.return_value.ollama.temperature = 0.7
            mock_settings.return_value.ollama.num_ctx = 4096
            mock_settings.return_value.ollama.timeout = 120
            
            provider = get_llm_provider()
            
            assert isinstance(provider, OllamaProvider)


class TestCheckLLMAvailability:
    """Tests for LLM availability checker."""

    @pytest.mark.asyncio
    async def test_check_openai_available(self):
        """Test checking OpenAI availability."""
        with patch("src.llm.provider.get_settings") as mock_settings:
            mock_settings.return_value.llm_provider = LLMProvider.OPENAI
            mock_settings.return_value.current_model = "gpt-4"
            mock_settings.return_value.openai.api_key.get_secret_value.return_value = "test"
            mock_settings.return_value.openai.model = "gpt-4"
            mock_settings.return_value.openai.temperature = 0.7
            mock_settings.return_value.openai.max_tokens = 2048
            
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.get.return_value.status_code = 200
                MockClient.return_value.__aenter__.return_value = mock_client
                
                result = await check_llm_availability()
                
                assert result["provider"] == "openai"
                assert result["available"] is True

    @pytest.mark.asyncio
    async def test_check_ollama_available(self):
        """Test checking Ollama availability with model list."""
        with patch("src.llm.provider.get_settings") as mock_settings:
            mock_settings.return_value.llm_provider = LLMProvider.OLLAMA
            mock_settings.return_value.current_model = "llama3.2"
            mock_settings.return_value.ollama.base_url = "http://localhost:11434"
            mock_settings.return_value.ollama.model = "llama3.2"
            mock_settings.return_value.ollama.temperature = 0.7
            mock_settings.return_value.ollama.num_ctx = 4096
            mock_settings.return_value.ollama.timeout = 120
            
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.get.return_value.status_code = 200
                mock_client.get.return_value.json.return_value = {
                    "models": [{"name": "llama3.2"}]
                }
                mock_client.get.return_value.raise_for_status = MagicMock()
                MockClient.return_value.__aenter__.return_value = mock_client
                
                result = await check_llm_availability()
                
                assert result["provider"] == "ollama"
                assert result["available"] is True
                assert "available_models" in result
