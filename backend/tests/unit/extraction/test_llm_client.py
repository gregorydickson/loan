"""Unit tests for Gemini LLM client.

Tests Gemini API client with mocked responses:
- Client initialization
- Structured extraction with schemas
- Model selection (Flash vs Pro)
- Token counting and metrics
- Error handling and retries
- Async extraction
- Response parsing
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.extraction.llm_client import GeminiClient, LLMResponse, _get_token_counts


# Test schemas for extraction
class SimpleSchema(BaseModel):
    """Simple test schema."""

    name: str
    value: int


class TestGetTokenCounts:
    """Tests for _get_token_counts helper function."""

    def test_extracts_token_counts_from_response(self):
        """Extracts token counts from valid response."""
        response = MagicMock()
        response.usage_metadata = MagicMock()
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = 50

        input_tokens, output_tokens = _get_token_counts(response)
        assert input_tokens == 100
        assert output_tokens == 50

    def test_handles_none_usage_metadata(self):
        """Returns (0, 0) when usage_metadata is None."""
        response = MagicMock()
        response.usage_metadata = None

        input_tokens, output_tokens = _get_token_counts(response)
        assert input_tokens == 0
        assert output_tokens == 0

    def test_handles_none_token_counts(self):
        """Returns 0 for None token counts."""
        response = MagicMock()
        response.usage_metadata = MagicMock()
        response.usage_metadata.prompt_token_count = None
        response.usage_metadata.candidates_token_count = None

        input_tokens, output_tokens = _get_token_counts(response)
        assert input_tokens == 0
        assert output_tokens == 0

    def test_handles_partial_none_counts(self):
        """Handles when only one count is None."""
        response = MagicMock()
        response.usage_metadata = MagicMock()
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = None

        input_tokens, output_tokens = _get_token_counts(response)
        assert input_tokens == 100
        assert output_tokens == 0


class TestGeminiClientInitialization:
    """Tests for GeminiClient initialization."""

    @patch("src.extraction.llm_client.genai.Client")
    def test_creates_client_without_api_key(self, mock_client_class):
        """Creates client using environment variable."""
        client = GeminiClient()
        mock_client_class.assert_called_once_with()

    @patch("src.extraction.llm_client.genai.Client")
    def test_creates_client_with_api_key(self, mock_client_class):
        """Creates client with provided API key."""
        api_key = "test-api-key-123"
        client = GeminiClient(api_key=api_key)
        mock_client_class.assert_called_once_with(api_key=api_key)


class TestExtractBasics:
    """Tests for basic extract functionality."""

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_returns_llm_response(self, mock_client_class):
        """Extract returns LLMResponse with parsed data."""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = MagicMock()
        mock_response.candidates[0].finish_reason.name = "STOP"

        mock_client.models.generate_content.return_value = mock_response

        # Test
        client = GeminiClient()
        result = client.extract(
            text="Extract from this text",
            schema=SimpleSchema,
            use_pro=False,
        )

        # Assertions
        assert isinstance(result, LLMResponse)
        assert result.parsed.name == "John"
        assert result.parsed.value == 42
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.model_used == "gemini-3-flash-preview"
        assert result.finish_reason == "STOP"
        assert result.latency_ms > 0

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_uses_flash_by_default(self, mock_client_class):
        """Extract uses Flash model by default."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = None
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.extract(
            text="Test text",
            schema=SimpleSchema,
        )

        # Check model used
        call_args = mock_client.models.generate_content.call_args
        assert call_args[1]["model"] == "gemini-3-flash-preview"

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_uses_pro_when_requested(self, mock_client_class):
        """Extract uses Pro model when use_pro=True."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = None
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.extract(
            text="Test text",
            schema=SimpleSchema,
            use_pro=True,
        )

        # Check model used
        call_args = mock_client.models.generate_content.call_args
        assert call_args[1]["model"] == "gemini-3-pro-preview"


class TestExtractConfiguration:
    """Tests for extract configuration options."""

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_uses_temperature_1(self, mock_client_class):
        """Extract uses temperature=1.0 (Gemini 3 requirement)."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = None
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        client.extract(text="Test", schema=SimpleSchema)

        # Check config
        call_args = mock_client.models.generate_content.call_args
        config = call_args[1]["config"]
        assert config.temperature == 1.0

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_includes_system_instruction(self, mock_client_class):
        """Extract includes system instruction in config."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = None
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        system_prompt = "You are a data extractor"
        client.extract(
            text="Test",
            schema=SimpleSchema,
            system_instruction=system_prompt,
        )

        # Check config
        call_args = mock_client.models.generate_content.call_args
        config = call_args[1]["config"]
        assert config.system_instruction == system_prompt

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_uses_json_schema(self, mock_client_class):
        """Extract uses response_json_schema for structured output."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = None
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        client.extract(text="Test", schema=SimpleSchema)

        # Check config
        call_args = mock_client.models.generate_content.call_args
        config = call_args[1]["config"]
        assert config.response_mime_type == "application/json"
        assert config.response_json_schema is not None


class TestExtractNoneResponse:
    """Tests for handling None response (truncation)."""

    @patch("src.extraction.llm_client.genai.Client")
    def test_none_response_returns_truncation(self, mock_client_class):
        """None response returns LLMResponse with parsed=None."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = None  # Truncated response
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 0
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.extract(text="Test", schema=SimpleSchema)

        assert result.content == ""
        assert result.parsed is None
        assert result.input_tokens == 100
        assert result.output_tokens == 0
        assert result.finish_reason == "MAX_TOKENS"

    @patch("src.extraction.llm_client.genai.Client")
    def test_none_response_with_none_usage(self, mock_client_class):
        """None response with None usage_metadata handled."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = None
        mock_response.usage_metadata = None
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.extract(text="Test", schema=SimpleSchema)

        assert result.parsed is None
        assert result.input_tokens == 0
        assert result.output_tokens == 0


class TestExtractFinishReason:
    """Tests for finish_reason extraction."""

    @patch("src.extraction.llm_client.genai.Client")
    def test_extracts_finish_reason_from_candidate(self, mock_client_class):
        """Extracts finish_reason from first candidate."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = None
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = MagicMock()
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.extract(text="Test", schema=SimpleSchema)

        assert result.finish_reason == "STOP"

    @patch("src.extraction.llm_client.genai.Client")
    def test_finish_reason_unknown_without_candidates(self, mock_client_class):
        """finish_reason is UNKNOWN when no candidates."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = None
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.extract(text="Test", schema=SimpleSchema)

        assert result.finish_reason == "UNKNOWN"

    @patch("src.extraction.llm_client.genai.Client")
    def test_finish_reason_unknown_when_none(self, mock_client_class):
        """finish_reason is UNKNOWN when candidate.finish_reason is None."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "John", "value": 42}'
        mock_response.usage_metadata = None
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = None
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.extract(text="Test", schema=SimpleSchema)

        assert result.finish_reason == "UNKNOWN"


class TestExtractAsync:
    """Tests for async extract_async method."""

    @pytest.mark.asyncio
    @patch("src.extraction.llm_client.genai.Client")
    async def test_extract_async_returns_llm_response(self, mock_client_class):
        """extract_async returns LLMResponse with parsed data."""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"name": "Alice", "value": 99}'
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 10
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = MagicMock()
        mock_response.candidates[0].finish_reason.name = "STOP"

        # Mock async method
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        # Test
        client = GeminiClient()
        result = await client.extract_async(
            text="Extract from this text",
            schema=SimpleSchema,
            use_pro=False,
        )

        # Assertions
        assert isinstance(result, LLMResponse)
        assert result.parsed.name == "Alice"
        assert result.parsed.value == 99
        assert result.input_tokens == 20
        assert result.output_tokens == 10
        assert result.model_used == "gemini-3-flash-preview"

    @pytest.mark.asyncio
    @patch("src.extraction.llm_client.genai.Client")
    async def test_extract_async_handles_none_response(self, mock_client_class):
        """extract_async handles None response (truncation)."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = None
        mock_response.usage_metadata = None

        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        client = GeminiClient()
        result = await client.extract_async(text="Test", schema=SimpleSchema)

        assert result.parsed is None
        assert result.finish_reason == "MAX_TOKENS"


class TestLLMResponseDataclass:
    """Tests for LLMResponse dataclass."""

    def test_llm_response_has_all_fields(self):
        """LLMResponse contains all required fields."""
        parsed = SimpleSchema(name="Test", value=123)
        response = LLMResponse(
            content='{"name": "Test", "value": 123}',
            parsed=parsed,
            input_tokens=100,
            output_tokens=50,
            latency_ms=250,
            model_used="gemini-3-flash-preview",
            finish_reason="STOP",
        )

        assert response.content == '{"name": "Test", "value": 123}'
        assert response.parsed.name == "Test"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.latency_ms == 250
        assert response.model_used == "gemini-3-flash-preview"
        assert response.finish_reason == "STOP"


class TestModelConstants:
    """Tests for model name constants."""

    def test_flash_model_constant(self):
        """FLASH_MODEL constant defined."""
        assert GeminiClient.FLASH_MODEL == "gemini-3-flash-preview"

    def test_pro_model_constant(self):
        """PRO_MODEL constant defined."""
        assert GeminiClient.PRO_MODEL == "gemini-3-pro-preview"
