"""Extraction router with method selection and fallback.

Routes between LangExtract and Docling extraction with retry logic
for transient errors and graceful fallback.

LXTR-11: LangExtract extraction errors logged with fallback to Docling
"""

import logging
from typing import Literal
from uuid import UUID

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.extraction.extraction_config import ExtractionConfig
from src.extraction.extractor import BorrowerExtractor, ExtractionResult
from src.extraction.langextract_processor import LangExtractProcessor, LangExtractResult
from src.ingestion.docling_processor import DocumentContent

logger = logging.getLogger(__name__)


class LangExtractTransientError(Exception):
    """Retryable LangExtract error (503, 429, timeout, overloaded)."""

    pass


class LangExtractFatalError(Exception):
    """Non-retryable LangExtract error - triggers immediate fallback."""

    pass


class ExtractionRouter:
    """Routes extraction between LangExtract and Docling with fallback.

    LXTR-11: LangExtract extraction errors logged with fallback to Docling

    Example:
        router = ExtractionRouter(
            langextract_processor=LangExtractProcessor(),
            docling_extractor=BorrowerExtractor(...),
        )
        result = router.extract(document, doc_id, "loan.pdf", method="auto")
    """

    def __init__(
        self,
        langextract_processor: LangExtractProcessor,
        docling_extractor: BorrowerExtractor,
    ):
        """Initialize with both extraction implementations.

        Args:
            langextract_processor: LangExtract-based processor
            docling_extractor: Docling-based BorrowerExtractor
        """
        self.langextract = langextract_processor
        self.docling = docling_extractor

    @retry(
        retry=retry_if_exception_type(LangExtractTransientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
    )
    def _try_langextract(
        self,
        document_text: str,
        document_id: UUID,
        document_name: str,
        raw_text: str | None,
        config: ExtractionConfig,
    ) -> LangExtractResult:
        """Attempt LangExtract with retry on transient errors.

        Args:
            document_text: Docling markdown output
            document_id: Document UUID
            document_name: Document filename
            raw_text: Optional raw text for offset translation
            config: Extraction configuration

        Returns:
            LangExtractResult on success

        Raises:
            LangExtractTransientError: For retryable errors (503, 429, timeout)
            LangExtractFatalError: For non-retryable errors
        """
        try:
            return self.langextract.extract(
                document_text=document_text,
                document_id=document_id,
                document_name=document_name,
                raw_text=raw_text,
                config=config,
            )
        except Exception as e:
            error_str = str(e).lower()
            # Classify transient vs fatal errors
            if any(
                x in error_str
                for x in ["503", "429", "timeout", "overloaded", "rate limit"]
            ):
                logger.warning(
                    "LangExtract transient error for %s, will retry: %s",
                    document_id,
                    str(e),
                )
                raise LangExtractTransientError(str(e)) from e
            logger.error("LangExtract fatal error for %s: %s", document_id, str(e))
            raise LangExtractFatalError(str(e)) from e

    def extract(
        self,
        document: DocumentContent,
        document_id: UUID,
        document_name: str,
        method: Literal["langextract", "docling", "auto"] = "auto",
        config: ExtractionConfig | None = None,
    ) -> ExtractionResult | LangExtractResult:
        """Extract with method selection and fallback.

        LXTR-11: LangExtract extraction errors logged with fallback to Docling

        Args:
            document: Processed document content from Docling
            document_id: Document UUID
            document_name: Document filename
            method: Extraction method:
                - "langextract": LangExtract only (no fallback, raises on error)
                - "docling": Docling only
                - "auto": LangExtract with Docling fallback (default)
            config: Extraction configuration (for langextract)

        Returns:
            ExtractionResult (Docling) or LangExtractResult (LangExtract)
        """
        config = config or ExtractionConfig()

        if method == "docling":
            logger.info("Using Docling extraction for %s", document_id)
            return self.docling.extract(document, document_id, document_name)

        if method == "langextract":
            # LangExtract only - no fallback, will raise on error
            result = self._try_langextract(
                document.text, document_id, document_name, None, config
            )
            logger.info("LangExtract succeeded for %s", document_id)
            return result

        # Auto mode: LangExtract with Docling fallback
        try:
            result = self._try_langextract(
                document.text, document_id, document_name, None, config
            )
            logger.info("LangExtract succeeded for %s (auto mode)", document_id)
            return result
        except (LangExtractTransientError, LangExtractFatalError) as e:
            logger.warning(
                "LangExtract failed for %s after retries: %s. Falling back to Docling.",
                document_id,
                str(e),
            )
            return self.docling.extract(document, document_id, document_name)
