"""LangExtract-based extraction processor for character-level source grounding.

This processor uses Google's LangExtract library to extract borrower data
with precise character-level offsets. Unlike the Docling-based BorrowerExtractor,
this processor populates char_start/char_end in SourceReference.
"""

import logging
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import langextract as lx
from langextract.core.data import AnnotatedDocument, CharInterval

from examples import ALL_EXAMPLES
from src.extraction.offset_translator import OffsetTranslator
from src.models.borrower import Address, BorrowerRecord, IncomeRecord
from src.models.document import SourceReference

logger = logging.getLogger(__name__)


@dataclass
class LangExtractResult:
    """Result from LangExtract extraction.

    Attributes:
        borrowers: Extracted borrower records with char offsets
        raw_extractions: Raw LangExtract result for debugging
        alignment_warnings: Any alignment issues detected
    """

    borrowers: list[BorrowerRecord]
    raw_extractions: AnnotatedDocument | None = None
    alignment_warnings: list[str] = field(default_factory=list)


class LangExtractProcessor:
    """Extract borrower data using LangExtract with character-level source grounding.

    Uses Gemini 3.0 Flash via LangExtract for extraction with precise
    character offset tracking. The few-shot examples define the extraction
    schema - no code-defined schema needed.

    Example:
        processor = LangExtractProcessor()
        result = processor.extract(
            document_text=docling_markdown,
            document_id=uuid,
            document_name="loan.pdf"
        )
    """

    def __init__(self, api_key: str | None = None):
        """Initialize with Gemini API key.

        Args:
            api_key: Gemini API key. If None, uses GOOGLE_API_KEY env var.
        """
        # LangExtract uses LANGEXTRACT_API_KEY env var
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if key:
            os.environ["LANGEXTRACT_API_KEY"] = key

        self.examples = ALL_EXAMPLES
        self._model_id = "gemini-3.0-flash"

    def extract(
        self,
        document_text: str,
        document_id: UUID,
        document_name: str,
        raw_text: str | None = None,
        extraction_passes: int = 2,
    ) -> LangExtractResult:
        """Extract borrower data with character-level source references.

        Args:
            document_text: Docling markdown output to extract from
            document_id: UUID of source document
            document_name: Human-readable document name
            raw_text: Optional raw text for offset translation
            extraction_passes: Number of extraction passes (1-5)

        Returns:
            LangExtractResult with borrowers and metadata
        """
        # Create offset translator for verification
        translator = OffsetTranslator(document_text, raw_text)

        # Run LangExtract
        try:
            result: AnnotatedDocument = lx.extract(
                text_or_documents=document_text,
                prompt_description=self._get_prompt_description(),
                examples=self.examples,
                model_id=self._model_id,
                extraction_passes=extraction_passes,
            )
        except Exception as e:
            logger.error("LangExtract extraction failed: %s", str(e))
            return LangExtractResult(
                borrowers=[],
                alignment_warnings=[f"Extraction failed: {str(e)}"],
            )

        # Convert to BorrowerRecords
        borrowers, warnings = self._convert_to_borrower_records(
            result=result,
            document_id=document_id,
            document_name=document_name,
            source_text=document_text,
            translator=translator,
        )

        return LangExtractResult(
            borrowers=borrowers,
            raw_extractions=result,
            alignment_warnings=warnings,
        )

    def _get_prompt_description(self) -> str:
        """Get the prompt description for LangExtract."""
        return """Extract all borrower information from this loan document including:
- Borrower names and personal identifiers (SSN)
- Contact information (address, phone, email)
- Income records with amounts, periods, years, and employers
- Account numbers and loan numbers

Extract data exactly as it appears in the document. If information is unclear or ambiguous, omit it rather than guessing."""

    def _convert_to_borrower_records(
        self,
        result: AnnotatedDocument,
        document_id: UUID,
        document_name: str,
        source_text: str,
        translator: OffsetTranslator,
    ) -> tuple[list[BorrowerRecord], list[str]]:
        """Convert LangExtract result to BorrowerRecord objects.

        Groups extractions by borrower and creates SourceReference with
        character offsets for each extraction.
        """
        warnings: list[str] = []
        borrower_map: dict[str, dict[str, Any]] = {}  # name -> accumulated data

        for extraction in result.extractions:
            # Get character offsets
            char_start: int | None = None
            char_end: int | None = None

            char_interval: CharInterval | None = extraction.char_interval
            if char_interval:
                char_start = char_interval.start_pos
                char_end = char_interval.end_pos

                # Verify offset (LXTR-08)
                if not translator.verify_offset(
                    char_start, char_end, extraction.extraction_text
                ):
                    warnings.append(
                        f"Offset verification failed for '{extraction.extraction_text[:30]}...'"
                    )

            # Track alignment status
            alignment = getattr(extraction, "alignment_status", None)
            if alignment and alignment != "match_exact":
                warnings.append(
                    f"Fuzzy alignment for '{extraction.extraction_text[:30]}...': {alignment}"
                )

            # Group by extraction class
            if extraction.extraction_class == "borrower":
                self._process_borrower_extraction(
                    extraction,
                    borrower_map,
                    document_id,
                    document_name,
                    source_text,
                    char_start,
                    char_end,
                )
            elif extraction.extraction_class == "income":
                self._process_income_extraction(extraction, borrower_map)
            elif extraction.extraction_class in ("account", "loan"):
                self._process_account_extraction(extraction, borrower_map)

        # Convert accumulated data to BorrowerRecords
        borrowers = []
        for name, data in borrower_map.items():
            try:
                borrower = self._create_borrower_record(name, data)
                borrowers.append(borrower)
            except Exception as e:
                warnings.append(f"Failed to create BorrowerRecord for '{name}': {e}")

        return borrowers, warnings

    def _process_borrower_extraction(
        self,
        extraction: Any,
        borrower_map: dict[str, dict[str, Any]],
        document_id: UUID,
        document_name: str,
        source_text: str,
        char_start: int | None,
        char_end: int | None,
    ) -> None:
        """Process a borrower extraction and add to borrower_map."""
        name = extraction.extraction_text
        attrs = extraction.attributes or {}

        if name not in borrower_map:
            # Create snippet from source text around extraction
            snippet = ""
            if char_start is not None and char_end is not None:
                # Get surrounding context (up to 200 chars)
                ctx_start = max(0, char_start - 50)
                ctx_end = min(len(source_text), char_end + 150)
                snippet = source_text[ctx_start:ctx_end]
            else:
                snippet = source_text[:200] if len(source_text) > 200 else source_text

            borrower_map[name] = {
                "ssn": attrs.get("ssn"),
                "phone": attrs.get("phone"),
                "email": attrs.get("email"),
                "address": (
                    {
                        "street": attrs.get("street"),
                        "city": attrs.get("city"),
                        "state": attrs.get("state"),
                        "zip_code": attrs.get("zip_code"),
                    }
                    if attrs.get("street")
                    else None
                ),
                "income_history": [],
                "account_numbers": [],
                "loan_numbers": [],
                "sources": [
                    SourceReference(
                        document_id=document_id,
                        document_name=document_name,
                        page_number=1,  # LangExtract doesn't track page; default to 1
                        snippet=snippet[:500],  # Limit snippet length
                        char_start=char_start,
                        char_end=char_end,
                    )
                ],
            }
        else:
            # Merge additional data
            if attrs.get("ssn") and not borrower_map[name].get("ssn"):
                borrower_map[name]["ssn"] = attrs["ssn"]
            if attrs.get("phone") and not borrower_map[name].get("phone"):
                borrower_map[name]["phone"] = attrs["phone"]
            if attrs.get("email") and not borrower_map[name].get("email"):
                borrower_map[name]["email"] = attrs["email"]

    def _process_income_extraction(
        self, extraction: Any, borrower_map: dict[str, dict[str, Any]]
    ) -> None:
        """Process an income extraction."""
        attrs = extraction.attributes or {}

        income = {
            "amount": attrs.get("amount"),
            "period": attrs.get("period", "annual"),
            "year": attrs.get("year"),
            "source_type": attrs.get("source_type", "employment"),
            "employer": attrs.get("employer"),
        }

        # Add to first borrower (simplified - real impl would match by employer/context)
        if borrower_map:
            first_borrower = next(iter(borrower_map.values()))
            first_borrower["income_history"].append(income)

    def _process_account_extraction(
        self, extraction: Any, borrower_map: dict[str, dict[str, Any]]
    ) -> None:
        """Process an account or loan extraction."""
        number = extraction.extraction_text

        # Add to first borrower
        if borrower_map:
            first_borrower = next(iter(borrower_map.values()))
            if extraction.extraction_class == "loan":
                first_borrower["loan_numbers"].append(number)
            else:
                first_borrower["account_numbers"].append(number)

    def _create_borrower_record(self, name: str, data: dict[str, Any]) -> BorrowerRecord:
        """Create a BorrowerRecord from accumulated extraction data."""
        address = None
        if data.get("address") and data["address"].get("street"):
            addr_data = data["address"]
            address = Address(
                street=addr_data["street"],
                city=addr_data.get("city", "Unknown"),
                state=addr_data.get("state", "XX"),
                zip_code=addr_data.get("zip_code", "00000"),
            )

        income_history = []
        for inc in data.get("income_history", []):
            if inc.get("amount") and inc.get("year"):
                try:
                    amount = Decimal(
                        str(inc["amount"]).replace(",", "").replace("$", "")
                    )
                    year = int(inc["year"])
                    income_history.append(
                        IncomeRecord(
                            amount=amount,
                            period=inc.get("period", "annual"),
                            year=year,
                            source_type=inc.get("source_type", "employment"),
                            employer=inc.get("employer"),
                        )
                    )
                except (ValueError, TypeError):
                    pass  # Skip invalid income records

        return BorrowerRecord(
            id=uuid4(),
            name=name,
            ssn=data.get("ssn"),
            phone=data.get("phone"),
            email=data.get("email"),
            address=address,
            income_history=income_history,
            account_numbers=data.get("account_numbers", []),
            loan_numbers=data.get("loan_numbers", []),
            sources=data.get("sources", []),
            confidence_score=0.8,  # LangExtract extractions are high confidence
        )
