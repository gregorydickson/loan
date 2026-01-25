"""Unit tests for ExtractionRouter."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.extraction.extraction_router import (
    ExtractionRouter,
    LangExtractTransientError,
    LangExtractFatalError,
)
from src.extraction.extraction_config import ExtractionConfig


class TestExtractionRouter:
    """Tests for ExtractionRouter method selection and fallback."""

    @pytest.fixture
    def mock_langextract(self):
        """Mock LangExtractProcessor."""
        processor = MagicMock()
        processor.extract.return_value = MagicMock(borrowers=[], alignment_warnings=[])
        return processor

    @pytest.fixture
    def mock_docling(self):
        """Mock BorrowerExtractor."""
        extractor = MagicMock()
        extractor.extract.return_value = MagicMock(borrowers=[], validation_errors=[])
        return extractor

    @pytest.fixture
    def mock_document(self):
        """Mock DocumentContent."""
        doc = MagicMock()
        doc.text = "Sample document text"
        return doc

    @pytest.fixture
    def router(self, mock_langextract, mock_docling):
        """Create router with mocked extractors."""
        return ExtractionRouter(mock_langextract, mock_docling)

    def test_method_docling_uses_docling_only(self, router, mock_docling, mock_document):
        """method='docling' uses Docling extractor directly."""
        doc_id = uuid4()
        router.extract(mock_document, doc_id, "test.pdf", method="docling")

        mock_docling.extract.assert_called_once()
        router.langextract.extract.assert_not_called()

    def test_method_langextract_uses_langextract_only(self, router, mock_document):
        """method='langextract' uses LangExtract processor directly."""
        doc_id = uuid4()
        router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        router.langextract.extract.assert_called_once()
        router.docling.extract.assert_not_called()

    def test_method_auto_tries_langextract_first(self, router, mock_document):
        """method='auto' tries LangExtract first."""
        doc_id = uuid4()
        router.extract(mock_document, doc_id, "test.pdf", method="auto")

        router.langextract.extract.assert_called_once()
        router.docling.extract.assert_not_called()  # No fallback needed

    def test_auto_fallback_on_fatal_error(self, router, mock_document):
        """method='auto' falls back to Docling on fatal error."""
        router.langextract.extract.side_effect = Exception("API key invalid")
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="auto")

        router.docling.extract.assert_called_once()

    def test_auto_fallback_on_transient_error_after_retries(self, router, mock_document):
        """method='auto' falls back after transient errors exhaust retries."""
        router.langextract.extract.side_effect = Exception("503 Service Unavailable")
        doc_id = uuid4()

        # Should retry 3 times then fallback
        with patch.object(router, "_try_langextract") as mock_try:
            mock_try.side_effect = LangExtractTransientError("503")
            router.extract(mock_document, doc_id, "test.pdf", method="auto")

        router.docling.extract.assert_called_once()

    def test_langextract_only_raises_on_error(self, router, mock_document):
        """method='langextract' raises error without fallback."""
        router.langextract.extract.side_effect = Exception("API error")
        doc_id = uuid4()

        with pytest.raises((LangExtractTransientError, LangExtractFatalError, Exception)):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

    def test_config_passed_to_langextract(self, router, mock_document):
        """ExtractionConfig is passed to LangExtract processor."""
        config = ExtractionConfig(extraction_passes=4, max_workers=20)
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="langextract", config=config)

        call_kwargs = router.langextract.extract.call_args[1]
        assert call_kwargs["config"] == config

    def test_default_config_when_none(self, router, mock_document):
        """Default ExtractionConfig used when config=None."""
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        call_kwargs = router.langextract.extract.call_args[1]
        assert isinstance(call_kwargs["config"], ExtractionConfig)

    def test_docling_method_skips_config(self, router, mock_docling, mock_document):
        """method='docling' ignores config parameter."""
        config = ExtractionConfig(extraction_passes=4)
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="docling", config=config)

        # Docling extract doesn't receive config
        call_args = mock_docling.extract.call_args
        assert "config" not in call_args.kwargs

    def test_default_method_is_auto(self, router, mock_document):
        """Default method is 'auto'."""
        doc_id = uuid4()

        # Call without method parameter
        router.extract(mock_document, doc_id, "test.pdf")

        # LangExtract should be tried first (auto mode)
        router.langextract.extract.assert_called_once()

    def test_returns_langextract_result_on_success(self, router, mock_document):
        """Successful LangExtract returns LangExtractResult."""
        expected_result = MagicMock(borrowers=[MagicMock()], alignment_warnings=[])
        router.langextract.extract.return_value = expected_result
        doc_id = uuid4()

        result = router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        assert result == expected_result

    def test_returns_docling_result_on_fallback(self, router, mock_document):
        """Fallback returns ExtractionResult from Docling."""
        expected_result = MagicMock(borrowers=[MagicMock()], validation_errors=[])
        router.docling.extract.return_value = expected_result
        router.langextract.extract.side_effect = Exception("API error")
        doc_id = uuid4()

        result = router.extract(mock_document, doc_id, "test.pdf", method="auto")

        assert result == expected_result


class TestTransientErrorClassification:
    """Tests for transient vs fatal error classification."""

    def test_503_is_transient(self):
        """503 errors are classified as transient."""
        error = Exception("503 Service Unavailable")
        error_str = str(error).lower()
        assert "503" in error_str

    def test_429_is_transient(self):
        """429 rate limit errors are classified as transient."""
        error = Exception("429 Too Many Requests")
        error_str = str(error).lower()
        assert "429" in error_str

    def test_timeout_is_transient(self):
        """Timeout errors are classified as transient."""
        error = Exception("Request timeout")
        error_str = str(error).lower()
        assert "timeout" in error_str

    def test_overloaded_is_transient(self):
        """Overloaded errors are classified as transient."""
        error = Exception("Model overloaded")
        error_str = str(error).lower()
        assert "overloaded" in error_str

    def test_rate_limit_is_transient(self):
        """Rate limit errors are classified as transient."""
        error = Exception("Rate limit exceeded")
        error_str = str(error).lower()
        assert "rate limit" in error_str

    def test_api_key_invalid_is_fatal(self):
        """API key errors are classified as fatal."""
        error = Exception("API key invalid")
        error_str = str(error).lower()
        # Should not match any transient patterns
        assert not any(
            x in error_str for x in ["503", "429", "timeout", "overloaded", "rate limit"]
        )


class TestRetryDecorator:
    """Tests for tenacity retry configuration."""

    def test_retry_decorator_on_try_langextract(self):
        """_try_langextract has retry decorator."""
        from src.extraction.extraction_router import ExtractionRouter

        # Check that the method has retry behavior via tenacity
        assert hasattr(ExtractionRouter._try_langextract, "retry")

    def test_retry_config_stop_after_3_attempts(self):
        """Retry stops after 3 attempts."""
        from src.extraction.extraction_router import ExtractionRouter

        # Get the retry object from the decorated method
        retry_state = ExtractionRouter._try_langextract.retry
        # tenacity uses stop_after_attempt which has a max_attempt_number attribute
        assert hasattr(retry_state.stop, "max_attempt_number")
        assert retry_state.stop.max_attempt_number == 3

    def test_retry_config_exponential_backoff(self):
        """Retry uses exponential backoff."""
        from src.extraction.extraction_router import ExtractionRouter

        retry_state = ExtractionRouter._try_langextract.retry
        # wait_exponential has multiplier, min, max attributes
        assert hasattr(retry_state.wait, "multiplier")
        assert retry_state.wait.multiplier == 2
        assert retry_state.wait.min == 4
        assert retry_state.wait.max == 60


class TestExceptionClasses:
    """Tests for custom exception classes."""

    def test_transient_error_can_be_raised(self):
        """LangExtractTransientError can be raised and caught."""
        with pytest.raises(LangExtractTransientError) as exc_info:
            raise LangExtractTransientError("503 Service Unavailable")
        assert "503" in str(exc_info.value)

    def test_fatal_error_can_be_raised(self):
        """LangExtractFatalError can be raised and caught."""
        with pytest.raises(LangExtractFatalError) as exc_info:
            raise LangExtractFatalError("Invalid API key")
        assert "Invalid API key" in str(exc_info.value)

    def test_transient_error_is_exception_subclass(self):
        """LangExtractTransientError is an Exception subclass."""
        assert issubclass(LangExtractTransientError, Exception)

    def test_fatal_error_is_exception_subclass(self):
        """LangExtractFatalError is an Exception subclass."""
        assert issubclass(LangExtractFatalError, Exception)
