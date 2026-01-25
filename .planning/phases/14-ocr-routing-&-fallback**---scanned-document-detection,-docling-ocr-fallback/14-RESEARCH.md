# Phase 14: OCR Routing & Fallback - Research

**Researched:** 2026-01-25
**Domain:** Scanned Document Detection, OCR Routing, Circuit Breaker Fallback Patterns
**Confidence:** HIGH

## Summary

Phase 14 implements intelligent OCR routing that automatically detects scanned documents and routes them to the LightOnOCR GPU service, while using direct text extraction for native PDFs. When the GPU service is unavailable, the system falls back to Docling's built-in OCR capabilities.

The key challenge is reliably distinguishing scanned PDFs (image-based, requiring OCR) from native PDFs (text-layer present, direct extraction possible). Research confirms multiple heuristic approaches: text extraction ratio, image coverage analysis, and font detection. The recommended approach is **text extraction ratio with page-level checks** using pypdfium2, which is already a dependency via Docling.

For GPU service fallback, the existing tenacity retry pattern (from ExtractionRouter) combined with a circuit breaker pattern ensures graceful degradation. The aiobreaker library provides native asyncio support for circuit breaker implementation.

**Primary recommendation:** Use pypdfium2 to detect scanned pages via text extraction ratio (text chars / expected chars threshold), implement circuit breaker around LightOnOCRClient, and fall back to Docling's do_ocr=True mode when GPU service is unavailable.

## Standard Stack

The established tools for this OCR routing implementation:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pypdfium2 | (via Docling) | PDF text layer detection | Already a dependency, fast PDFium bindings |
| aiobreaker | 1.2+ | Circuit breaker for GPU service | Native asyncio support, simple API |
| tenacity | 9.0+ | Retry logic | Already used in ExtractionRouter |
| LightOnOCRClient | (Phase 13) | GPU OCR service client | Existing implementation from Phase 13 |
| DoclingProcessor | (existing) | Fallback OCR | Built-in OCR via do_ocr=True |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28+ | HTTP client | Health checks, API calls (existing) |
| structlog | 25.5+ | Structured logging | OCR routing decision logging |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pypdfium2 text ratio | PyMuPDF image coverage | PyMuPDF adds dependency; pypdfium2 already installed |
| aiobreaker | pybreaker | pybreaker uses Tornado; aiobreaker is native asyncio |
| Character ratio threshold | Page count vs image count | Ratio is more reliable for mixed documents |

**Installation:**
```bash
pip install aiobreaker  # New dependency for circuit breaker
# pypdfium2, tenacity, httpx already installed
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
  src/
    ocr/
      __init__.py              # Exports OCRRouter, ScannedDocumentDetector
      lightonocr_client.py     # Existing GPU service client
      scanned_detector.py      # NEW: Scanned document detection
      ocr_router.py            # NEW: OCR routing with fallback
```

### Pattern 1: Scanned Document Detection via Text Ratio

**What:** Detect scanned pages by checking if extractable text is below a threshold relative to page size.
**When to use:** Before routing a document to OCR
**Example:**
```python
# Source: PyMuPDF discussions, pypdf documentation patterns
import pypdfium2 as pdfium

class ScannedDocumentDetector:
    """Detect scanned/image-based pages in PDF documents.

    LOCR-05: Scanned document detection implemented (auto OCR routing)

    Uses text extraction ratio: if extractable characters per page
    is below threshold, the page is likely a scanned image.
    """

    # Minimum characters per page to consider it "native" (has text layer)
    MIN_CHARS_THRESHOLD = 50

    # Ratio of scanned pages to trigger full-document OCR
    SCANNED_PAGE_RATIO_THRESHOLD = 0.5

    def detect_page_needs_ocr(self, page: pdfium.PdfPage) -> bool:
        """Check if a single page needs OCR.

        Args:
            page: pypdfium2 PdfPage object

        Returns:
            True if page appears to be scanned (needs OCR)
        """
        textpage = page.get_textpage()
        text = textpage.get_text_bounded()

        # If we extracted meaningful text, page has a text layer
        if text and len(text.strip()) >= self.MIN_CHARS_THRESHOLD:
            return False

        return True

    def detect_document_needs_ocr(self, pdf_bytes: bytes) -> tuple[bool, list[int]]:
        """Analyze entire document for OCR need.

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Tuple of (needs_ocr: bool, scanned_page_indices: list[int])
        """
        pdf = pdfium.PdfDocument(pdf_bytes)
        scanned_pages = []

        for i in range(len(pdf)):
            page = pdf[i]
            if self.detect_page_needs_ocr(page):
                scanned_pages.append(i)

        # Document needs OCR if majority of pages are scanned
        ratio = len(scanned_pages) / len(pdf) if len(pdf) > 0 else 0
        needs_ocr = ratio >= self.SCANNED_PAGE_RATIO_THRESHOLD

        return needs_ocr, scanned_pages
```

### Pattern 2: Circuit Breaker for GPU Service

**What:** Prevent cascading failures when GPU service is unavailable
**When to use:** Wrap LightOnOCRClient calls
**Example:**
```python
# Source: aiobreaker documentation
from datetime import timedelta
from aiobreaker import CircuitBreaker

from src.ocr.lightonocr_client import LightOnOCRClient, LightOnOCRError

# Circuit breaker for GPU OCR service
# Opens after 3 failures, resets after 60 seconds
gpu_ocr_breaker = CircuitBreaker(
    fail_max=3,
    reset_timeout=timedelta(seconds=60),
    exclude=[LightOnOCRError],  # Don't trip on expected errors
)

class OCRRouter:
    """Routes OCR between GPU service and Docling fallback.

    LOCR-05: Scanned document detection implemented (auto OCR routing)
    LOCR-11: Fallback to Docling OCR when GPU service unavailable
    """

    def __init__(
        self,
        lightonocr_client: LightOnOCRClient,
        docling_processor: DoclingProcessor,
    ):
        self.gpu_client = lightonocr_client
        self.docling = docling_processor
        self.detector = ScannedDocumentDetector()

    @gpu_ocr_breaker
    async def _try_gpu_ocr(self, image_bytes: bytes) -> str:
        """Attempt GPU OCR with circuit breaker protection."""
        return await self.gpu_client.extract_text(image_bytes)

    async def process_with_ocr(
        self,
        pdf_bytes: bytes,
        filename: str,
    ) -> DocumentContent:
        """Process document with intelligent OCR routing.

        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Original filename

        Returns:
            DocumentContent with extracted text
        """
        needs_ocr, scanned_pages = self.detector.detect_document_needs_ocr(pdf_bytes)

        if not needs_ocr:
            # Native PDF - use direct text extraction (no OCR)
            return self.docling.process_bytes(pdf_bytes, filename)

        # Try GPU OCR first
        try:
            # Convert scanned pages to images and OCR
            text_parts = await self._ocr_scanned_pages(pdf_bytes, scanned_pages)
            # ... combine with native page text
        except CircuitBreakerError:
            logger.warning("GPU OCR circuit open, falling back to Docling OCR")
            return self._docling_ocr_fallback(pdf_bytes, filename)
```

### Pattern 3: Docling OCR Fallback Configuration

**What:** Configure Docling to perform OCR when GPU service unavailable
**When to use:** Circuit breaker is open OR GPU service health check fails
**Example:**
```python
# Source: Docling documentation, existing DoclingProcessor
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat

class DoclingOCRProcessor:
    """Docling processor configured for OCR fallback.

    LOCR-11: Fallback to Docling OCR when GPU service unavailable
    """

    def __init__(self):
        self._ocr_converter = self._create_ocr_converter()

    def _create_ocr_converter(self) -> DocumentConverter:
        """Create converter with OCR enabled."""
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        # Force OCR even if text layer exists (for consistency)
        # pipeline_options.ocr_options.force_full_page_ocr = True

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                ),
            }
        )

    def process_with_ocr(self, pdf_bytes: bytes, filename: str) -> DocumentContent:
        """Process PDF with Docling's built-in OCR."""
        # Implementation similar to existing DoclingProcessor
        # but with do_ocr=True
        ...
```

### Pattern 4: OCR Mode API Parameter

**What:** Allow API callers to control OCR behavior
**When to use:** Document upload endpoint
**Example:**
```python
# Source: DUAL-02 requirement (Phase 15 integration)
from typing import Literal

OCRMode = Literal["auto", "force", "skip"]

async def upload_document(
    file: UploadFile,
    ocr: OCRMode = "auto",  # DUAL-02: OCR mode selection
) -> Document:
    """Upload document with OCR mode control.

    Args:
        file: Uploaded file
        ocr: OCR mode:
            - "auto": Detect scanned pages, OCR only if needed (default)
            - "force": Always run OCR (for poor-quality native PDFs)
            - "skip": Never run OCR (fastest, native PDFs only)
    """
    ...
```

### Anti-Patterns to Avoid
- **Always running OCR:** Wastes GPU resources on native PDFs with perfect text layers
- **Single threshold for all documents:** Different document types may need tuned thresholds
- **Ignoring mixed documents:** Some PDFs have both native and scanned pages
- **No circuit breaker:** GPU service unavailability causes cascading timeouts
- **Synchronous health checks:** Block request processing; use async with caching

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom parser | pypdfium2 via Docling | Battle-tested, handles edge cases |
| Circuit breaker state | Custom state machine | aiobreaker | Handles timing, half-open state |
| Retry with backoff | Manual retry loops | tenacity | Configurable, composable with circuit breaker |
| OCR quality fallback | Character confidence scoring | Docling's multi-engine support | Handles OCR engine failures |
| Image to text | Custom CNN/transformer | LightOnOCR or Docling OCR engines | State-of-the-art, maintained |

**Key insight:** The combination of pypdfium2 (detection) + aiobreaker (circuit breaker) + tenacity (retry) + existing components (LightOnOCRClient, DoclingProcessor) provides a complete solution without custom implementations.

## Common Pitfalls

### Pitfall 1: False Positives on OCR'd PDFs
**What goes wrong:** PDFs that have been OCR'd already are re-OCR'd unnecessarily
**Why it happens:** They have a text layer from previous OCR, but may also have image content
**How to avoid:** Check for "GlyphlessFont" in font list (indicates Tesseract OCR); consider the text quality not just presence
**Warning signs:** Double-OCR artifacts, processing time spikes on already-processed documents

### Pitfall 2: Circuit Breaker Thrashing
**What goes wrong:** Circuit breaker opens/closes rapidly, causing inconsistent behavior
**Why it happens:** reset_timeout too short, or fail_max too low
**How to avoid:** Use conservative settings (fail_max=3, reset_timeout=60s); implement half-open state testing
**Warning signs:** Frequent circuit state changes in logs, inconsistent fallback behavior

### Pitfall 3: Memory Exhaustion on Large Scanned PDFs
**What goes wrong:** OOM when converting large scanned PDFs to images for GPU OCR
**Why it happens:** Loading entire PDF into memory, then converting all pages to images
**How to avoid:** Process pages one at a time; use streaming where possible; set max page limits
**Warning signs:** Memory usage spikes, container restarts, "Killed" errors

### Pitfall 4: Silent Fallback Degradation
**What goes wrong:** Users don't know they're getting Docling OCR instead of GPU OCR
**Why it happens:** Fallback happens silently without logging or metadata
**How to avoid:** Log fallback events; set ocr_method metadata on Document model; expose in API response
**Warning signs:** Quality inconsistencies without corresponding logs

### Pitfall 5: Blocking Health Checks
**What goes wrong:** OCR routing blocks on GPU service health check
**Why it happens:** Synchronous health check before every request
**How to avoid:** Use cached health status with background refresh; rely on circuit breaker state instead
**Warning signs:** High latency on first request, timeouts during GPU cold starts

## Code Examples

Verified patterns from official sources and existing codebase:

### pypdfium2 Text Extraction
```python
# Source: pypdfium2 documentation, verified with Docling dependency
import pypdfium2 as pdfium

def get_page_text_length(pdf_bytes: bytes, page_index: int) -> int:
    """Get character count from a PDF page's text layer."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    page = pdf[page_index]
    textpage = page.get_textpage()
    text = textpage.get_text_bounded()
    return len(text.strip()) if text else 0
```

### aiobreaker Decorator Usage
```python
# Source: aiobreaker documentation
from datetime import timedelta
from aiobreaker import CircuitBreaker, CircuitBreakerError

breaker = CircuitBreaker(fail_max=3, reset_timeout=timedelta(seconds=60))

@breaker
async def call_gpu_service(image_bytes: bytes) -> str:
    """Protected GPU service call."""
    # If breaker is open, raises CircuitBreakerError immediately
    return await gpu_client.extract_text(image_bytes)

# Usage with fallback
try:
    result = await call_gpu_service(image_bytes)
except CircuitBreakerError:
    # GPU service unhealthy, use fallback
    result = docling_ocr_fallback(image_bytes)
```

### Combining Circuit Breaker with Tenacity
```python
# Source: tenacity + aiobreaker integration pattern
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from aiobreaker import CircuitBreaker, CircuitBreakerError

breaker = CircuitBreaker(fail_max=3, reset_timeout=timedelta(seconds=60))

class GPUServiceTransientError(Exception):
    """Retryable GPU service error."""
    pass

@retry(
    retry=retry_if_exception_type(GPUServiceTransientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
)
@breaker
async def resilient_gpu_call(image_bytes: bytes) -> str:
    """GPU call with retry inside circuit breaker."""
    try:
        return await gpu_client.extract_text(image_bytes)
    except LightOnOCRError as e:
        if "503" in str(e) or "timeout" in str(e).lower():
            raise GPUServiceTransientError(str(e)) from e
        raise  # Fatal errors pass through
```

### PDF Page to Image Conversion
```python
# Source: pypdfium2 documentation
import pypdfium2 as pdfium
from PIL import Image
import io

def page_to_png_bytes(pdf_bytes: bytes, page_index: int, dpi: int = 150) -> bytes:
    """Convert PDF page to PNG image bytes for OCR."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    page = pdf[page_index]

    # Render at specified DPI
    scale = dpi / 72  # PDF default is 72 DPI
    bitmap = page.render(scale=scale)
    pil_image = bitmap.to_pil()

    # Convert to PNG bytes
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return buffer.getvalue()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Always OCR all PDFs | Intelligent detection + routing | 2024-2025 | 5-10x cost reduction for native PDFs |
| Tesseract-only OCR | VLM-based OCR (LightOnOCR) | 2025 | Better accuracy on complex layouts |
| Simple retry loops | Circuit breaker + retry | 2020s | Prevents cascading failures |
| Synchronous PDF processing | Async with page streaming | 2024+ | Better memory efficiency |

**Deprecated/outdated:**
- PyPDF2: Superseded by pypdf (same API, maintained)
- Synchronous circuit breakers: Use aiobreaker for asyncio applications
- Fixed OCR thresholds: Adaptive thresholds based on document type preferred

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal MIN_CHARS_THRESHOLD Value**
   - What we know: 50 chars is a reasonable starting point; empty or near-empty indicates scanned
   - What's unclear: Optimal value may vary by document type (loan docs vs receipts vs contracts)
   - Recommendation: Start with 50, make configurable, tune based on production data

2. **Mixed Document Handling Strategy**
   - What we know: Some PDFs have native pages and scanned pages
   - What's unclear: Whether to OCR only scanned pages or entire document for consistency
   - Recommendation: OCR scanned pages individually, combine with native page text

3. **Circuit Breaker State Persistence**
   - What we know: aiobreaker supports Redis backing for distributed state
   - What's unclear: Whether single-instance state is sufficient for this application
   - Recommendation: Start with in-memory state (single Cloud Run instance); add Redis if scaling

## Sources

### Primary (HIGH confidence)
- [pypdfium2 GitHub](https://github.com/pypdfium2-team/pypdfium2) - PDF text extraction API
- [aiobreaker Documentation](https://aiobreaker.netlify.app/) - Circuit breaker for asyncio
- [PyMuPDF Discussion #1653](https://github.com/pymupdf/PyMuPDF/discussions/1653) - Scanned PDF detection patterns
- [pypdf Text Extraction Docs](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) - PDF types and detection
- [Docling PDF Backend](https://deepwiki.com/docling-project/docling/3.1-pdf-backend) - OCR configuration options

### Secondary (MEDIUM confidence)
- [Quantrium Medium Article](https://medium.com/quantrium-tech/identifying-text-based-and-image-based-pdfs-using-python-10dba29a02b4) - Text vs image PDF identification
- [Open Preservation Foundation](https://openpreservation.org/blogs/scanned-vs-native-pdfs-how-to-differentiate-them/) - Scanned vs native PDF differentiation
- [tenacity + circuit breaker integration](https://dev.to/akarshan/building-a-robust-redis-client-with-retry-logic-in-python-jeg) - Combining retry with circuit breaker

### Tertiary (LOW confidence)
- MIN_CHARS_THRESHOLD value (needs production validation)
- Optimal circuit breaker timing parameters (may need tuning)

## Metadata

**Confidence breakdown:**
- Scanned detection: HIGH - Multiple verified sources agree on text ratio approach
- Circuit breaker: HIGH - aiobreaker well-documented, active maintenance
- Docling fallback: HIGH - Existing DoclingProcessor with do_ocr option
- Threshold values: MEDIUM - Starting points provided, need production validation

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - stable patterns, pypdfium2 API stable)

## Phase 14 Requirements Mapping

| Requirement | Research Finding | Confidence |
|-------------|------------------|------------|
| LOCR-05: Scanned document detection | pypdfium2 text ratio detection pattern verified | HIGH |
| LOCR-11: Docling OCR fallback | DoclingProcessor.do_ocr=True with circuit breaker | HIGH |
