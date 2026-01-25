# Phase 11: LangExtract Core Integration - Research

**Researched:** 2026-01-24
**Domain:** LangExtract library, Gemini 3.0 Flash extraction, character-level source grounding, few-shot examples
**Confidence:** HIGH

## Summary

Phase 11 integrates Google's LangExtract library into the existing loan document extraction system to provide character-level source grounding. LangExtract was released in July 2025 and provides precise source attribution by mapping every extraction to exact character offsets in the source text. The library uses few-shot examples to define extraction schemas without requiring model fine-tuning.

The existing v1.0 system uses Gemini 3.0 Flash with custom prompts via `google-genai` for extraction, producing BorrowerRecord objects with page-level SourceReference. Phase 11 adds a parallel LangExtractProcessor that extracts the same entity types but with character-level offsets (char_start, char_end) in SourceReference. The SourceReference database model needs two new nullable columns for backward compatibility with existing v1.0 extractions.

The key technical challenge is **offset translation** between Docling's markdown output (which LangExtract will receive) and the raw/original text positions. Docling converts PDF/DOCX to structured markdown with formatting changes, so character positions in the markdown don't correspond directly to positions in the original document. This requires an offset translation layer that Phase 11 must implement.

**Primary recommendation:** Install LangExtract v1.1.1, create few-shot examples using verbatim text from sample loan documents, add char_start/char_end nullable columns to SourceReference, and implement an OffsetTranslator class that tracks Docling's text transformations.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langextract | 1.1.1 | Source-grounded extraction | Official Google library, Gemini-optimized, character offsets built-in |
| google-genai | 1.60.0+ | Gemini API client | Already in project, LangExtract can use same API key |
| alembic | 1.18.0+ | Database migrations | Already in project for schema changes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| difflib | stdlib | Fuzzy text alignment | For offset translation verification |
| rapidfuzz | 3.0.0+ | Fast fuzzy matching | Already installed, use for alignment fallback |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangExtract | Custom prompt engineering | LangExtract provides battle-tested offset alignment; custom solution risks bugs |
| Gemini 3.0 Flash | Gemini 3.0 Pro | Pro is more expensive; Flash has proven sufficient and is LangExtract's recommended model |

**Installation:**
```bash
# Add to pyproject.toml dependencies
pip install langextract==1.1.1
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── src/
│   ├── extraction/
│   │   ├── extractor.py           # Existing BorrowerExtractor (Docling path)
│   │   ├── langextract_processor.py  # NEW: LangExtract extraction
│   │   ├── offset_translator.py      # NEW: Docling markdown to raw text alignment
│   │   └── prompts.py             # Existing prompts (enhanced for LangExtract)
│   ├── models/
│   │   └── document.py            # SourceReference (add char_start/char_end)
│   └── storage/
│       └── models.py              # ORM SourceReference (add columns)
├── examples/                       # NEW: Few-shot examples directory
│   ├── __init__.py
│   ├── borrower_examples.py       # Few-shot examples for borrower extraction
│   ├── income_examples.py         # Few-shot examples for income records
│   └── account_examples.py        # Few-shot examples for account numbers
└── alembic/
    └── versions/
        └── 002_add_char_offsets.py  # Migration for nullable offset columns
```

### Pattern 1: LangExtract Extraction with Few-Shot Examples
**What:** Define extraction schema through examples, not code
**When to use:** For all LangExtract extractions
**Example:**
```python
# Source: https://github.com/google/langextract
import langextract as lx

# Define few-shot example with verbatim text
borrower_example = lx.data.ExampleData(
    text="""John Smith
SSN: 123-45-6789
Address: 123 Main Street, Dallas, TX 75201
Phone: (214) 555-1234
Annual Income: $85,000 (2025)""",
    extractions=[
        lx.data.Extraction(
            extraction_class="borrower",
            extraction_text="John Smith",
            attributes={
                "ssn": "123-45-6789",
                "street": "123 Main Street",
                "city": "Dallas",
                "state": "TX",
                "zip_code": "75201",
                "phone": "(214) 555-1234"
            }
        ),
        lx.data.Extraction(
            extraction_class="income",
            extraction_text="$85,000 (2025)",
            attributes={
                "amount": "85000",
                "period": "annual",
                "year": "2025",
                "source_type": "employment"
            }
        )
    ]
)

# Extract from new document
result = lx.extract(
    text_or_documents=docling_markdown_output,
    prompt_description="Extract all borrower information including names, SSN, address, phone, income records, and account numbers from this loan document.",
    examples=[borrower_example],
    model_id="gemini-3.0-flash"
)
```

### Pattern 2: Character Offset Access
**What:** Retrieve char_start/char_end from LangExtract results
**When to use:** When storing source references
**Example:**
```python
# Source: https://github.com/google/langextract/blob/v1.0.0/langextract/data.py
from langextract.core.data import AnnotatedDocument, Extraction, CharInterval

def extract_offsets(result: AnnotatedDocument) -> list[dict]:
    """Extract character offsets from LangExtract result."""
    references = []
    for extraction in result.extractions:
        char_interval: CharInterval | None = extraction.char_interval
        if char_interval:
            references.append({
                "extraction_class": extraction.extraction_class,
                "text": extraction.extraction_text,
                "char_start": char_interval.start_pos,  # inclusive
                "char_end": char_interval.end_pos,      # exclusive
                "attributes": extraction.attributes,
                "alignment_status": extraction.alignment_status,  # "match_exact" or "match_fuzzy"
            })
    return references
```

### Pattern 3: Offset Translation Layer
**What:** Map Docling markdown positions to original document positions
**When to use:** When displaying source highlights or verifying offsets
**Example:**
```python
# Custom implementation required - no standard library
class OffsetTranslator:
    """Translate character offsets between Docling markdown and raw text."""

    def __init__(self, docling_markdown: str, raw_text: str):
        self.markdown = docling_markdown
        self.raw = raw_text
        self._build_alignment_map()

    def _build_alignment_map(self):
        """Build bidirectional character position mapping."""
        # Strategy: Find anchor points (exact substring matches)
        # and interpolate positions between anchors
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, self.markdown, self.raw)
        self.matches = matcher.get_matching_blocks()

    def markdown_to_raw(self, start: int, end: int) -> tuple[int, int]:
        """Convert markdown character positions to raw text positions."""
        # Find closest anchor points and interpolate
        # Return (raw_start, raw_end) or (None, None) if not mappable
        pass

    def verify_offset(self, char_start: int, char_end: int, expected_text: str) -> bool:
        """Verify that offsets correctly locate the expected text."""
        actual = self.markdown[char_start:char_end]
        return actual == expected_text or self._fuzzy_match(actual, expected_text) > 0.85
```

### Pattern 4: Nullable Schema Migration (Backward Compatibility)
**What:** Add char_start/char_end as nullable columns
**When to use:** For database schema evolution
**Example:**
```python
# Source: https://alembic.sqlalchemy.org/en/latest/ops.html
# alembic/versions/002_add_char_offsets.py
def upgrade() -> None:
    # Add nullable columns - no data migration needed for new columns
    op.add_column(
        "source_references",
        sa.Column("char_start", sa.Integer(), nullable=True)
    )
    op.add_column(
        "source_references",
        sa.Column("char_end", sa.Integer(), nullable=True)
    )

def downgrade() -> None:
    op.drop_column("source_references", "char_end")
    op.drop_column("source_references", "char_start")
```

### Anti-Patterns to Avoid
- **Non-verbatim few-shot examples:** LangExtract requires extraction_text to match source text exactly; paraphrased examples cause "Prompt alignment warnings"
- **Assuming 1:1 offset mapping:** Docling markdown has different character positions than raw PDF text; MUST implement translation
- **Making char_start/char_end NOT NULL:** Breaks backward compatibility with v1.0 Docling extractions
- **Using Gemini Pro for all extractions:** Flash is faster, cheaper, and recommended by LangExtract for most cases

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Character-level source grounding | Custom offset tracking prompts | LangExtract | LangExtract handles fuzzy alignment, multiple occurrences, edge cases |
| Text alignment/matching | Simple string.find() | LangExtract's resolver + difflib | LangExtract has configurable similarity thresholds (0.85 default) |
| Few-shot schema definition | Complex JSON schema | LangExtract ExampleData | Examples are more intuitive, LangExtract infers schema |
| Substring verification | Manual position checking | LangExtract's alignment_status | Returns "match_exact" vs "match_fuzzy" per extraction |

**Key insight:** LangExtract solves the hard problems (fuzzy alignment, LLM hallucination detection, multiple occurrence disambiguation). The custom work is limited to: (1) defining domain-specific examples, (2) offset translation for Docling markdown.

## Common Pitfalls

### Pitfall 1: Few-Shot Example Text Mismatch
**What goes wrong:** LangExtract raises "Prompt alignment warnings" and extraction quality degrades
**Why it happens:** extraction_text in examples doesn't exactly match the source text (whitespace, punctuation differences)
**How to avoid:**
1. Copy-paste text directly from sample documents
2. Run `lx.validate_examples(examples)` before production
3. Use real loan document text, not synthetic examples
**Warning signs:** LangExtract warns "extraction_text should ideally be verbatim from the example's text"

### Pitfall 2: Offset Position Confusion (Inclusive vs Exclusive)
**What goes wrong:** Substring extraction off by one character
**Why it happens:** CharInterval uses `start_pos` (inclusive) and `end_pos` (exclusive) like Python slicing
**How to avoid:**
1. Use `text[char_start:char_end]` directly - Python slicing semantics match
2. Add verification: assert extracted_text == text[char_start:char_end]
**Warning signs:** Off-by-one errors in highlighted text

### Pitfall 3: Docling Markdown vs Raw Text Offset Mismatch
**What goes wrong:** Character offsets point to wrong text when using original document
**Why it happens:** Docling adds markdown formatting (headers, lists, bold) that shifts character positions
**How to avoid:**
1. Store BOTH the markdown text LangExtract processed AND the raw text
2. Implement OffsetTranslator class for position mapping
3. Use markdown offsets for LangExtract verification, translated offsets for UI display
**Warning signs:** Highlighted text doesn't match expected borrower name/value

### Pitfall 4: API Key Configuration
**What goes wrong:** LangExtract fails with authentication errors
**Why it happens:** LangExtract uses LANGEXTRACT_API_KEY env var, project uses GOOGLE_API_KEY
**How to avoid:**
1. Set both env vars to same value, OR
2. Configure LangExtract to use existing google-genai client
3. Test locally before deployment
**Warning signs:** "API key not found" or "Invalid API key" errors

### Pitfall 5: Large Document Performance
**What goes wrong:** Extraction takes too long or hits rate limits
**Why it happens:** LangExtract processes entire document by default; long documents need chunking
**How to avoid:**
1. Use `extraction_passes=3` for thorough extraction on important docs
2. Use `max_workers=20` for parallel chunk processing
3. Use `max_char_buffer=1000` to limit context per extraction
**Warning signs:** Timeouts, Gemini rate limit errors (429)

## Code Examples

Verified patterns from official sources:

### LangExtractProcessor Class Structure
```python
# Source: https://github.com/google/langextract
import langextract as lx
from uuid import UUID
from src.models.document import SourceReference
from src.models.borrower import BorrowerRecord

class LangExtractProcessor:
    """Extract borrower data using LangExtract with character-level source grounding."""

    def __init__(self, api_key: str | None = None):
        """Initialize with Gemini API key."""
        import os
        if api_key:
            os.environ["LANGEXTRACT_API_KEY"] = api_key

        # Load few-shot examples
        from examples.borrower_examples import BORROWER_EXAMPLES
        self.examples = BORROWER_EXAMPLES

    def extract(
        self,
        document_text: str,  # Docling markdown output
        document_id: UUID,
        document_name: str,
    ) -> list[BorrowerRecord]:
        """Extract borrowers with character-level source references."""
        result = lx.extract(
            text_or_documents=document_text,
            prompt_description=self._get_prompt_description(),
            examples=self.examples,
            model_id="gemini-3.0-flash",
            extraction_passes=2,  # Multiple passes for better recall
        )

        return self._convert_to_borrower_records(
            result, document_id, document_name, document_text
        )

    def _get_prompt_description(self) -> str:
        return """Extract all borrower information from this loan document including:
- Borrower names and personal identifiers (SSN)
- Contact information (address, phone, email)
- Income records with amounts, periods, years, and employers
- Account numbers and loan numbers
Extract data exactly as it appears. If information is unclear, omit it."""

    def _convert_to_borrower_records(
        self,
        result: lx.data.AnnotatedDocument,
        document_id: UUID,
        document_name: str,
        source_text: str,
    ) -> list[BorrowerRecord]:
        """Convert LangExtract result to BorrowerRecord objects."""
        borrowers = []
        # Group extractions by borrower name
        # ... implementation details
        return borrowers
```

### Few-Shot Example Definition
```python
# Source: https://github.com/google/langextract
# examples/borrower_examples.py
import langextract as lx

# CRITICAL: extraction_text MUST be verbatim from sample text
SAMPLE_LOAN_TEXT_1 = """BORROWER INFORMATION

Primary Borrower: Sarah Johnson
Social Security Number: 987-65-4321
Current Address: 456 Oak Avenue, Apartment 12B, Houston, TX 77001
Phone: (713) 555-9876
Email: sarah.johnson@email.com

EMPLOYMENT INCOME
Employer: TechCorp Industries
Position: Senior Engineer
Annual Salary: $125,000 (2025)
Annual Salary: $118,000 (2024)

ACCOUNT INFORMATION
Checking Account: 1234567890
Loan Number: LN-2025-001234"""

BORROWER_EXAMPLES = [
    lx.data.ExampleData(
        text=SAMPLE_LOAN_TEXT_1,
        extractions=[
            lx.data.Extraction(
                extraction_class="borrower",
                extraction_text="Sarah Johnson",
                attributes={
                    "ssn": "987-65-4321",
                    "street": "456 Oak Avenue, Apartment 12B",
                    "city": "Houston",
                    "state": "TX",
                    "zip_code": "77001",
                    "phone": "(713) 555-9876",
                    "email": "sarah.johnson@email.com"
                }
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$125,000 (2025)",
                attributes={
                    "amount": "125000",
                    "period": "annual",
                    "year": "2025",
                    "source_type": "employment",
                    "employer": "TechCorp Industries"
                }
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$118,000 (2024)",
                attributes={
                    "amount": "118000",
                    "period": "annual",
                    "year": "2024",
                    "source_type": "employment",
                    "employer": "TechCorp Industries"
                }
            ),
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="1234567890",
                attributes={"account_type": "checking"}
            ),
            lx.data.Extraction(
                extraction_class="loan",
                extraction_text="LN-2025-001234",
                attributes={"loan_type": "unknown"}
            ),
        ]
    ),
]
```

### Offset Verification Test
```python
# Source: Verification pattern from requirements LXTR-08
def test_character_offset_verification():
    """Verify character offsets via substring matching."""
    import langextract as lx

    test_text = "Borrower: John Smith, SSN: 123-45-6789"

    # Mock or real extraction
    result = lx.extract(
        text_or_documents=test_text,
        prompt_description="Extract borrower name and SSN",
        examples=BORROWER_EXAMPLES,
        model_id="gemini-3.0-flash"
    )

    # Verify each extraction's offsets
    for extraction in result.extractions:
        if extraction.char_interval:
            start = extraction.char_interval.start_pos
            end = extraction.char_interval.end_pos

            # Substring verification
            actual_text = test_text[start:end]
            expected_text = extraction.extraction_text

            # Must match exactly OR be fuzzy match
            assert actual_text == expected_text or \
                extraction.alignment_status == "match_fuzzy", \
                f"Offset mismatch: expected '{expected_text}' at [{start}:{end}], got '{actual_text}'"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Page-level source references | Character-level offsets | LangExtract launch July 2025 | Precise source highlighting, better verification |
| Custom prompt engineering for offsets | LangExtract's built-in grounding | July 2025 | Eliminates hallucination of positions |
| JSON schema definition | Few-shot examples | Industry trend 2025 | More intuitive, better LLM understanding |
| Single extraction pass | Multi-pass extraction | LangExtract optimization | Higher recall on long documents |

**Deprecated/outdated:**
- Manual character position prompting: LangExtract handles this automatically
- Gemini 2.5 Flash: Gemini 3.0 Flash offers 10 percentage-point accuracy lift on PDFs

## Open Questions

Things that couldn't be fully resolved:

1. **Docling markdown to raw text offset mapping**
   - What we know: Docling converts to markdown with added formatting; offsets won't match
   - What's unclear: Exact mapping algorithm; whether Docling exposes any position metadata
   - Recommendation: Implement OffsetTranslator as separate utility; may need to store both markdown offsets and "display" positions

2. **LangExtract + existing google-genai client sharing**
   - What we know: LangExtract uses LANGEXTRACT_API_KEY; project uses GOOGLE_API_KEY via google-genai
   - What's unclear: Whether LangExtract can use existing client or requires separate key config
   - Recommendation: Set both env vars to same value for simplicity

3. **Few-shot example versioning strategy**
   - What we know: Examples stored in examples/ directory per LXTR-12
   - What's unclear: How to handle example updates without breaking existing extractions
   - Recommendation: Version examples in separate files (v1/, v2/) or via git tags

## Sources

### Primary (HIGH confidence)
- [GitHub - google/langextract](https://github.com/google/langextract) - Official library, API reference, data models
- [PyPI - langextract](https://pypi.org/project/langextract/) - Version 1.1.1, Python >=3.10 requirement
- [LangExtract data.py](https://github.com/google/langextract/blob/v1.0.0/langextract/data.py) - CharInterval, Extraction, AnnotatedDocument classes
- [Google Developers Blog - Introducing LangExtract](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/) - Official announcement, feature overview

### Secondary (MEDIUM confidence)
- [Demystifying Text Anchoring in LangExtract](https://shanechang.com/p/demystifying-text-anchoring-langextract/) - Deep dive on fuzzy alignment implementation
- [Gemini 3 Flash Documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash) - Model capabilities for document extraction
- [Box Blog - Gemini 3 Flash Accuracy](https://blog.box.com/gemini-3-flash-sets-new-standard-accuracy-unstructured-data-extraction) - 10 percentage-point lift on PDFs

### Tertiary (LOW confidence)
- [Alembic Operation Reference](https://alembic.sqlalchemy.org/en/latest/ops.html) - add_column for migrations (verified pattern)

## Metadata

**Confidence breakdown:**
- LangExtract API/data models: HIGH - Official GitHub source code reviewed
- Character offset format: HIGH - CharInterval class definition verified
- Few-shot example format: HIGH - Official documentation and code examples
- Docling offset translation: LOW - No official solution found, custom implementation required
- Gemini 3.0 Flash integration: HIGH - LangExtract documentation recommends this model

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - LangExtract is stable at v1.1.1)

## Phase 11 Requirements Mapping

| Requirement | Research Finding | Confidence |
|-------------|------------------|------------|
| LXTR-01: char_start/char_end in SourceReference | CharInterval.start_pos (inclusive), .end_pos (exclusive) | HIGH |
| LXTR-02: Nullable offsets for backward compatibility | Alembic add_column with nullable=True | HIGH |
| LXTR-03: LangExtractProcessor with Gemini 3.0 Flash | `lx.extract(model_id="gemini-3.0-flash")` | HIGH |
| LXTR-04: Few-shot examples for loan entities | ExampleData class with borrower/income/account extraction_class | HIGH |
| LXTR-05: Verbatim text from sample documents | CRITICAL requirement - LangExtract validates alignment | HIGH |
| LXTR-08: Character offset verification | `text[start_pos:end_pos] == extraction_text` + alignment_status | HIGH |
| LXTR-09: Offset translation layer | Custom OffsetTranslator needed (Docling markdown != raw) | LOW |
| LXTR-12: Examples in examples/ directory | Standard Python package structure with version files | HIGH |
