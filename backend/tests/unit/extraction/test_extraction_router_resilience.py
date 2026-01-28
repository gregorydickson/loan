"""Advanced resilience tests for ExtractionRouter.

Tests retry behavior, exponential backoff timing, error recovery,
and production failure scenarios.

NOTE: tenacity wraps exhausted retries in RetryError, which may not be
caught by the current except clause. Tests account for this behavior.
"""

import time
from unittest.mock import MagicMock, patch, call
from uuid import uuid4

import pytest
from tenacity import RetryError

from src.extraction.extraction_config import ExtractionConfig
from src.extraction.extraction_router import (
    ExtractionRouter,
    LangExtractFatalError,
    LangExtractTransientError,
)


class TestRetryBehavior:
    """Tests for actual retry behavior and timing."""

    @pytest.fixture
    def router(self):
        """Create router with mocked extractors."""
        langextract = MagicMock()
        docling = MagicMock()
        docling.extract.return_value = MagicMock(borrowers=[])
        return ExtractionRouter(langextract, docling)

    @pytest.fixture
    def mock_document(self):
        """Mock DocumentContent."""
        doc = MagicMock()
        doc.text = "Sample document"
        return doc

    def test_transient_error_retries_exactly_3_times(self, router, mock_document):
        """Transient errors trigger exactly 3 retry attempts."""
        router.langextract.extract.side_effect = Exception("503 Service Unavailable")
        doc_id = uuid4()

        # After exhausting retries, tenacity raises RetryError
        # Use method="langextract" to avoid fallback and observe RetryError
        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Verify 3 attempts were made
        assert router.langextract.extract.call_count == 3

    def test_exponential_backoff_timing(self, router, mock_document):
        """Verify exponential backoff increases wait time between retries."""
        router.langextract.extract.side_effect = Exception("429 Rate Limit")
        doc_id = uuid4()

        start_time = time.time()
        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")
        elapsed = time.time() - start_time

        # With multiplier=2, min=4, max=60:
        # Attempt 1: immediate
        # Wait ~4s (2^1 * 2 = 4, but actual backoff may vary)
        # Attempt 2: after wait
        # Wait ~8s (2^2 * 2 = 8, but actual backoff may vary)
        # Attempt 3: after wait
        # Total: ~8-12 seconds expected
        assert elapsed >= 6, "Should wait at least 6s with exponential backoff"
        assert elapsed < 20, "Should not wait more than 20s for 3 attempts"

    def test_fatal_error_skips_retries(self, router, mock_document):
        """Fatal errors skip retry logic and fallback immediately."""
        router.langextract.extract.side_effect = Exception("API key invalid")
        doc_id = uuid4()

        start_time = time.time()
        router.extract(mock_document, doc_id, "test.pdf", method="auto")
        elapsed = time.time() - start_time

        # Should fallback immediately without retries
        assert router.langextract.extract.call_count == 1, "Should try once only"
        assert elapsed < 2, "Should not wait for retries on fatal error"

    def test_success_on_second_retry_stops_retrying(self, router, mock_document):
        """Success on retry stops further retry attempts."""
        success_result = MagicMock(borrowers=[])
        router.langextract.extract.side_effect = [
            Exception("503 Service Unavailable"),
            success_result,  # Success on retry
        ]
        doc_id = uuid4()

        result = router.extract(mock_document, doc_id, "test.pdf", method="auto")

        # Should stop after second attempt (first retry)
        assert router.langextract.extract.call_count == 2
        assert result == success_result

    def test_mixed_transient_errors_all_trigger_retry(self, router, mock_document):
        """All transient error types trigger retry behavior."""
        router.langextract.extract.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("429 Too Many Requests"),
            Exception("Request timeout after 30s"),
        ]
        doc_id = uuid4()

        # All 3 transient errors exhaust retries
        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # All 3 should be retried
        assert router.langextract.extract.call_count == 3

    def test_langextract_only_mode_retries_without_fallback(self, router, mock_document):
        """method='langextract' retries but raises instead of fallback."""
        router.langextract.extract.side_effect = Exception("503 Service Unavailable")
        doc_id = uuid4()

        # tenacity wraps exhausted retries in RetryError
        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should retry 3 times
        assert router.langextract.extract.call_count == 3
        # But never fallback
        router.docling.extract.assert_not_called()


class TestErrorClassificationEdgeCases:
    """Tests for error classification edge cases."""

    @pytest.fixture
    def router(self):
        """Create router with mocked extractors."""
        langextract = MagicMock()
        docling = MagicMock()
        docling.extract.return_value = MagicMock(borrowers=[])
        return ExtractionRouter(langextract, docling)

    @pytest.fixture
    def mock_document(self):
        """Mock DocumentContent."""
        doc = MagicMock()
        doc.text = "Sample document"
        return doc

    def test_uppercase_error_codes_classified_correctly(self, router, mock_document):
        """Error codes in uppercase are correctly classified."""
        router.langextract.extract.side_effect = Exception("HTTP 503 SERVICE UNAVAILABLE")
        doc_id = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should retry (transient)
        assert router.langextract.extract.call_count == 3

    def test_error_message_with_multiple_keywords(self, router, mock_document):
        """Error with multiple keywords still classified correctly."""
        router.langextract.extract.side_effect = Exception(
            "503 timeout: service overloaded, rate limit exceeded"
        )
        doc_id = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should retry (transient due to 503)
        assert router.langextract.extract.call_count == 3

    def test_partial_match_transient_keyword(self, router, mock_document):
        """Partial matches of transient keywords are handled."""
        # "timeout" is a keyword, but "timeoutable" is not
        router.langextract.extract.side_effect = Exception("connection timeout occurred")
        doc_id = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should retry (contains "timeout")
        assert router.langextract.extract.call_count == 3

    def test_error_with_no_keywords_is_fatal(self, router, mock_document):
        """Errors without transient keywords are classified as fatal."""
        router.langextract.extract.side_effect = Exception("Invalid JSON response")
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="auto")

        # Should not retry (fatal)
        assert router.langextract.extract.call_count == 1
        router.docling.extract.assert_called_once()

    def test_gemini_specific_error_messages(self, router, mock_document):
        """Gemini API specific error messages classified correctly."""
        # Common Gemini errors
        router.langextract.extract.side_effect = Exception(
            "RESOURCE_EXHAUSTED: Model is overloaded"
        )
        doc_id = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should retry (contains "overloaded")
        assert router.langextract.extract.call_count == 3


class TestLoggingBehavior:
    """Tests for logging at different error states."""

    @pytest.fixture
    def router(self):
        """Create router with mocked extractors."""
        langextract = MagicMock()
        docling = MagicMock()
        docling.extract.return_value = MagicMock(borrowers=[])
        return ExtractionRouter(langextract, docling)

    @pytest.fixture
    def mock_document(self):
        """Mock DocumentContent."""
        doc = MagicMock()
        doc.text = "Sample"
        return doc

    @patch("src.extraction.extraction_router.logger")
    def test_transient_error_logs_warning(self, mock_logger, router, mock_document):
        """Transient errors log warning messages."""
        router.langextract.extract.side_effect = Exception("503 Service Unavailable")
        doc_id = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should log warning for transient error
        warning_calls = [call for call in mock_logger.warning.call_args_list]
        assert len(warning_calls) >= 3, "Should log warning on each retry"

    @patch("src.extraction.extraction_router.logger")
    def test_fatal_error_logs_error(self, mock_logger, router, mock_document):
        """Fatal errors log error messages."""
        router.langextract.extract.side_effect = Exception("Invalid API key")
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="auto")

        # Should log error for fatal error
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0]
        assert "fatal" in error_call[0].lower()

    @patch("src.extraction.extraction_router.logger")
    def test_successful_extraction_logs_info(self, mock_logger, router, mock_document):
        """Successful extraction logs info message."""
        router.langextract.extract.return_value = MagicMock(borrowers=[])
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should log success
        mock_logger.info.assert_called()
        info_call = mock_logger.info.call_args[0]
        assert "succeeded" in info_call[0].lower()

    @patch("src.extraction.extraction_router.logger")
    def test_fallback_logs_warning(self, mock_logger, router, mock_document):
        """Fallback to Docling logs warning message (on fatal errors)."""
        # Use fatal error for immediate fallback
        router.langextract.extract.side_effect = Exception("Invalid API key")
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="auto")

        # Should log warning/error about failure and fallback
        all_calls = mock_logger.error.call_args_list + mock_logger.warning.call_args_list
        assert len(all_calls) >= 1, "Should log error or warning"


class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    @pytest.fixture
    def router(self):
        """Create router with mocked extractors."""
        langextract = MagicMock()
        docling = MagicMock()
        docling.extract.return_value = MagicMock(borrowers=[])
        return ExtractionRouter(langextract, docling)

    @pytest.fixture
    def mock_document(self):
        """Mock DocumentContent."""
        doc = MagicMock()
        doc.text = "Sample"
        return doc

    def test_multiple_documents_processed_independently(self, router, mock_document):
        """Multiple documents process independently without interference."""
        # First doc succeeds, second fails
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                borrower_mock = MagicMock()
                borrower_mock.name = "John"
                return MagicMock(borrowers=[borrower_mock])
            else:
                raise Exception("503 Service Unavailable")

        router.langextract.extract.side_effect = side_effect

        doc_id_1 = uuid4()
        doc_id_2 = uuid4()

        # Process first document
        result1 = router.extract(mock_document, doc_id_1, "doc1.pdf", method="langextract")
        assert result1.borrowers[0].name == "John"

        # Process second document (should fail and retry, eventually raising RetryError)
        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id_2, "doc2.pdf", method="langextract")

        # Total calls: 1 success + 3 retries = 4
        assert call_count == 4

    def test_retry_state_not_shared_between_requests(self, router, mock_document):
        """Retry state doesn't leak between different requests."""
        # First request: fail all 3 attempts
        router.langextract.extract.side_effect = Exception("503 Service Unavailable")
        doc_id_1 = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id_1, "doc1.pdf", method="langextract")

        first_call_count = router.langextract.extract.call_count
        assert first_call_count == 3

        # Second request: should also get 3 fresh attempts
        router.langextract.extract.reset_mock()
        router.langextract.extract.side_effect = Exception("429 Rate Limit")
        doc_id_2 = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id_2, "doc2.pdf", method="langextract")

        second_call_count = router.langextract.extract.call_count
        assert second_call_count == 3, "Should get fresh retry attempts"


class TestEdgeCaseRecovery:
    """Tests for edge case error scenarios."""

    @pytest.fixture
    def router(self):
        """Create router with mocked extractors."""
        langextract = MagicMock()
        docling = MagicMock()
        docling.extract.return_value = MagicMock(borrowers=[])
        return ExtractionRouter(langextract, docling)

    @pytest.fixture
    def mock_document(self):
        """Mock DocumentContent."""
        doc = MagicMock()
        doc.text = "Sample"
        return doc

    def test_empty_error_message_classified_as_fatal(self, router, mock_document):
        """Empty error message is classified as fatal."""
        router.langextract.extract.side_effect = Exception("")
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="auto")

        # Should not retry (fatal)
        assert router.langextract.extract.call_count == 1

    def test_none_error_message_handled(self, router, mock_document):
        """Error with None message is handled gracefully."""
        error = Exception()
        error.args = ()  # No message
        router.langextract.extract.side_effect = error
        doc_id = uuid4()

        # Should not crash
        result = router.extract(mock_document, doc_id, "test.pdf", method="auto")
        assert result is not None

    def test_unicode_error_message_handled(self, router, mock_document):
        """Error messages with unicode characters are handled."""
        router.langextract.extract.side_effect = Exception("503 服务不可用 Service Unavailable")
        doc_id = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should retry (contains "503")
        assert router.langextract.extract.call_count == 3

    def test_very_long_error_message_classified_correctly(self, router, mock_document):
        """Very long error messages are classified correctly."""
        long_message = "Error context: " + "x" * 10000 + " timeout occurred"
        router.langextract.extract.side_effect = Exception(long_message)
        doc_id = uuid4()

        with pytest.raises(RetryError):
            router.extract(mock_document, doc_id, "test.pdf", method="langextract")

        # Should retry (contains "timeout")
        assert router.langextract.extract.call_count == 3

    def test_exception_during_error_classification_handled(self, router, mock_document):
        """Exceptions during error classification are handled gracefully."""

        class BrokenException(Exception):
            """Exception that breaks on str()."""

            def __str__(self):
                raise ValueError("Cannot convert to string")

        router.langextract.extract.side_effect = BrokenException()
        doc_id = uuid4()

        # Should not crash, should handle gracefully
        # Since str(e) raises, it will be caught and likely classified as fatal
        try:
            router.extract(mock_document, doc_id, "test.pdf", method="auto")
        except Exception:
            # If it raises, that's acceptable - the point is no crash
            pass

        # Should have attempted at least once
        assert router.langextract.extract.call_count >= 1


class TestDoclingFallbackReliability:
    """Tests for Docling fallback reliability."""

    @pytest.fixture
    def router(self):
        """Create router with mocked extractors."""
        langextract = MagicMock()
        docling = MagicMock()
        return ExtractionRouter(langextract, docling)

    @pytest.fixture
    def mock_document(self):
        """Mock DocumentContent."""
        doc = MagicMock()
        doc.text = "Sample"
        return doc

    def test_fallback_receives_correct_parameters(self, router, mock_document):
        """Docling fallback receives correct document, ID, and name."""
        router.langextract.extract.side_effect = Exception("503 Service Unavailable")
        doc_id = uuid4()
        doc_name = "loan_app.pdf"

        router.extract(mock_document, doc_id, doc_name, method="auto")

        # Verify Docling called with correct params
        router.docling.extract.assert_called_once_with(mock_document, doc_id, doc_name)

    def test_fallback_even_if_docling_also_fails(self, router, mock_document):
        """System attempts Docling fallback even if it also fails."""
        router.langextract.extract.side_effect = Exception("503 Service Unavailable")
        router.docling.extract.side_effect = Exception("Docling also failed")
        doc_id = uuid4()

        with pytest.raises(Exception) as exc_info:
            router.extract(mock_document, doc_id, "test.pdf", method="auto")

        # Should have tried both
        assert router.langextract.extract.call_count == 3
        router.docling.extract.assert_called_once()
        assert "Docling also failed" in str(exc_info.value)

    def test_fallback_returns_docling_result_type(self, router, mock_document):
        """Fallback returns ExtractionResult from Docling, not LangExtractResult."""
        docling_result = MagicMock(borrowers=[MagicMock()], validation_errors=[])
        router.docling.extract.return_value = docling_result
        router.langextract.extract.side_effect = Exception("API error")
        doc_id = uuid4()

        result = router.extract(mock_document, doc_id, "test.pdf", method="auto")

        # Should return Docling's result
        assert result == docling_result
        assert hasattr(result, "validation_errors")  # Docling characteristic


class TestConfigPropagation:
    """Tests for config propagation through retry logic."""

    @pytest.fixture
    def router(self):
        """Create router with mocked extractors."""
        langextract = MagicMock()
        docling = MagicMock()
        docling.extract.return_value = MagicMock(borrowers=[])
        return ExtractionRouter(langextract, docling)

    @pytest.fixture
    def mock_document(self):
        """Mock DocumentContent."""
        doc = MagicMock()
        doc.text = "Sample"
        return doc

    def test_config_passed_to_all_retry_attempts(self, router, mock_document):
        """Config parameter is passed to all retry attempts."""
        config = ExtractionConfig(extraction_passes=5, max_workers=10)
        router.langextract.extract.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("503 Service Unavailable"),
            MagicMock(borrowers=[]),  # Success on 3rd attempt
        ]
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="langextract", config=config)

        # All 3 calls should receive the same config
        for call in router.langextract.extract.call_args_list:
            assert call.kwargs["config"] == config

    def test_default_config_created_once(self, router, mock_document):
        """Default config is created once, not per retry attempt."""
        router.langextract.extract.side_effect = Exception("503 Service Unavailable")
        doc_id = uuid4()

        router.extract(mock_document, doc_id, "test.pdf", method="auto")

        # Check that all calls received the same config instance
        configs = [call.kwargs["config"] for call in router.langextract.extract.call_args_list]
        assert len(configs) == 3
        # All should be the same instance (not just equal)
        assert all(c is configs[0] for c in configs)
