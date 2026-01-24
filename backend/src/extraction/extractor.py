"""BorrowerExtractor: Main orchestrator for document extraction pipeline.

This module ties together all extraction components:
- ComplexityClassifier: Routes to Flash vs Pro model
- DocumentChunker: Splits large documents
- GeminiClient: LLM extraction
- BorrowerDeduplicator: Merges duplicate records
- FieldValidator: Validates extracted fields
- ConfidenceCalculator: Scores extraction confidence

The extractor coordinates these components to:
1. Assess document complexity
2. Chunk large documents
3. Extract borrowers from each chunk
4. Deduplicate merged records
5. Validate and score results
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import ValidationError as PydanticValidationError

from src.extraction.chunker import DocumentChunker
from src.extraction.complexity_classifier import (
    ComplexityAssessment,
    ComplexityClassifier,
    ComplexityLevel,
)
from src.extraction.confidence import ConfidenceCalculator
from src.extraction.deduplication import BorrowerDeduplicator
from src.extraction.llm_client import GeminiClient
from src.extraction.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt
from src.extraction.schemas import (
    BorrowerExtractionResult,
    ExtractedBorrower,
)
from src.extraction.validation import FieldValidator, ValidationError
from src.ingestion.docling_processor import DocumentContent
from src.models.borrower import Address, BorrowerRecord, IncomeRecord
from src.models.document import SourceReference

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Complete result from document extraction.

    Attributes:
        borrowers: Deduplicated list of extracted borrowers
        complexity: Document complexity assessment
        chunks_processed: Number of chunks extracted from
        total_tokens: Total tokens used across all chunks
        validation_errors: All validation errors found
        consistency_warnings: Consistency issues flagged for review (added by Plan 03-05)
    """

    borrowers: list[BorrowerRecord]
    complexity: ComplexityAssessment
    chunks_processed: int
    total_tokens: int
    validation_errors: list[ValidationError] = field(default_factory=list)
    consistency_warnings: list = field(default_factory=list)


class BorrowerExtractor:
    """Orchestrates the full borrower extraction pipeline.

    Coordinates complexity assessment, chunking, LLM extraction,
    deduplication, validation, and confidence scoring.

    Example:
        extractor = BorrowerExtractor(
            llm_client=GeminiClient(),
            classifier=ComplexityClassifier(),
            chunker=DocumentChunker(),
            validator=FieldValidator(),
            confidence_calc=ConfidenceCalculator(),
            deduplicator=BorrowerDeduplicator(),
        )
        result = extractor.extract(doc_content, doc_id, "loan.pdf")
    """

    def __init__(
        self,
        llm_client: GeminiClient,
        classifier: ComplexityClassifier,
        chunker: DocumentChunker,
        validator: FieldValidator,
        confidence_calc: ConfidenceCalculator,
        deduplicator: BorrowerDeduplicator,
    ) -> None:
        """Initialize extractor with required components.

        Args:
            llm_client: Gemini client for LLM extraction
            classifier: Complexity classifier for model routing
            chunker: Document chunker for large documents
            validator: Field validator for format checking
            confidence_calc: Confidence calculator for scoring
            deduplicator: Deduplicator for merging duplicates
        """
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
    ) -> ExtractionResult:
        """Extract borrower data from a document.

        Args:
            document: Processed document content from Docling
            document_id: UUID of the source document
            document_name: Human-readable document name

        Returns:
            ExtractionResult with extracted borrowers and metadata
        """
        # Step 1: Assess complexity
        assessment = self.classifier.classify(document.text, document.page_count)
        use_pro = assessment.level == ComplexityLevel.COMPLEX

        # Step 2: Chunk document
        chunks = self.chunker.chunk(document.text)

        # Step 3: Extract from each chunk
        all_borrowers: list[BorrowerRecord] = []
        total_tokens = 0
        all_validation_errors: list[ValidationError] = []

        for chunk in chunks:
            # Find page number for this chunk
            page_number = self._find_page_for_position(document, chunk.start_char)

            # Build prompt
            prompt = build_extraction_prompt(chunk.text)

            # Call LLM
            response = self.llm_client.extract(
                text=prompt,
                schema=BorrowerExtractionResult,
                use_pro=use_pro,
                system_instruction=EXTRACTION_SYSTEM_PROMPT,
            )

            total_tokens += response.input_tokens + response.output_tokens

            # Process extracted borrowers
            if response.parsed and isinstance(response.parsed, BorrowerExtractionResult):
                extraction_result = response.parsed
                for extracted in extraction_result.borrowers:
                    # Create snippet from chunk (first 200 chars)
                    snippet = chunk.text[:200] if len(chunk.text) > 200 else chunk.text

                    # Convert to BorrowerRecord (may fail due to Pydantic validation)
                    try:
                        borrower = self._convert_to_borrower_record(
                            extracted=extracted,
                            document_id=document_id,
                            document_name=document_name,
                            page_number=page_number,
                            snippet=snippet,
                        )
                        all_borrowers.append(borrower)
                    except PydanticValidationError as e:
                        # Track validation errors from Pydantic
                        for error in e.errors():
                            field_name = str(error.get("loc", ["unknown"])[0])
                            all_validation_errors.append(
                                ValidationError(
                                    field=field_name,
                                    value=str(error.get("input", "")),
                                    error_type="FORMAT",
                                    message=error.get("msg", "Validation failed"),
                                )
                            )
                        logger.warning(
                            "Failed to convert extracted borrower '%s': %s",
                            extracted.name,
                            str(e),
                        )

        # Step 4: Deduplicate
        merged = self.deduplicator.deduplicate(all_borrowers)

        # Step 5: Validate and score each borrower
        for borrower in merged:
            # Validate fields
            validation_passed = True

            # Validate SSN
            ssn_result = self.validator.validate_ssn(borrower.ssn)
            if not ssn_result.is_valid:
                all_validation_errors.extend(ssn_result.errors)
                validation_passed = False

            # Validate phone
            phone_result = self.validator.validate_phone(borrower.phone)
            if not phone_result.is_valid:
                all_validation_errors.extend(phone_result.errors)
                validation_passed = False

            # Validate ZIP if address exists
            if borrower.address:
                zip_result = self.validator.validate_zip(borrower.address.zip_code)
                if not zip_result.is_valid:
                    all_validation_errors.extend(zip_result.errors)
                    validation_passed = False

            # Validate income years
            for income in borrower.income_history:
                year_result = self.validator.validate_year(income.year)
                if not year_result.is_valid:
                    all_validation_errors.extend(year_result.errors)
                    validation_passed = False

            # Calculate confidence score
            breakdown = self.confidence_calc.calculate(
                record=borrower,
                format_validation_passed=validation_passed,
                source_count=len(borrower.sources),
            )

            # Update borrower with new confidence score
            # Note: BorrowerRecord is a Pydantic model, so we recreate it
            # For now, we'll mutate (Pydantic allows this with model_config)
            object.__setattr__(borrower, "confidence_score", breakdown.total)

        return ExtractionResult(
            borrowers=merged,
            complexity=assessment,
            chunks_processed=len(chunks),
            total_tokens=total_tokens,
            validation_errors=all_validation_errors,
        )

    def _find_page_for_position(
        self, document: DocumentContent, char_pos: int
    ) -> int:
        """Find the page number for a character position in the document.

        Args:
            document: Document with page-level content
            char_pos: Character position in full document text

        Returns:
            Page number (1-indexed), defaults to 1 if cannot determine
        """
        # If we have page-level text, try to find which page contains the position
        if document.pages:
            cumulative_len = 0
            for page in document.pages:
                page_len = len(page.text) if page.text else 0
                if cumulative_len + page_len > char_pos:
                    return page.page_number
                cumulative_len += page_len

            # If position is beyond all pages, return last page
            if document.pages:
                return document.pages[-1].page_number

        # Fallback: estimate based on total length and page count
        if document.page_count > 0 and len(document.text) > 0:
            chars_per_page = len(document.text) / document.page_count
            estimated_page = int(char_pos / chars_per_page) + 1
            return min(estimated_page, document.page_count)

        return 1

    def _convert_to_borrower_record(
        self,
        extracted: ExtractedBorrower,
        document_id: UUID,
        document_name: str,
        page_number: int,
        snippet: str,
    ) -> BorrowerRecord:
        """Convert an ExtractedBorrower to a BorrowerRecord.

        Args:
            extracted: LLM extraction result
            document_id: Source document UUID
            document_name: Source document name
            page_number: Page number in source document
            snippet: Text snippet from extraction location

        Returns:
            BorrowerRecord with source attribution
        """
        # Create source reference
        source = SourceReference(
            document_id=document_id,
            document_name=document_name,
            page_number=page_number,
            snippet=snippet,
        )

        # Convert address if present
        address = None
        if extracted.address:
            address = Address(
                street=extracted.address.street,
                city=extracted.address.city,
                state=extracted.address.state,
                zip_code=extracted.address.zip_code,
            )

        # Convert income history (float -> Decimal)
        income_history = [
            IncomeRecord(
                amount=Decimal(str(income.amount)),
                period=income.period,
                year=income.year,
                source_type=income.source_type,
                employer=income.employer,
            )
            for income in extracted.income_history
        ]

        return BorrowerRecord(
            id=uuid4(),
            name=extracted.name,
            ssn=extracted.ssn,
            phone=extracted.phone,
            email=extracted.email,
            address=address,
            income_history=income_history,
            account_numbers=list(extracted.account_numbers),
            loan_numbers=list(extracted.loan_numbers),
            sources=[source],
            confidence_score=0.5,  # Initial score, updated after validation
        )
