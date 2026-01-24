"""LLM extraction module for borrower data extraction.

This module provides the core LLM client and extraction utilities
for extracting structured borrower data from loan documents.

Main exports:
- GeminiClient: Gemini API client with retry logic and structured output
- LLMResponse: Dataclass for extraction results with metrics
"""

from src.extraction.llm_client import GeminiClient, LLMResponse

__all__ = ["GeminiClient", "LLMResponse"]
