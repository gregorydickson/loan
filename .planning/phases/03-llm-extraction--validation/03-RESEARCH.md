# Phase 3: LLM Extraction & Validation - Research

**Researched:** 2026-01-23
**Domain:** LLM extraction (Gemini 3.0), structured output, document complexity classification, data validation, confidence scoring
**Confidence:** HIGH

---

## Summary

This research covers the LLM extraction and validation layer for extracting structured borrower data from loan documents using Google's Gemini 3.0 models. The key components are: the google-genai SDK (v1.60.0+) for Gemini API access, complexity-based model routing (Flash for standard documents, Pro for complex), structured output with Pydantic schemas, document chunking for large texts, confidence scoring based on field completeness and validation, and format validation for SSN, phone, and zip codes.

The standard approach uses the `google-genai` SDK's `generate_content` method with `response_mime_type="application/json"` and `response_json_schema` for structured extraction. Critical findings include: (1) Gemini 3 models return `None` when `max_output_tokens` is exceeded with structured output - handle with generous limits or chunking; (2) `Field(default=...)` in Pydantic causes issues - use Optional types instead; (3) temperature should stay at 1.0 for Gemini 3 models; (4) tenacity library provides production-ready retry with exponential backoff and jitter.

**Primary recommendation:** Use `gemini-3-flash-preview` as default (75% cheaper, 3x faster), route to `gemini-3-pro-preview` only for complex multi-borrower documents or poor scan quality. Implement chunking at 4000 tokens with 200-token overlap. Calculate confidence scores based on field completeness, format validation, and multi-source confirmation. Use RapidFuzz for name deduplication with 90%+ threshold.

---

## Standard Stack

The established libraries/tools for this domain (versions from pyproject.toml):

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | 1.60.0+ | Gemini API client | Official SDK with structured output, async support, native Pydantic |
| tenacity | 9.0.0+ | Retry logic | Production-ready exponential backoff with jitter |
| rapidfuzz | 3.x | Fuzzy matching | 10-15x faster than thefuzz, MIT license, C++ implementation |
| phonenumbers | 8.x | Phone validation | Google's libphonenumber port, comprehensive US format support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.12.0+ | Schema validation | Extraction schemas, validation models |
| hashlib | stdlib | Hashing | SSN hashing for storage (never store raw SSN) |
| re | stdlib | Regex validation | SSN, zip code format checking |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Gemini 3 Flash | Gemini 3 Pro | Pro has deeper reasoning but 4-8x cost; Flash beats Pro on coding benchmarks |
| RapidFuzz | TheFuzz | TheFuzz has GPL license, 10-15x slower; API identical |
| phonenumbers | Regex only | phonenumbers handles all US formats, international; regex fragile |
| tenacity | manual retry | tenacity battle-tested, configurable; manual error-prone |

**Installation:**
Already in Phase 1 pyproject.toml. Add to dev dependencies:
```bash
pip install rapidfuzz phonenumbers  # Add to pyproject.toml if not present
```

---

## Architecture Patterns

### Recommended Project Structure
```
backend/src/
├── extraction/
│   ├── __init__.py
│   ├── llm_client.py           # Gemini client with retry logic
│   ├── complexity_classifier.py # Document complexity assessment
│   ├── prompts.py              # Extraction prompt templates
│   ├── extractor.py            # Orchestrator: chunk, extract, aggregate
│   ├── confidence.py           # Confidence score calculation
│   └── validation.py           # Format validation (SSN, phone, etc.)
├── models/
│   ├── borrower.py             # (from Phase 1) - extraction output schema
│   └── document.py             # (from Phase 1) - source references
└── ingestion/
    └── docling_processor.py    # (from Phase 2) - provides DocumentContent
```

### Pattern 1: Gemini Client with Structured Output
**What:** Wrap google-genai client for structured JSON extraction
**When to use:** All LLM extraction calls
**Example:**
```python
# Source: https://ai.google.dev/gemini-api/docs/structured-output
from google import genai
from google.genai import types
from google.genai import errors
from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)
from dataclasses import dataclass
import time


@dataclass
class LLMResponse:
    """Structured response from LLM extraction."""
    content: str
    parsed: BaseModel | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model_used: str
    finish_reason: str


class GeminiClient:
    """Gemini API client with retry logic and structured output support."""

    FLASH_MODEL = "gemini-3-flash-preview"
    PRO_MODEL = "gemini-3-pro-preview"

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize client with API key or use environment variable."""
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
            system_instruction: Optional system prompt

        Returns:
            LLMResponse with parsed data and usage metrics
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

        try:
            response = self.client.models.generate_content(
                model=model,
                contents=text,
                config=config,
            )
        except errors.APIError as e:
            if e.code == 429:  # Rate limit
                raise  # Let tenacity handle retry
            raise

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Handle None response (can happen when output truncated)
        if response.text is None:
            return LLMResponse(
                content="",
                parsed=None,
                input_tokens=response.usage_metadata.prompt_token_count or 0,
                output_tokens=0,
                latency_ms=latency_ms,
                model_used=model,
                finish_reason="MAX_TOKENS",
            )

        # Parse response into Pydantic model
        parsed = schema.model_validate_json(response.text)

        return LLMResponse(
            content=response.text,
            parsed=parsed,
            input_tokens=response.usage_metadata.prompt_token_count or 0,
            output_tokens=response.usage_metadata.candidates_token_count or 0,
            latency_ms=latency_ms,
            model_used=model,
            finish_reason=response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN",
        )

    async def extract_async(
        self,
        text: str,
        schema: type[BaseModel],
        use_pro: bool = False,
        system_instruction: str | None = None,
    ) -> LLMResponse:
        """Async version of extract using client.aio."""
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

        if response.text is None:
            return LLMResponse(
                content="",
                parsed=None,
                input_tokens=response.usage_metadata.prompt_token_count or 0,
                output_tokens=0,
                latency_ms=latency_ms,
                model_used=model,
                finish_reason="MAX_TOKENS",
            )

        parsed = schema.model_validate_json(response.text)

        return LLMResponse(
            content=response.text,
            parsed=parsed,
            input_tokens=response.usage_metadata.prompt_token_count or 0,
            output_tokens=response.usage_metadata.candidates_token_count or 0,
            latency_ms=latency_ms,
            model_used=model,
            finish_reason=response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN",
        )
```

### Pattern 2: Document Complexity Classification
**What:** Heuristic-based classifier to route documents to appropriate model
**When to use:** Before extraction to select Flash vs Pro
**Example:**
```python
# Source: PRD requirements EXTRACT-11 through EXTRACT-15
from enum import Enum
from dataclasses import dataclass
import re


class ComplexityLevel(str, Enum):
    """Document complexity levels for model selection."""
    STANDARD = "standard"  # Use gemini-3-flash-preview
    COMPLEX = "complex"    # Use gemini-3-pro-preview


@dataclass
class ComplexityAssessment:
    """Result of complexity classification."""
    level: ComplexityLevel
    reasons: list[str]
    page_count: int
    estimated_borrowers: int
    has_handwritten: bool
    has_poor_quality: bool


class ComplexityClassifier:
    """Classifies document complexity for model selection.

    Heuristics based on:
    - Number of potential borrowers (names, SSN patterns)
    - Document length (page count)
    - Scan quality indicators
    - Handwritten content detection
    """

    # Patterns indicating multiple borrowers
    MULTI_BORROWER_PATTERNS = [
        r"co-borrower",
        r"joint\s+applicant",
        r"spouse",
        r"borrower\s+2",
        r"second\s+borrower",
    ]

    # Patterns indicating poor scan quality
    POOR_QUALITY_PATTERNS = [
        r"\[illegible\]",
        r"\[unclear\]",
        r"\?\?\?",
        r"[^\w\s]{5,}",  # Many consecutive special chars
    ]

    # Patterns indicating handwritten content
    HANDWRITTEN_PATTERNS = [
        r"\[handwritten\]",
        r"signature:",
        r"signed:",
    ]

    def classify(self, text: str, page_count: int) -> ComplexityAssessment:
        """Classify document complexity based on text and metadata.

        Args:
            text: Full document text (from Docling)
            page_count: Number of pages in document

        Returns:
            ComplexityAssessment with level and reasons
        """
        reasons: list[str] = []
        text_lower = text.lower()

        # Check for multiple borrowers
        borrower_indicators = sum(
            1 for pattern in self.MULTI_BORROWER_PATTERNS
            if re.search(pattern, text_lower)
        )
        estimated_borrowers = 1 + borrower_indicators

        if borrower_indicators > 0:
            reasons.append(f"Multiple borrower indicators found ({borrower_indicators})")

        # Check page count (>10 pages = complex)
        if page_count > 10:
            reasons.append(f"Large document ({page_count} pages)")

        # Check for poor scan quality
        poor_quality_count = sum(
            len(re.findall(pattern, text_lower))
            for pattern in self.POOR_QUALITY_PATTERNS
        )
        has_poor_quality = poor_quality_count > 3

        if has_poor_quality:
            reasons.append(f"Poor scan quality indicators ({poor_quality_count})")

        # Check for handwritten content
        handwritten_count = sum(
            len(re.findall(pattern, text_lower))
            for pattern in self.HANDWRITTEN_PATTERNS
        )
        has_handwritten = handwritten_count > 0

        if has_handwritten:
            reasons.append(f"Handwritten content detected ({handwritten_count})")

        # Determine complexity level
        level = ComplexityLevel.STANDARD
        if (
            estimated_borrowers > 1
            or page_count > 10
            or has_poor_quality
            or has_handwritten
        ):
            level = ComplexityLevel.COMPLEX

        return ComplexityAssessment(
            level=level,
            reasons=reasons if reasons else ["Standard single-borrower document"],
            page_count=page_count,
            estimated_borrowers=estimated_borrowers,
            has_handwritten=has_handwritten,
            has_poor_quality=has_poor_quality,
        )
```

### Pattern 3: Document Chunking with Overlap
**What:** Split large documents into overlapping chunks for extraction
**When to use:** Documents exceeding ~4000 tokens
**Example:**
```python
# Source: https://www.pinecone.io/learn/chunking-strategies/
from dataclasses import dataclass


@dataclass
class TextChunk:
    """A chunk of document text with position metadata."""
    text: str
    start_char: int
    end_char: int
    chunk_index: int
    total_chunks: int


class DocumentChunker:
    """Splits documents into overlapping chunks for LLM processing.

    Uses character-based chunking with paragraph-aware boundaries.
    """

    def __init__(
        self,
        max_chars: int = 16000,  # ~4000 tokens at 4 chars/token
        overlap_chars: int = 800,  # ~200 tokens overlap
    ) -> None:
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> list[TextChunk]:
        """Split text into overlapping chunks.

        Attempts to split on paragraph boundaries when possible.
        """
        if len(text) <= self.max_chars:
            return [TextChunk(
                text=text,
                start_char=0,
                end_char=len(text),
                chunk_index=0,
                total_chunks=1,
            )]

        chunks: list[TextChunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.max_chars, len(text))

            # Try to find paragraph boundary near end
            if end < len(text):
                # Look for paragraph break in last 20% of chunk
                search_start = end - int(self.max_chars * 0.2)
                para_break = text.rfind("\n\n", search_start, end)
                if para_break > start:
                    end = para_break + 2  # Include the newlines

            chunk_text = text[start:end]
            chunks.append(TextChunk(
                text=chunk_text,
                start_char=start,
                end_char=end,
                chunk_index=chunk_index,
                total_chunks=0,  # Updated after all chunks created
            ))

            # Move start with overlap
            if end >= len(text):
                break
            start = end - self.overlap_chars
            chunk_index += 1

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks
```

### Pattern 4: Confidence Score Calculation
**What:** Calculate extraction confidence based on field completeness and validation
**When to use:** After extraction to flag low-confidence records for review
**Example:**
```python
# Source: PRD requirements EXTRACT-25 through EXTRACT-29
from dataclasses import dataclass
from src.models.borrower import BorrowerRecord


@dataclass
class ConfidenceBreakdown:
    """Breakdown of confidence score components."""
    base_score: float
    required_fields_bonus: float
    optional_fields_bonus: float
    multi_source_bonus: float
    validation_bonus: float
    total: float
    requires_review: bool


class ConfidenceCalculator:
    """Calculates confidence scores for extracted borrower records.

    Formula:
    - Base: 0.5
    - +0.1 per complete required field (name, address) [max +0.2]
    - +0.05 per complete optional field (income, accounts) [max +0.15]
    - +0.1 if multiple sources confirm same data
    - +0.15 if all format validations pass

    Range: 0.0 to 1.0
    Review threshold: < 0.7
    """

    REVIEW_THRESHOLD = 0.7
    BASE_SCORE = 0.5

    def calculate(
        self,
        record: BorrowerRecord,
        format_validation_passed: bool,
        source_count: int,
    ) -> ConfidenceBreakdown:
        """Calculate confidence score for a borrower record.

        Args:
            record: Extracted borrower record
            format_validation_passed: Whether all format validations passed
            source_count: Number of sources confirming this record

        Returns:
            ConfidenceBreakdown with score components
        """
        # Required fields: name, address
        required_bonus = 0.0
        if record.name and len(record.name) > 1:
            required_bonus += 0.1
        if record.address is not None:
            required_bonus += 0.1

        # Optional fields: income_history, account_numbers, loan_numbers
        optional_bonus = 0.0
        if record.income_history:
            optional_bonus += 0.05
        if record.account_numbers:
            optional_bonus += 0.05
        if record.loan_numbers:
            optional_bonus += 0.05
        optional_bonus = min(optional_bonus, 0.15)

        # Multi-source confirmation
        multi_source_bonus = 0.1 if source_count > 1 else 0.0

        # Format validation bonus
        validation_bonus = 0.15 if format_validation_passed else 0.0

        total = min(
            self.BASE_SCORE
            + required_bonus
            + optional_bonus
            + multi_source_bonus
            + validation_bonus,
            1.0
        )

        return ConfidenceBreakdown(
            base_score=self.BASE_SCORE,
            required_fields_bonus=required_bonus,
            optional_fields_bonus=optional_bonus,
            multi_source_bonus=multi_source_bonus,
            validation_bonus=validation_bonus,
            total=total,
            requires_review=total < self.REVIEW_THRESHOLD,
        )
```

### Pattern 5: Format Validation with Error Tracking
**What:** Validate SSN, phone, zip formats with detailed error tracking
**When to use:** Post-extraction validation
**Example:**
```python
# Source: PRD requirements VALID-01 through VALID-06
import re
from dataclasses import dataclass, field
from typing import Literal

# Optional: import phonenumbers for robust phone validation
try:
    import phonenumbers
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False


@dataclass
class ValidationError:
    """A single validation error."""
    field: str
    value: str
    error_type: str
    message: str


@dataclass
class ValidationResult:
    """Result of validation checks."""
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class FieldValidator:
    """Validates extracted field formats."""

    # SSN: XXX-XX-XXXX (with or without dashes)
    SSN_PATTERN = re.compile(r"^\d{3}-?\d{2}-?\d{4}$")
    SSN_FORMATTED = re.compile(r"^\d{3}-\d{2}-\d{4}$")

    # ZIP: XXXXX or XXXXX-XXXX
    ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")

    # US Phone (basic): allows various formats
    # NANP: area code and exchange cannot start with 0 or 1
    PHONE_BASIC = re.compile(
        r"^(?:\+?1[-.\s]?)?"  # Optional country code
        r"(?:\(?\d{3}\)?[-.\s]?)"  # Area code
        r"\d{3}[-.\s]?\d{4}$"  # Number
    )

    def validate_ssn(self, ssn: str | None) -> ValidationResult:
        """Validate SSN format (XXX-XX-XXXX)."""
        if ssn is None:
            return ValidationResult(is_valid=True)  # Optional field

        if not self.SSN_PATTERN.match(ssn):
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="ssn",
                    value=ssn,
                    error_type="FORMAT",
                    message="SSN must be in XXX-XX-XXXX format",
                )],
            )

        # Warn if not formatted with dashes
        if not self.SSN_FORMATTED.match(ssn):
            return ValidationResult(
                is_valid=True,
                warnings=["SSN should use XXX-XX-XXXX format with dashes"],
            )

        return ValidationResult(is_valid=True)

    def validate_phone(self, phone: str | None) -> ValidationResult:
        """Validate US phone number format."""
        if phone is None:
            return ValidationResult(is_valid=True)

        # Use phonenumbers library if available
        if HAS_PHONENUMBERS:
            try:
                parsed = phonenumbers.parse(phone, "US")
                if not phonenumbers.is_valid_number(parsed):
                    return ValidationResult(
                        is_valid=False,
                        errors=[ValidationError(
                            field="phone",
                            value=phone,
                            error_type="INVALID",
                            message="Phone number is not valid for US",
                        )],
                    )
                return ValidationResult(is_valid=True)
            except phonenumbers.NumberParseException:
                return ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        field="phone",
                        value=phone,
                        error_type="FORMAT",
                        message="Could not parse phone number",
                    )],
                )

        # Fallback to regex
        # Normalize: remove all non-digits
        digits = re.sub(r"\D", "", phone)

        # Should be 10 digits (or 11 with country code 1)
        if len(digits) == 11 and digits[0] == "1":
            digits = digits[1:]
        if len(digits) != 10:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="phone",
                    value=phone,
                    error_type="LENGTH",
                    message="US phone number must have 10 digits",
                )],
            )

        # NANP rules: area code and exchange can't start with 0 or 1
        if digits[0] in "01" or digits[3] in "01":
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="phone",
                    value=phone,
                    error_type="NANP",
                    message="Invalid US phone: area code/exchange cannot start with 0 or 1",
                )],
            )

        return ValidationResult(is_valid=True)

    def validate_zip(self, zip_code: str | None) -> ValidationResult:
        """Validate US ZIP code format (XXXXX or XXXXX-XXXX)."""
        if zip_code is None:
            return ValidationResult(is_valid=True)

        if not self.ZIP_PATTERN.match(zip_code):
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="zip_code",
                    value=zip_code,
                    error_type="FORMAT",
                    message="ZIP code must be XXXXX or XXXXX-XXXX format",
                )],
            )

        return ValidationResult(is_valid=True)
```

### Pattern 6: Fuzzy Name Deduplication
**What:** Deduplicate borrower records using fuzzy name matching
**When to use:** When aggregating results from multiple chunks or documents
**Example:**
```python
# Source: https://github.com/rapidfuzz/RapidFuzz
from rapidfuzz import fuzz, process, utils
from src.models.borrower import BorrowerRecord


class BorrowerDeduplicator:
    """Deduplicates borrower records using fuzzy matching.

    Priority:
    1. Exact SSN/account number match
    2. Fuzzy name match (>90%) + address match
    3. Name + last 4 of SSN/account
    """

    NAME_THRESHOLD = 90  # Fuzzy match threshold for names

    def deduplicate(self, records: list[BorrowerRecord]) -> list[BorrowerRecord]:
        """Merge duplicate borrower records.

        Args:
            records: List of extracted borrower records

        Returns:
            Deduplicated list with merged data
        """
        if not records:
            return []

        merged: list[BorrowerRecord] = []

        for record in records:
            match_found = False

            for i, existing in enumerate(merged):
                if self._is_duplicate(record, existing):
                    merged[i] = self._merge_records(existing, record)
                    match_found = True
                    break

            if not match_found:
                merged.append(record)

        return merged

    def _is_duplicate(self, a: BorrowerRecord, b: BorrowerRecord) -> bool:
        """Check if two records represent the same borrower."""
        # 1. Exact SSN match
        if a.ssn and b.ssn and a.ssn == b.ssn:
            return True

        # 2. Exact account number match
        common_accounts = set(a.account_numbers) & set(b.account_numbers)
        if common_accounts:
            return True

        # 3. Fuzzy name match + address similarity
        name_score = fuzz.token_sort_ratio(
            a.name.lower(),
            b.name.lower(),
            processor=utils.default_process,
        )

        if name_score >= self.NAME_THRESHOLD:
            # Check address if both have it
            if a.address and b.address:
                if a.address.zip_code == b.address.zip_code:
                    return True
            else:
                # High name match without address = probable duplicate
                return name_score >= 95

        # 4. Name + last 4 of SSN
        if a.ssn and b.ssn:
            if a.ssn[-4:] == b.ssn[-4:] and name_score >= 80:
                return True

        return False

    def _merge_records(
        self, existing: BorrowerRecord, new: BorrowerRecord
    ) -> BorrowerRecord:
        """Merge two records, preferring higher-confidence data."""
        # Keep the record with higher confidence as base
        if new.confidence_score > existing.confidence_score:
            base, other = new, existing
        else:
            base, other = existing, new

        # Merge lists (deduplicate)
        merged_income = list(base.income_history)
        for income in other.income_history:
            if income not in merged_income:
                merged_income.append(income)

        merged_accounts = list(set(base.account_numbers) | set(other.account_numbers))
        merged_loans = list(set(base.loan_numbers) | set(other.loan_numbers))
        merged_sources = list(base.sources) + [s for s in other.sources if s not in base.sources]

        return BorrowerRecord(
            id=base.id,
            name=base.name,
            ssn=base.ssn or other.ssn,
            phone=base.phone or other.phone,
            email=base.email or other.email,
            address=base.address or other.address,
            income_history=merged_income,
            account_numbers=merged_accounts,
            loan_numbers=merged_loans,
            sources=merged_sources,
            confidence_score=max(base.confidence_score, other.confidence_score),
            extracted_at=base.extracted_at,
        )
```

### Anti-Patterns to Avoid
- **Setting max_output_tokens with structured output:** Causes `None` response when limit exceeded. Either don't set it, or use generous limits and implement chunking.
- **Using Field(default=...) in Pydantic schemas for Gemini:** Known issue causes schema rejection. Use `Optional[T]` with `None` default instead.
- **Setting temperature < 1.0 for Gemini 3:** Official docs warn this causes looping/degraded performance. Keep at 1.0.
- **Reusing google-genai Client without context manager:** Can cause "client has been closed" errors. Use `with Client() as client:` or `async with Client().aio as aclient:`.
- **Storing raw SSN in database:** Always hash SSNs with SHA-256 for storage, only show masked version in UI.
- **Using thefuzz instead of rapidfuzz:** GPL license issues and 10-15x slower. API is identical.

---

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gemini API retry | try/except loops | tenacity with wait_exponential_jitter | Battle-tested, handles jitter, configurable |
| Phone validation | Regex patterns | phonenumbers library | Handles all US formats, NANP rules, international |
| Fuzzy name matching | Levenshtein from scratch | RapidFuzz | C++ optimized, 10-15x faster, multiple algorithms |
| Token counting | Character heuristics | client.models.count_tokens() | Accurate, model-specific tokenization |
| Structured output parsing | JSON parsing + validation | response_json_schema + Pydantic | Automatic schema enforcement, type safety |
| SSN masking | Manual string slicing | f"***-**-{ssn[-4:]}" | Consistent, prevents accidental exposure |

**Key insight:** The google-genai SDK handles most complexity - structured output, retries, async. Focus on business logic (complexity classification, confidence scoring, deduplication) rather than API plumbing.

---

## Common Pitfalls

### Pitfall 1: Gemini 3 Returns None with max_output_tokens
**What goes wrong:** `response.text` and `response.parsed` are `None` when output exceeds limit
**Why it happens:** Structured output mode truncates to empty rather than partial JSON
**How to avoid:**
- Don't set `max_output_tokens` for extraction tasks
- Use document chunking to keep prompts manageable
- If you must limit, set very high (e.g., 64000) and handle None gracefully
```python
if response.text is None:
    # Retry with smaller chunk or log for manual review
    pass
```
**Warning signs:** Intermittent None responses, especially on complex documents

### Pitfall 2: Pydantic Field(default=...) Rejected by Gemini
**What goes wrong:** Schema rejected with cryptic error about default values
**Why it happens:** Known issue #699 in googleapis/python-genai
**How to avoid:**
```python
# BAD: Causes schema rejection
class Borrower(BaseModel):
    name: str = Field(default="Unknown")

# GOOD: Use Optional with None
class Borrower(BaseModel):
    name: str | None = None
```
**Warning signs:** "Invalid schema" errors when using Field(default=...)

### Pitfall 3: Temperature < 1.0 Causes Looping
**What goes wrong:** Model loops infinitely or produces degraded output
**Why it happens:** Gemini 3 models optimized for temperature=1.0
**How to avoid:** Always use `temperature=1.0` (the default). If you need more deterministic output, use structured output constraints rather than temperature.
**Warning signs:** Repeated text, infinite generation, timeout errors

### Pitfall 4: Rate Limiting (429) Without Proper Backoff
**What goes wrong:** Requests fail repeatedly, no progress
**Why it happens:** Rate limits are per-project, not per-key; multiple apps share limit
**How to avoid:**
```python
from tenacity import retry, wait_exponential_jitter, stop_after_attempt

@retry(
    wait=wait_exponential_jitter(initial=1, max=60, jitter=5),
    stop=stop_after_attempt(5),
)
def call_gemini(...):
    ...
```
**Warning signs:** 429 errors, especially during batch processing

### Pitfall 5: SSN Stored in Plain Text
**What goes wrong:** PII exposure in database or logs
**Why it happens:** Treating SSN like any other field
**How to avoid:**
- Hash SSN with SHA-256 for storage (for deduplication)
- Never log full SSN
- Only store/display masked version: `***-**-1234`
```python
import hashlib
ssn_hash = hashlib.sha256(ssn.encode()).hexdigest()
```
**Warning signs:** SSN visible in logs, database dumps, or API responses

### Pitfall 6: Chunking Splits Data Entities
**What goes wrong:** Borrower info split across chunks, incomplete extraction
**Why it happens:** Fixed-size chunking without entity awareness
**How to avoid:**
- Use paragraph-boundary splitting
- Implement overlap (200 tokens recommended)
- Post-process: deduplicate and merge chunks
```python
# Look for natural breaks
para_break = text.rfind("\n\n", search_start, end)
if para_break > start:
    end = para_break + 2
```
**Warning signs:** Partial records, duplicate fields with slight variations

---

## Code Examples

Verified patterns from official sources:

### Complete Extraction Pipeline
```python
# Source: Combined from google-genai docs and PRD requirements
from uuid import UUID
from src.ingestion.docling_processor import DocumentContent
from src.models.borrower import BorrowerRecord
from src.models.document import SourceReference


class BorrowerExtractor:
    """Orchestrates borrower extraction from documents."""

    def __init__(
        self,
        llm_client: GeminiClient,
        classifier: ComplexityClassifier,
        chunker: DocumentChunker,
        validator: FieldValidator,
        confidence_calc: ConfidenceCalculator,
        deduplicator: BorrowerDeduplicator,
    ) -> None:
        self.llm_client = llm_client
        self.classifier = classifier
        self.chunker = chunker
        self.validator = validator
        self.confidence_calc = confidence_calc
        self.deduplicator = deduplicator

    def extract(
        self,
        document: DocumentContent,
        document_id: UUID,
        document_name: str,
    ) -> list[BorrowerRecord]:
        """Extract borrowers from a document.

        1. Classify complexity
        2. Chunk if needed
        3. Extract from each chunk
        4. Aggregate and deduplicate
        5. Validate and score confidence
        """
        # 1. Assess complexity
        assessment = self.classifier.classify(
            text=document.text,
            page_count=document.page_count,
        )
        use_pro = assessment.level == ComplexityLevel.COMPLEX

        # 2. Chunk document
        chunks = self.chunker.chunk(document.text)

        # 3. Extract from each chunk
        all_borrowers: list[BorrowerRecord] = []
        for chunk in chunks:
            # Find page number for this chunk
            page_number = self._find_page_for_position(document, chunk.start_char)

            response = self.llm_client.extract(
                text=chunk.text,
                schema=BorrowerExtractionResult,
                use_pro=use_pro,
                system_instruction=EXTRACTION_SYSTEM_PROMPT,
            )

            if response.parsed:
                for borrower in response.parsed.borrowers:
                    # Add source reference
                    borrower.sources.append(SourceReference(
                        document_id=document_id,
                        document_name=document_name,
                        page_number=page_number,
                        section=None,
                        snippet=chunk.text[:200],
                    ))
                    all_borrowers.append(borrower)

        # 4. Deduplicate
        merged = self.deduplicator.deduplicate(all_borrowers)

        # 5. Validate and calculate confidence
        for borrower in merged:
            ssn_valid = self.validator.validate_ssn(borrower.ssn)
            phone_valid = self.validator.validate_phone(borrower.phone)
            zip_valid = self.validator.validate_zip(
                borrower.address.zip_code if borrower.address else None
            )

            all_valid = ssn_valid.is_valid and phone_valid.is_valid and zip_valid.is_valid

            confidence = self.confidence_calc.calculate(
                record=borrower,
                format_validation_passed=all_valid,
                source_count=len(borrower.sources),
            )
            borrower.confidence_score = confidence.total

        return merged

    def _find_page_for_position(self, doc: DocumentContent, char_pos: int) -> int:
        """Find which page a character position falls on."""
        # Simple heuristic: divide by average chars per page
        if doc.page_count == 0:
            return 1
        chars_per_page = len(doc.text) // doc.page_count
        if chars_per_page == 0:
            return 1
        page = (char_pos // chars_per_page) + 1
        return min(page, doc.page_count)
```

### Extraction Prompt Template
```python
# Source: PRD requirements EXTRACT-16 through EXTRACT-18

EXTRACTION_SYSTEM_PROMPT = """You are a loan document data extraction specialist. Extract borrower information from loan documents with high accuracy.

Your task:
1. Identify all borrowers mentioned in the document
2. Extract their personal information (name, SSN, address, phone, email)
3. Extract income history with amounts, periods, and sources
4. Extract account and loan numbers

Rules:
- Extract data exactly as it appears - do not infer or guess
- If a field is unclear or missing, omit it (return null)
- SSN format: XXX-XX-XXXX
- Income amounts: numeric only, no currency symbols
- Multiple borrowers should be separate records

Quality indicators to note:
- Mark data from handwritten sections with lower confidence
- Note if scanned text appears unclear
"""

EXTRACTION_USER_PROMPT_TEMPLATE = """Extract all borrower information from this loan document:

---
{document_text}
---

Return a JSON object with the extracted borrowers."""


def build_extraction_prompt(document_text: str) -> str:
    """Build the user prompt for extraction.

    Handles special characters safely.
    """
    # Escape any characters that might confuse the model
    safe_text = document_text.replace("{", "{{").replace("}", "}}")
    return EXTRACTION_USER_PROMPT_TEMPLATE.format(document_text=safe_text)
```

### Extraction Result Schema
```python
# Source: Compatible with google-genai structured output
from pydantic import BaseModel
from typing import Optional


class ExtractedAddress(BaseModel):
    """Address extracted from document."""
    street: str
    city: str
    state: str  # Two-letter code
    zip_code: str


class ExtractedIncome(BaseModel):
    """Income record extracted from document."""
    amount: float  # Use float for JSON compatibility
    period: str  # annual, monthly, weekly, biweekly
    year: int
    source_type: str  # employment, self-employment, other
    employer: Optional[str] = None


class ExtractedBorrower(BaseModel):
    """Borrower data extracted from document."""
    name: str
    ssn: Optional[str] = None  # XXX-XX-XXXX format
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[ExtractedAddress] = None
    income_history: list[ExtractedIncome] = []
    account_numbers: list[str] = []
    loan_numbers: list[str] = []


class BorrowerExtractionResult(BaseModel):
    """Container for extraction results."""
    borrowers: list[ExtractedBorrower] = []
    extraction_notes: Optional[str] = None  # Any quality issues noted
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google-generativeai SDK | google-genai SDK | 2025 | New official SDK with better async, structured output |
| Gemini 2.0 Flash | Gemini 3 Flash | Jan 2026 | 3x faster, Pro-level reasoning, cheaper |
| JSON mode prompting | response_json_schema | 2025 | Guaranteed valid JSON, type-safe |
| Manual token counting | client.models.count_tokens() | 2025 | Accurate, model-specific |
| FuzzyWuzzy/thefuzz | RapidFuzz | 2024 | 10-15x faster, MIT license |
| Manual backoff | tenacity library | ongoing | Industry standard, configurable |

**Deprecated/outdated:**
- `google-generativeai` package: Use `google-genai` (already in pyproject.toml)
- Gemini 2.0 models: Deprecated, shutdown March 2026
- `fuzzywuzzy` package: Renamed to `thefuzz`, prefer `rapidfuzz`
- Temperature tuning for determinism: Use structured output instead

---

## Open Questions

Things that couldn't be fully resolved:

1. **Thinking budget vs. max_output_tokens interaction**
   - What we know: Setting max_output_tokens causes issues with thinking models
   - What's unclear: Optimal thinking_level setting for extraction tasks
   - Recommendation: Use default thinking_level, don't set max_output_tokens

2. **Optimal chunk size for loan documents**
   - What we know: 4000 tokens is common recommendation
   - What's unclear: Best size for loan documents specifically
   - Recommendation: Start with 4000 tokens, tune based on extraction quality

3. **Confidence score calibration**
   - What we know: Formula in PRD gives 0.0-1.0 range
   - What's unclear: Whether 0.7 threshold is optimal for loan documents
   - Recommendation: Start with 0.7, adjust based on manual review feedback

4. **RapidFuzz vs. phonenumbers installation**
   - What we know: Not in current pyproject.toml
   - What's unclear: Whether to add as required or optional dependencies
   - Recommendation: Add `rapidfuzz>=3.0.0` and `phonenumbers>=8.0.0` to dependencies

---

## Sources

### Primary (HIGH confidence)
- [Google Gen AI SDK Documentation](https://googleapis.github.io/python-genai/) - API patterns, async support
- [Gemini API Structured Output](https://ai.google.dev/gemini-api/docs/structured-output) - Pydantic integration
- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3) - Model names, thinking config
- [Google Cloud Gemini 3 Flash](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash) - Model capabilities
- [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) - Cost comparison
- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Retry patterns
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) - Fuzzy matching API

### Secondary (MEDIUM confidence)
- [Issue #1039: Structured Output None](https://github.com/googleapis/python-genai/issues/1039) - max_output_tokens issue
- [Issue #699: Pydantic default values](https://github.com/googleapis/python-genai/issues/699) - Field(default=...) issue
- [Issue #782: Thinking models unreliable](https://github.com/googleapis/python-genai/issues/782) - Thinking budget issues
- [Pinecone Chunking Strategies](https://www.pinecone.io/learn/chunking-strategies/) - Chunking best practices
- [Google Cloud 429 Error Handling](https://cloud.google.com/blog/products/ai-machine-learning/learn-how-to-handle-429-resource-exhaustion-errors-in-your-llms) - Rate limit strategies

### Tertiary (LOW confidence)
- Various Medium articles on confidence scoring - Validate approach with actual data
- Stack Overflow discussions on fuzzy matching - Edge cases may vary

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - google-genai SDK well-documented, tenacity battle-tested
- Gemini 3 API patterns: HIGH - Official documentation verified
- Structured output: HIGH - Official examples, known issues documented
- Chunking strategy: MEDIUM - General best practices, tune for loan docs
- Confidence scoring: MEDIUM - Formula from PRD, threshold needs validation
- Deduplication: MEDIUM - Standard approach, threshold tuning needed

**Research date:** 2026-01-23
**Valid until:** 2026-02-23 (30 days - Gemini 3 models in preview, watch for GA changes)
