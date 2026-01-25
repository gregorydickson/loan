# Phase 17: Testing & Quality - Research

**Researched:** 2026-01-25
**Domain:** Python testing with pytest, mypy type checking, code coverage
**Confidence:** HIGH

## Summary

This phase focuses on achieving comprehensive test coverage for all v2.0 features with type safety. The project already has a well-established testing infrastructure using pytest 8.3.0, pytest-cov 6.0.0, and mypy 1.14.0 with strict mode enabled. Current coverage stands at 85.14%, exceeding the 80% threshold. The main work involves:

1. Enhancing existing LangExtract processor tests with few-shot example validation
2. Adding character offset verification tests (LXTR-08 requirement)
3. Creating LightOnOCR GPU service integration tests with proper mocking
4. Adding scanned document detection accuracy tests
5. Ensuring E2E tests cover both Docling and LangExtract extraction paths
6. Adding dual pipeline method selection tests
7. Ensuring mypy strict mode compliance for all new code

The existing test structure follows pytest best practices with separate unit/integration directories, proper fixture organization in conftest.py files, and FastAPI dependency override patterns for mocking.

**Primary recommendation:** Extend the existing test infrastructure rather than restructuring. Focus on filling gaps for v2.0 features while maintaining the established patterns.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.3.0 | Test framework | De facto Python testing standard, rich plugin ecosystem |
| pytest-asyncio | 1.3.0 | Async test support | Required for FastAPI async endpoints |
| pytest-cov | 6.0.0 | Coverage measurement | Integrated coverage with pytest |
| mypy | 1.14.0 | Static type checking | Industry standard for Python type safety |
| httpx | 0.28.0 | Async HTTP client | Required for FastAPI AsyncClient testing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-xdist | 3.0.0 | Parallel test execution | Speed up large test suites |
| aiosqlite | 0.21.0 | Async SQLite for tests | In-memory test databases |
| unittest.mock | stdlib | Mocking/patching | External service mocking |
| MagicMock/AsyncMock | stdlib | Mock objects | GPU service, LLM API mocking |
| coverage | 7.13+ | Code coverage engine | Used by pytest-cov |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest | unittest | pytest has better fixtures, less boilerplate, rich ecosystem |
| pytest-asyncio | anyio | anyio is more general, pytest-asyncio is simpler for asyncio-only |
| mypy | pyright | pyright faster but mypy has better ecosystem integration |

**Installation:**
Already configured in pyproject.toml dev dependencies. No additional packages needed.

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── tests/
│   ├── conftest.py              # Shared fixtures (client, mock dependencies)
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── extraction/          # LangExtract, offset translator tests
│   │   │   ├── __init__.py
│   │   │   ├── test_langextract_processor.py
│   │   │   ├── test_offset_translator.py
│   │   │   ├── test_extraction_router.py
│   │   │   └── test_extraction_config.py
│   │   ├── ocr/                 # OCR routing, detection, client tests
│   │   │   ├── __init__.py
│   │   │   ├── test_lightonocr_client.py
│   │   │   ├── test_scanned_detector.py
│   │   │   └── test_ocr_router.py
│   │   └── test_*.py            # Other unit tests
│   ├── integration/
│   │   ├── conftest.py          # Integration-specific fixtures
│   │   ├── test_dual_pipeline.py
│   │   ├── test_e2e_extraction.py
│   │   ├── test_e2e_docling.py     # NEW: Docling path regression
│   │   ├── test_e2e_langextract.py # NEW: LangExtract path E2E
│   │   └── test_gpu_service.py     # NEW: GPU integration tests
│   └── extraction/              # Specialized extraction tests
│       └── test_*.py
└── examples/                    # Few-shot examples for validation
    ├── __init__.py
    ├── borrower_examples.py
    ├── income_examples.py
    └── account_examples.py
```

### Pattern 1: FastAPI Dependency Override for Mocking
**What:** Override FastAPI dependencies to inject mocks during testing
**When to use:** All integration tests that need mocked external services
**Example:**
```python
# Source: Existing tests/integration/conftest.py
@pytest.fixture
async def client(async_engine, db_session, mock_gcs_client, mock_docling_processor):
    """Create test client with mocked dependencies."""
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession)

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = lambda: mock_gcs_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
```

### Pattern 2: Character Offset Verification Tests
**What:** Test that extracted offsets correctly locate text via substring matching
**When to use:** LangExtract source grounding verification (LXTR-08)
**Example:**
```python
# Source: Existing tests/unit/test_char_offset_verification.py
def test_substring_at_exact_offsets():
    """Text at [char_start:char_end] matches extracted text exactly."""
    source_text = "Borrower Name: John Smith, SSN: 123-45-6789"

    extractions = [
        {"text": "John Smith", "start": 15, "end": 25},
        {"text": "123-45-6789", "start": 32, "end": 43},
    ]

    for ext in extractions:
        actual = source_text[ext["start"]:ext["end"]]
        assert actual == ext["text"], f"Substring mismatch at [{ext['start']}:{ext['end']}]"
```

### Pattern 3: GPU Service Mocking with AsyncMock
**What:** Mock HTTP responses from GPU Cloud Run service
**When to use:** LightOnOCR client integration tests
**Example:**
```python
# Source: Existing tests/unit/ocr/test_lightonocr_client.py
@pytest.mark.asyncio
async def test_extract_text_success(client, mock_id_token):
    """Test successful text extraction."""
    mock_response = {"choices": [{"message": {"content": "Extracted text"}}]}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_response,
        )
        mock_client_class.return_value = mock_client

        result = await client.extract_text(PNG_BYTES)
        assert result == "Extracted text"
```

### Pattern 4: Few-Shot Example Validation
**What:** Validate that extraction_text in examples matches source text
**When to use:** TEST-01 requirement for few-shot validation
**Example:**
```python
# Source: examples/__init__.py validate_examples function
def test_all_examples_have_verbatim_text():
    """All few-shot examples must have verbatim extraction_text."""
    from examples import ALL_EXAMPLES, validate_examples

    errors = validate_examples()
    assert not errors, f"Invalid examples: {errors}"

def test_borrower_examples_complete():
    """Borrower examples cover all required fields."""
    from examples import BORROWER_EXAMPLES

    assert len(BORROWER_EXAMPLES) >= 3, "Need minimum 3 borrower examples"

    for example in BORROWER_EXAMPLES:
        has_borrower = any(e.extraction_class == "borrower" for e in example.extractions)
        assert has_borrower, f"Example missing borrower extraction: {example.text[:50]}..."
```

### Pattern 5: Circuit Breaker State Testing
**What:** Test circuit breaker transitions for GPU service resilience
**When to use:** OCR routing fallback tests (TEST-08)
**Example:**
```python
# Source: Existing tests/unit/ocr/test_ocr_router.py
@pytest.mark.asyncio
async def test_fallback_on_circuit_breaker_open(router, mock_detector, mock_gpu_client):
    """Falls back to Docling when circuit breaker is open."""
    mock_detector.detect.return_value = DetectionResult(
        needs_ocr=True, scanned_pages=[0], total_pages=1, scanned_ratio=1.0
    )
    reopen_time = datetime.now(timezone.utc)
    mock_gpu_client.health_check.side_effect = CircuitBreakerError(
        "Circuit breaker is open", reopen_time
    )

    result = await router.process(b"pdf", "test.pdf", mode="auto")

    assert result.ocr_method == "docling"
```

### Anti-Patterns to Avoid
- **Testing implementation details:** Test behavior, not internal methods. Focus on public API.
- **Over-mocking:** Don't mock so much that tests don't reflect reality. Keep some real dependencies.
- **Shared mutable state:** Each test should be independent. Use function-scoped fixtures by default.
- **Ignoring async context:** Always use `pytest.mark.asyncio` and proper async fixtures.
- **Hardcoded test data:** Use fixtures and factories for reusable test data.
- **Testing coverage, not quality:** Writing weak tests just to hit coverage numbers.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async test support | Custom event loop management | pytest-asyncio | Handles event loop per test properly |
| Coverage measurement | Manual line counting | pytest-cov | Handles branches, excludes, reports |
| HTTP mocking | Custom mock classes | httpx + AsyncMock | Better integration with httpx async |
| Database fixtures | Manual setup/teardown | SQLAlchemy + async_sessionmaker | Proper transaction rollback |
| API testing | Raw requests | AsyncClient + ASGITransport | Direct ASGI testing without network |
| Type checking | Manual assertions | mypy --strict | Static analysis catches issues at build |
| Retry logic testing | Time-based tests | tenacity.retry mock | Avoid flaky time-dependent tests |

**Key insight:** The project already has well-established patterns for all these areas. Extend existing fixtures rather than creating new approaches.

## Common Pitfalls

### Pitfall 1: Async Fixture Scope Mismatch
**What goes wrong:** Using session-scoped async fixtures with function-scoped event loops
**Why it happens:** pytest-asyncio defaults to function scope for event loops
**How to avoid:** Set `asyncio_default_fixture_loop_scope = "function"` in pyproject.toml (already configured)
**Warning signs:** "There is no current event loop" errors

### Pitfall 2: Character Offset Indexing Errors
**What goes wrong:** Off-by-one errors when slicing text with char_start/char_end
**Why it happens:** Python uses exclusive end index (text[start:end] excludes char at end)
**How to avoid:** Always verify with `source_text[char_start:char_end] == expected_text`
**Warning signs:** Tests pass but offsets are wrong by 1 character

### Pitfall 3: Mock State Leakage Between Tests
**What goes wrong:** Test A configures mock, Test B sees stale mock state
**Why it happens:** Not clearing dependency_overrides or using module-scoped mocks
**How to avoid:** Always call `app.dependency_overrides.clear()` in fixture cleanup
**Warning signs:** Tests pass individually but fail when run together

### Pitfall 4: Testing Against Real GPU Service
**What goes wrong:** Tests fail due to GPU service cold start (2-5 minute timeout)
**Why it happens:** Integration tests calling actual Cloud Run GPU service
**How to avoid:** Always mock LightOnOCRClient in unit/integration tests. Only call real service in manual E2E validation.
**Warning signs:** Intermittent timeouts, tests taking 5+ minutes

### Pitfall 5: mypy Strict Mode False Positives
**What goes wrong:** Valid code fails mypy due to missing stubs or incorrect inference
**Why it happens:** Third-party libraries missing type stubs
**How to avoid:** Add targeted `# type: ignore[error-code]` with comments explaining why
**Warning signs:** Excessive type: ignore comments, errors about "no attribute"

### Pitfall 6: Coverage Measurement on Source vs Installed
**What goes wrong:** Coverage reports 0% because measuring wrong package path
**Why it happens:** Testing installed package but measuring source directory
**How to avoid:** Use `--cov=src` consistently, ensure editable install with `pip install -e .`
**Warning signs:** Coverage much lower than expected, missing files in report

### Pitfall 7: Duplicate Borrower Extraction in Tests
**What goes wrong:** Tests create same borrower multiple times with different IDs
**Why it happens:** Mock returns same data but new UUID each call
**How to avoid:** Create mock data with stable IDs in fixture, or verify deduplication
**Warning signs:** Tests expect 1 borrower but find 3

## Code Examples

Verified patterns from official sources and existing codebase:

### Few-Shot Example Validation Test (TEST-01)
```python
# Source: examples/__init__.py pattern
import pytest
from examples import ALL_EXAMPLES, validate_examples, BORROWER_EXAMPLES

class TestFewShotExamples:
    """TEST-01: LangExtract processor unit tests with few-shot example validation."""

    def test_all_examples_valid(self):
        """All extraction_text must be verbatim substrings of source."""
        errors = validate_examples()
        assert not errors, f"Invalid examples found:\n" + "\n".join(errors)

    def test_borrower_examples_have_required_fields(self):
        """Borrower examples must demonstrate SSN, address extraction."""
        for example in BORROWER_EXAMPLES:
            borrower_extractions = [
                e for e in example.extractions
                if e.extraction_class == "borrower"
            ]
            assert borrower_extractions, "Each example needs borrower extraction"

    def test_examples_cover_edge_cases(self):
        """Examples should cover various document formats."""
        example_texts = [e.text for e in ALL_EXAMPLES]
        # Check diversity
        assert len(ALL_EXAMPLES) >= 9, "Need minimum 9 examples (3 per category)"
```

### Character Offset Verification Test (TEST-02)
```python
# Source: tests/unit/test_char_offset_verification.py pattern
import pytest
from src.extraction.offset_translator import OffsetTranslator
from src.models.document import SourceReference
from uuid import uuid4

class TestCharacterOffsetVerification:
    """TEST-02: Character offset verification via substring matching."""

    @pytest.fixture
    def loan_application_text(self):
        return """LOAN APPLICATION

Borrower: John Michael Smith
SSN: 123-45-6789
Address: 456 Oak Lane, Austin, TX 78701
"""

    def test_offset_verification_exact_match(self, loan_application_text):
        """Offsets must produce exact substring match."""
        translator = OffsetTranslator(loan_application_text)

        # Test SSN extraction
        ssn_start = loan_application_text.find("123-45-6789")
        ssn_end = ssn_start + len("123-45-6789")

        assert translator.verify_offset(ssn_start, ssn_end, "123-45-6789")

    def test_source_reference_offsets_valid(self, loan_application_text):
        """SourceReference char_start/char_end locate correct text."""
        name_text = "John Michael Smith"
        name_start = loan_application_text.find(name_text)
        name_end = name_start + len(name_text)

        source = SourceReference(
            document_id=uuid4(),
            document_name="test.pdf",
            page_number=1,
            snippet=loan_application_text[:200],
            char_start=name_start,
            char_end=name_end,
        )

        actual = loan_application_text[source.char_start:source.char_end]
        assert actual == name_text
```

### GPU Service Integration Test (TEST-03)
```python
# Source: tests/unit/ocr/test_lightonocr_client.py pattern
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ocr.lightonocr_client import LightOnOCRClient, LightOnOCRError

class TestLightOnOCRIntegration:
    """TEST-03: LightOnOCR GPU service integration tests."""

    @pytest.fixture
    def mock_id_token(self):
        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock:
            mock.return_value = "mock-token"
            yield mock

    @pytest.mark.asyncio
    async def test_successful_extraction(self, mock_id_token):
        """GPU service returns extracted text on success."""
        client = LightOnOCRClient(service_url="https://test.run.app")
        mock_response = {"choices": [{"message": {"content": "OCR result"}}]}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            mock_client_class.return_value = mock_client

            result = await client.extract_text(b"\x89PNG...")
            assert result == "OCR result"

    @pytest.mark.asyncio
    async def test_cold_start_timeout_handling(self, mock_id_token):
        """Client handles GPU cold start timeouts gracefully."""
        import httpx
        client = LightOnOCRClient(service_url="https://test.run.app", timeout=5.0)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.TimeoutException("Cold start timeout")
            mock_client_class.return_value = mock_client

            with pytest.raises(LightOnOCRError, match="timed out"):
                await client.extract_text(b"\x89PNG...")
```

### Scanned Document Detection Accuracy Test (TEST-04)
```python
# Source: tests/unit/ocr/test_scanned_detector.py pattern
import pytest
from unittest.mock import MagicMock, patch
from src.ocr.scanned_detector import ScannedDocumentDetector, DetectionResult

class TestScannedDocumentDetectionAccuracy:
    """TEST-04: Scanned document detection accuracy tests."""

    @pytest.fixture
    def detector(self):
        return ScannedDocumentDetector()

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detects_fully_scanned_document(self, mock_pdf_class, detector):
        """100% scanned pages detected correctly."""
        self._setup_mock_pdf(mock_pdf_class, page_texts=["", "", ""])

        result = detector.detect(b"scanned pdf bytes")

        assert result.needs_ocr is True
        assert result.scanned_ratio == 1.0
        assert result.scanned_pages == [0, 1, 2]

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detects_native_pdf(self, mock_pdf_class, detector):
        """Native PDF with text layer detected correctly."""
        self._setup_mock_pdf(mock_pdf_class, page_texts=["A"*100, "B"*100])

        result = detector.detect(b"native pdf bytes")

        assert result.needs_ocr is False
        assert result.scanned_ratio == 0.0

    def _setup_mock_pdf(self, mock_pdf_class, page_texts):
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=len(page_texts))

        mock_pages = []
        for text in page_texts:
            mock_page = MagicMock()
            mock_textpage = MagicMock()
            mock_textpage.get_text_bounded.return_value = text
            mock_page.get_textpage.return_value = mock_textpage
            mock_pages.append(mock_page)

        mock_pdf.__getitem__ = MagicMock(side_effect=lambda x: mock_pages[x])
        mock_pdf_class.return_value = mock_pdf
```

### Dual Pipeline Method Selection Test (TEST-07)
```python
# Source: tests/integration/test_dual_pipeline.py pattern
import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from src.extraction.extraction_router import ExtractionRouter
from src.extraction.langextract_processor import LangExtractProcessor, LangExtractResult
from src.extraction.extractor import BorrowerExtractor, ExtractionResult

class TestDualPipelineMethodSelection:
    """TEST-07: Dual pipeline method selection tests."""

    @pytest.fixture
    def mock_langextract(self):
        processor = MagicMock(spec=LangExtractProcessor)
        processor.extract.return_value = LangExtractResult(borrowers=[], alignment_warnings=[])
        return processor

    @pytest.fixture
    def mock_docling(self):
        extractor = MagicMock(spec=BorrowerExtractor)
        extractor.extract.return_value = MagicMock(borrowers=[], validation_errors=[])
        return extractor

    @pytest.fixture
    def router(self, mock_langextract, mock_docling):
        return ExtractionRouter(mock_langextract, mock_docling)

    def test_method_langextract_uses_langextract_only(self, router, mock_langextract, mock_docling):
        """method='langextract' routes to LangExtract."""
        doc = MagicMock()
        doc.text = "Test"

        router.extract(doc, uuid4(), "test.pdf", method="langextract")

        mock_langextract.extract.assert_called_once()
        mock_docling.extract.assert_not_called()

    def test_method_docling_uses_docling_only(self, router, mock_langextract, mock_docling):
        """method='docling' routes to Docling."""
        doc = MagicMock()
        doc.text = "Test"

        router.extract(doc, uuid4(), "test.pdf", method="docling")

        mock_docling.extract.assert_called_once()
        mock_langextract.extract.assert_not_called()
```

### OCR Routing Logic Test (TEST-08)
```python
# Source: tests/unit/ocr/test_ocr_router.py pattern
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ocr.ocr_router import OCRRouter, OCRMode
from src.ocr.scanned_detector import DetectionResult

class TestOCRRoutingLogic:
    """TEST-08: OCR routing logic tests (auto/force/skip)."""

    @pytest.fixture
    def mock_components(self):
        gpu = MagicMock()
        gpu.health_check = AsyncMock(return_value=True)
        docling = MagicMock()
        docling.enable_tables = True
        detector = MagicMock()
        return gpu, docling, detector

    @pytest.fixture
    def router(self, mock_components):
        gpu, docling, detector = mock_components
        return OCRRouter(gpu_client=gpu, docling_processor=docling, detector=detector)

    @pytest.mark.asyncio
    async def test_skip_mode_never_ocrs(self, router, mock_components):
        """mode='skip' bypasses OCR regardless of document type."""
        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Text")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"pdf", "test.pdf", mode="skip")

            assert result.ocr_method == "none"
            MockProcessor.assert_called_once()
            call_kwargs = MockProcessor.call_args[1]
            assert call_kwargs["enable_ocr"] is False

    @pytest.mark.asyncio
    async def test_force_mode_always_ocrs(self, router, mock_components):
        """mode='force' runs OCR on all pages."""
        gpu, _, detector = mock_components

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            with patch("src.ocr.ocr_router.pdfium.PdfDocument") as MockPdf:
                mock_pdf = MagicMock()
                mock_pdf.__len__ = MagicMock(return_value=2)
                MockPdf.return_value = mock_pdf

                mock_instance = MagicMock()
                mock_instance.process_bytes.return_value = MagicMock(text="Text")
                MockProcessor.return_value = mock_instance

                result = await router.process(b"pdf", "test.pdf", mode="force")

            assert result.ocr_method == "docling"
            assert len(result.pages_ocrd) == 2
```

### mypy Compliance Test (TEST-12)
```python
# This is tested via CI, not unit tests. Configure in pyproject.toml:
# Source: backend/pyproject.toml

"""
[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
exclude = ["alembic/"]

# Allow tests to have looser typing
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_untyped_calls = false
disallow_incomplete_defs = false
"""

# Run via: python3 -m mypy src/
# Coverage via: pytest --cov=src --cov-fail-under=80
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| unittest TestCase | pytest functions | 2020+ | Less boilerplate, better fixtures |
| requests for API tests | httpx AsyncClient | 2022+ | Native async support |
| manual coverage | pytest-cov | 2018+ | Integrated coverage in test runs |
| Python 3.8 typing | Python 3.12 generics | 2024 | Better type inference, less verbose |
| pytest-asyncio 0.x | pytest-asyncio 1.x | 2025 | Simpler event loop handling |
| coverage.py 6.x | coverage.py 7.x | 2025 | Removed subprocess .pth hack |

**Deprecated/outdated:**
- `@pytest.mark.asyncio` with scope parameter: Use pyproject.toml config instead
- `pytest-runner` / `setup.py test`: Use direct pytest invocation
- `TestClient` sync tests for FastAPI: Use `AsyncClient` with `ASGITransport`

## Open Questions

Things that couldn't be fully resolved:

1. **GPU Cold Start Performance Test Strategy**
   - What we know: GPU service has 2-5 minute cold start, need to test handling
   - What's unclear: Whether to run actual cold start in CI (expensive, slow)
   - Recommendation: Mock cold start behavior in unit tests; manual E2E for real cold start validation

2. **Real LightOnOCR Integration Tests**
   - What we know: Current tests mock GPU service entirely
   - What's unclear: When/how to run tests against actual GPU service
   - Recommendation: Create separate test mark for GPU integration; only run manually or on release branches

3. **Few-Shot Example Coverage**
   - What we know: 9 examples exist (3 per category)
   - What's unclear: Whether this is sufficient for production quality
   - Recommendation: Validate with real documents; add examples as edge cases discovered

## Sources

### Primary (HIGH confidence)
- [pytest documentation](https://docs.pytest.org/en/stable/) - Test organization, fixtures, best practices
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/) - AsyncClient patterns
- [mypy documentation](https://mypy.readthedocs.io/en/stable/) - Strict mode configuration
- Project codebase: `backend/tests/` - Existing patterns and fixtures
- Project codebase: `backend/pyproject.toml` - Current configuration

### Secondary (MEDIUM confidence)
- [pytest-cov GitHub](https://github.com/pytest-dev/pytest-cov) - Coverage plugin details
- [Real Python pytest guide](https://realpython.com/pytest-python-testing/) - Best practices
- [NerdWallet pytest practices](https://www.nerdwallet.com/blog/engineering/5-pytest-best-practices/) - Industry patterns
- [pytest-with-eric](https://pytest-with-eric.com/) - Advanced patterns

### Tertiary (LOW confidence)
- WebSearch results for 2026 testing patterns - General best practices, needs validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using established pytest ecosystem, versions verified in pyproject.toml
- Architecture: HIGH - Following existing patterns in codebase
- Pitfalls: MEDIUM - Based on common pytest issues and project-specific patterns
- Code examples: HIGH - Based on existing tests and official documentation

**Research date:** 2026-01-25
**Valid until:** 90 days (stable tools, patterns unlikely to change)
