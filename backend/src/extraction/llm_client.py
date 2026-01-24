"""Gemini API client for structured data extraction from loan documents.

This module provides a production-ready Gemini client with:
- Structured output support using Pydantic schemas
- Retry logic with exponential backoff for rate limiting
- Token usage tracking and latency metrics
- Both sync and async extraction methods

Key patterns:
- Temperature=1.0 (Gemini 3 requires this for optimal performance)
- No max_output_tokens (causes None response with structured output)
- response_json_schema for guaranteed valid JSON
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from google import genai
from google.genai import errors, types
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

if TYPE_CHECKING:
    from google.genai.types import GenerateContentResponse


def _get_token_counts(response: "GenerateContentResponse") -> tuple[int, int]:
    """Safely extract token counts from response, handling None values.

    Args:
        response: The Gemini API response

    Returns:
        Tuple of (input_tokens, output_tokens), defaulting to 0 if unavailable
    """
    if response.usage_metadata is None:
        return 0, 0

    input_tokens = response.usage_metadata.prompt_token_count or 0
    output_tokens = response.usage_metadata.candidates_token_count or 0
    return input_tokens, output_tokens


@dataclass
class LLMResponse:
    """Structured response from LLM extraction.

    Attributes:
        content: Raw response text (empty string if truncated)
        parsed: Parsed Pydantic model (None if truncated)
        input_tokens: Input token count
        output_tokens: Output token count
        latency_ms: Request latency in milliseconds
        model_used: Model name that was called
        finish_reason: Why generation stopped (e.g., STOP, MAX_TOKENS)
    """

    content: str
    parsed: BaseModel | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model_used: str
    finish_reason: str


class GeminiClient:
    """Gemini API client with retry logic and structured output support.

    Uses the google-genai SDK to call Gemini models for structured
    data extraction. Supports both Flash (default) and Pro models
    with automatic retry on rate limits and server errors.

    Example:
        client = GeminiClient()
        response = client.extract(
            text="Document text...",
            schema=BorrowerSchema,
            use_pro=False,
        )
        if response.parsed:
            print(response.parsed.name)
    """

    FLASH_MODEL = "gemini-3-flash-preview"
    PRO_MODEL = "gemini-3-pro-preview"

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Gemini client.

        Args:
            api_key: Optional API key. If not provided, uses GEMINI_API_KEY
                    or GOOGLE_API_KEY environment variable.
        """
        # Uses GEMINI_API_KEY or GOOGLE_API_KEY from environment if not provided
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    @retry(
        wait=wait_exponential_jitter(initial=1, max=60, jitter=5),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(errors.APIError),
    )
    def extract(
        self,
        text: str,
        schema: type[BaseModel],
        use_pro: bool = False,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        """Extract structured data from text using Gemini.

        Args:
            text: Document text to extract from
            schema: Pydantic model defining expected output structure
            use_pro: Use Pro model for complex documents (default: Flash)
            system_instruction: Optional system prompt for extraction context

        Returns:
            LLMResponse with parsed data and usage metrics

        Raises:
            errors.APIError: On API errors after retries exhausted
        """
        model = self.PRO_MODEL if use_pro else self.FLASH_MODEL
        start_time = time.perf_counter()

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=1.0,  # CRITICAL: Gemini 3 needs temp=1.0
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
            # Don't set max_output_tokens - causes None with structured output
        )

        response = self.client.models.generate_content(
            model=model,
            contents=text,
            config=config,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract token counts safely
        input_tokens, output_tokens = _get_token_counts(response)

        # Handle None response (can happen when output truncated)
        if response.text is None:
            return LLMResponse(
                content="",
                parsed=None,
                input_tokens=input_tokens,
                output_tokens=0,
                latency_ms=latency_ms,
                model_used=model,
                finish_reason="MAX_TOKENS",
            )

        # Parse response into Pydantic model
        parsed = schema.model_validate_json(response.text)

        # Safely get finish_reason
        finish_reason = "UNKNOWN"
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.finish_reason:
                finish_reason = candidate.finish_reason.name

        return LLMResponse(
            content=response.text,
            parsed=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model_used=model,
            finish_reason=finish_reason,
        )

    async def extract_async(
        self,
        text: str,
        schema: type[BaseModel],
        use_pro: bool = False,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        """Async version of extract using client.aio.

        Args:
            text: Document text to extract from
            schema: Pydantic model defining expected output structure
            use_pro: Use Pro model for complex documents (default: Flash)
            system_instruction: Optional system prompt for extraction context

        Returns:
            LLMResponse with parsed data and usage metrics
        """
        model = self.PRO_MODEL if use_pro else self.FLASH_MODEL
        start_time = time.perf_counter()

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=1.0,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
        )

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=text,
            config=config,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract token counts safely
        input_tokens, output_tokens = _get_token_counts(response)

        if response.text is None:
            return LLMResponse(
                content="",
                parsed=None,
                input_tokens=input_tokens,
                output_tokens=0,
                latency_ms=latency_ms,
                model_used=model,
                finish_reason="MAX_TOKENS",
            )

        parsed = schema.model_validate_json(response.text)

        # Safely get finish_reason
        finish_reason = "UNKNOWN"
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.finish_reason:
                finish_reason = candidate.finish_reason.name

        return LLMResponse(
            content=response.text,
            parsed=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model_used=model,
            finish_reason=finish_reason,
        )
