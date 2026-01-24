"""Unit tests for the Gemini LLM client.

Tests cover:
- Client initialization (with/without API key)
- Model selection (Flash vs Pro)
- Response parsing into Pydantic models
- None response handling (truncated output)
- Retry logic on API errors
- Token usage tracking
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from src.extraction.llm_client import GeminiClient, LLMResponse


# Test schema for extraction (prefixed with Sample to avoid pytest collection)
class SampleBorrower(BaseModel):
    """Simple test schema for extraction tests."""

    name: str
    age: int | None = None


class SampleExtractionResult(BaseModel):
    """Container for extraction results."""

    borrowers: list[SampleBorrower] = []


def create_mock_response(
    text: str | None = '{"name": "John Doe", "age": 35}',
    prompt_tokens: int = 100,
    candidate_tokens: int = 50,
    finish_reason: str = "STOP",
) -> MagicMock:
    """Create a mock Gemini API response.

    Args:
        text: Response text (None simulates truncated output)
        prompt_tokens: Input token count
        candidate_tokens: Output token count
        finish_reason: Finish reason (STOP, MAX_TOKENS, etc.)

    Returns:
        MagicMock configured as Gemini response
    """
    mock_response = MagicMock()
    mock_response.text = text

    # Mock usage_metadata
    mock_response.usage_metadata = MagicMock()
    mock_response.usage_metadata.prompt_token_count = prompt_tokens
    mock_response.usage_metadata.candidates_token_count = candidate_tokens

    # Mock candidates with finish_reason
    mock_candidate = MagicMock()
    mock_candidate.finish_reason = MagicMock()
    mock_candidate.finish_reason.name = finish_reason
    mock_response.candidates = [mock_candidate]

    return mock_response


class TestGeminiClientInit:
    """Tests for GeminiClient initialization."""

    @patch("src.extraction.llm_client.genai.Client")
    def test_gemini_client_init_default(self, mock_client_class: MagicMock) -> None:
        """Verify client initializes without API key (uses env)."""
        client = GeminiClient()

        # Should call genai.Client() without api_key arg
        mock_client_class.assert_called_once_with()
        assert client.client is not None

    @patch("src.extraction.llm_client.genai.Client")
    def test_gemini_client_init_with_key(self, mock_client_class: MagicMock) -> None:
        """Verify client accepts explicit API key."""
        api_key = "test-api-key-12345"
        client = GeminiClient(api_key=api_key)

        # Should call genai.Client(api_key=api_key)
        mock_client_class.assert_called_once_with(api_key=api_key)
        assert client.client is not None


class TestGeminiClientExtract:
    """Tests for GeminiClient.extract method."""

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_returns_llm_response(self, mock_client_class: MagicMock) -> None:
        """Mock successful response, verify LLMResponse fields."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = create_mock_response(
            text='{"name": "Jane Doe", "age": 28}',
            prompt_tokens=150,
            candidate_tokens=75,
            finish_reason="STOP",
        )
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        response = client.extract(
            text="Test document content",
            schema=SampleBorrower,
        )

        assert isinstance(response, LLMResponse)
        assert response.content == '{"name": "Jane Doe", "age": 28}'
        assert response.parsed is not None
        assert isinstance(response.parsed, SampleBorrower)
        assert response.parsed.name == "Jane Doe"
        assert response.parsed.age == 28
        assert response.input_tokens == 150
        assert response.output_tokens == 75
        assert response.latency_ms >= 0
        assert response.finish_reason == "STOP"

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_uses_flash_by_default(self, mock_client_class: MagicMock) -> None:
        """Verify FLASH_MODEL used when use_pro=False."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = create_mock_response()

        client = GeminiClient()
        response = client.extract(
            text="Test content",
            schema=SampleBorrower,
            use_pro=False,
        )

        # Verify the model parameter
        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == GeminiClient.FLASH_MODEL
        assert response.model_used == GeminiClient.FLASH_MODEL

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_uses_pro_when_requested(self, mock_client_class: MagicMock) -> None:
        """Verify PRO_MODEL used when use_pro=True."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = create_mock_response()

        client = GeminiClient()
        response = client.extract(
            text="Test content",
            schema=SampleBorrower,
            use_pro=True,
        )

        # Verify the model parameter
        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == GeminiClient.PRO_MODEL
        assert response.model_used == GeminiClient.PRO_MODEL

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_handles_none_response(self, mock_client_class: MagicMock) -> None:
        """Mock None text response, verify parsed=None and finish_reason=MAX_TOKENS."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = create_mock_response(
            text=None,  # Simulates truncated output
            prompt_tokens=500,
            candidate_tokens=0,
        )
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        response = client.extract(
            text="Test content",
            schema=SampleBorrower,
        )

        assert response.content == ""
        assert response.parsed is None
        assert response.finish_reason == "MAX_TOKENS"
        assert response.input_tokens == 500
        assert response.output_tokens == 0

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_parses_pydantic_model(self, mock_client_class: MagicMock) -> None:
        """Verify JSON response parsed into Pydantic model."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = create_mock_response(
            text='{"borrowers": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": null}]}'
        )
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiClient()
        response = client.extract(
            text="Test content",
            schema=SampleExtractionResult,
        )

        assert response.parsed is not None
        assert isinstance(response.parsed, SampleExtractionResult)
        assert len(response.parsed.borrowers) == 2
        assert response.parsed.borrowers[0].name == "Alice"
        assert response.parsed.borrowers[0].age == 30
        assert response.parsed.borrowers[1].name == "Bob"
        assert response.parsed.borrowers[1].age is None

    @patch("src.extraction.llm_client.genai.Client")
    def test_extract_passes_system_instruction(self, mock_client_class: MagicMock) -> None:
        """Verify system_instruction is passed to config."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = create_mock_response()

        client = GeminiClient()
        system_prompt = "You are a loan document extraction specialist."
        client.extract(
            text="Test content",
            schema=SampleBorrower,
            system_instruction=system_prompt,
        )

        # Verify system_instruction in config
        call_kwargs = mock_client.models.generate_content.call_args
        config = call_kwargs.kwargs["config"]
        assert config.system_instruction == system_prompt


class TestGeminiClientRetry:
    """Tests for retry logic on API errors."""

    @patch("src.extraction.llm_client.genai.Client")
    def test_retry_on_api_error(self, mock_client_class: MagicMock) -> None:
        """Mock APIError, verify retry is triggered."""
        from google.genai import errors

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # First call raises APIError (429 rate limit), second succeeds
        # APIError requires: code (int), response_json (dict with 'error.message' or 'message')
        mock_client.models.generate_content.side_effect = [
            errors.APIError(code=429, response_json={"message": "Rate limited"}),
            create_mock_response(),
        ]

        client = GeminiClient()
        response = client.extract(
            text="Test content",
            schema=SampleBorrower,
        )

        # Should have been called twice (1 failure + 1 success)
        assert mock_client.models.generate_content.call_count == 2
        assert response.parsed is not None

    @patch("src.extraction.llm_client.genai.Client")
    def test_retry_exhausted_raises(self, mock_client_class: MagicMock) -> None:
        """Verify exception raised after retries exhausted."""
        from google.genai import errors
        from tenacity import RetryError

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # All calls raise APIError (500 server error)
        # APIError requires: code (int), response_json (dict with 'error.message' or 'message')
        mock_client.models.generate_content.side_effect = errors.APIError(
            code=500, response_json={"message": "Server error"}
        )

        client = GeminiClient()

        # Tenacity wraps exhausted retries in RetryError
        with pytest.raises(RetryError):
            client.extract(
                text="Test content",
                schema=SampleBorrower,
            )

        # Should have retried 3 times (configured stop_after_attempt)
        assert mock_client.models.generate_content.call_count == 3


class TestGeminiClientAsync:
    """Tests for async extract method."""

    @pytest.mark.asyncio
    @patch("src.extraction.llm_client.genai.Client")
    async def test_extract_async_returns_llm_response(
        self, mock_client_class: MagicMock
    ) -> None:
        """Verify async extract returns correct LLMResponse."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = create_mock_response(
            text='{"name": "Async Test", "age": 42}',
            prompt_tokens=200,
            candidate_tokens=100,
        )

        # Mock the async method
        async def mock_generate(*args, **kwargs):
            return mock_response

        mock_client.aio.models.generate_content = mock_generate

        client = GeminiClient()
        response = await client.extract_async(
            text="Test async content",
            schema=SampleBorrower,
        )

        assert isinstance(response, LLMResponse)
        assert response.parsed is not None
        assert response.parsed.name == "Async Test"
        assert response.parsed.age == 42
        assert response.input_tokens == 200
        assert response.output_tokens == 100

    @pytest.mark.asyncio
    @patch("src.extraction.llm_client.genai.Client")
    async def test_extract_async_handles_none_response(
        self, mock_client_class: MagicMock
    ) -> None:
        """Verify async extract handles None response."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = create_mock_response(text=None, prompt_tokens=300)

        async def mock_generate(*args, **kwargs):
            return mock_response

        mock_client.aio.models.generate_content = mock_generate

        client = GeminiClient()
        response = await client.extract_async(
            text="Test async content",
            schema=SampleBorrower,
        )

        assert response.parsed is None
        assert response.finish_reason == "MAX_TOKENS"
        assert response.content == ""


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_llm_response_creation(self) -> None:
        """Verify LLMResponse can be created with all fields."""
        parsed_model = SampleBorrower(name="Test", age=25)

        response = LLMResponse(
            content='{"name": "Test", "age": 25}',
            parsed=parsed_model,
            input_tokens=100,
            output_tokens=50,
            latency_ms=250,
            model_used="gemini-3-flash-preview",
            finish_reason="STOP",
        )

        assert response.content == '{"name": "Test", "age": 25}'
        assert response.parsed == parsed_model
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.latency_ms == 250
        assert response.model_used == "gemini-3-flash-preview"
        assert response.finish_reason == "STOP"

    def test_llm_response_with_none_parsed(self) -> None:
        """Verify LLMResponse handles None parsed field."""
        response = LLMResponse(
            content="",
            parsed=None,
            input_tokens=100,
            output_tokens=0,
            latency_ms=150,
            model_used="gemini-3-flash-preview",
            finish_reason="MAX_TOKENS",
        )

        assert response.parsed is None
        assert response.finish_reason == "MAX_TOKENS"
