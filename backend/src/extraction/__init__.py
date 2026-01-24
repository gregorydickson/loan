"""LLM-based extraction and validation components.

This package provides the complete borrower extraction pipeline:
- GeminiClient: LLM client for structured data extraction
- ComplexityClassifier: Routes documents to appropriate model
- DocumentChunker: Splits large documents for processing
- FieldValidator: Validates extracted field formats
- ConfidenceCalculator: Scores extraction confidence
- BorrowerDeduplicator: Merges duplicate borrower records
- BorrowerExtractor: Orchestrates the full pipeline
"""

from src.extraction.chunker import DocumentChunker, TextChunk
from src.extraction.complexity_classifier import (
    ComplexityAssessment,
    ComplexityClassifier,
    ComplexityLevel,
)
from src.extraction.confidence import ConfidenceBreakdown, ConfidenceCalculator
from src.extraction.deduplication import BorrowerDeduplicator
from src.extraction.extractor import BorrowerExtractor, ExtractionResult
from src.extraction.llm_client import GeminiClient, LLMResponse
from src.extraction.schemas import (
    BorrowerExtractionResult,
    ExtractedAddress,
    ExtractedBorrower,
    ExtractedIncome,
)
from src.extraction.validation import FieldValidator, ValidationError, ValidationResult

__all__ = [
    # LLM Client
    "GeminiClient",
    "LLMResponse",
    # Complexity Classification
    "ComplexityClassifier",
    "ComplexityAssessment",
    "ComplexityLevel",
    # Document Chunking
    "DocumentChunker",
    "TextChunk",
    # Validation
    "FieldValidator",
    "ValidationResult",
    "ValidationError",
    # Confidence Scoring
    "ConfidenceCalculator",
    "ConfidenceBreakdown",
    # Deduplication
    "BorrowerDeduplicator",
    # Extraction Schemas
    "ExtractedBorrower",
    "ExtractedAddress",
    "ExtractedIncome",
    "BorrowerExtractionResult",
    # Main Extractor
    "BorrowerExtractor",
    "ExtractionResult",
]
