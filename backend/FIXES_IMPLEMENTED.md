# Document Upload Status Issue - Fixes Implemented

## Problem
Documents were showing status "failed" in the document list even though the upload API returned 201 (Created).

## Root Cause Analysis
1. **Transaction rollback**: When processing failed after document creation, the entire transaction was rolled back, preventing document records from persisting
2. **Silent failures**: Errors during processing lacked detailed logging, making debugging difficult
3. **All-or-nothing persistence**: If any borrower failed to persist, the entire document was marked as failed

## Fixes Implemented

### Fix 1: Prevent Full Transaction Rollback
**Location**: `backend/src/ingestion/document_service.py:254-265`

**What changed**:
- Added `await self.repository.session.commit()` after GCS upload completes
- Document record is now committed BEFORE processing starts
- If processing fails, the document persists with FAILED/PENDING status instead of disappearing

**Impact**:
- Documents will always appear in the database after upload
- Status can be tracked even if processing fails
- Users can see what documents exist and their current state

```python
# FIX 1: Commit document creation before processing
# This prevents full transaction rollback if processing fails
await self.repository.session.commit()
logger.info(
    "Document record committed before processing",
    extra={
        "document_id": str(document_id),
        "filename": filename,
        "file_size_bytes": len(content),
        "extraction_method": extraction_method,
    }
)
```

### Fix 2: Add Detailed Error Logging
**Locations**: Multiple places throughout `document_service.py`

**What changed**:
- Added structured logging with `extra` fields at all failure points
- Captures: document_id, filename, error_type, error_detail, extraction_method, ocr_mode
- Added `exc_info=e` for full stack traces
- Logs at appropriate levels (INFO for progress, ERROR for failures, WARNING for partial issues)

**Impact**:
- Detailed error context for debugging
- Can trace exact failure point and reason
- Structured logs can be parsed by log aggregators

**Key logging points added**:
1. GCS upload failures (line 268-278)
2. Cloud Tasks queueing failures (line 304-318)
3. OCR processing start/completion (lines 350-378, 381-389)
4. Document processing success (lines 391-400)
5. Borrower persistence failures (lines 448-460)
6. Extraction/persistence ValueErrors (lines 499-510)
7. General extraction failures (line 529-541)
8. DocumentProcessingError failures (lines 550-565)

### Fix 3: Capture Partial Failures
**Location**: `backend/src/ingestion/document_service.py:434-479`

**What changed**:
- Track `persisted_count` to count successful borrower saves
- Collect persistence errors but continue processing remaining borrowers
- If any borrower fails, mark document as COMPLETED with warning in `error_message` field
- Store detailed error summary: "Partial success: X/Y borrowers persisted. Failures: ..."

**Impact**:
- Documents can succeed even if some borrowers fail to persist
- Users see partial data instead of complete failure
- Error message shows exactly what succeeded and what failed
- Better user experience - partial data is better than no data

```python
# FIX 3: Allow partial success - mark as completed with warning
if persistence_errors:
    error_summary = f"Partial success: {persisted_count}/{len(extraction_result.borrowers)} borrowers persisted. Failures: {'; '.join(persistence_errors)}"
    logger.warning(
        "Document completed with partial borrower persistence",
        extra={
            "document_id": str(document_id),
            "persisted_count": persisted_count,
            "total_count": len(extraction_result.borrowers),
            "failed_count": len(persistence_errors),
        }
    )
    # Update document with warning message but keep COMPLETED status
    await self.repository.update_status(
        document_id,
        DocumentStatus.COMPLETED,
        error_message=error_summary,
    )
```

## Testing Recommendations

### 1. Test with Various Documents
- **Valid PDF**: Should complete successfully
- **Scanned PDF** (if OCR disabled): May fail at Docling stage - verify document persists with FAILED status
- **Document with invalid borrower data**: Should complete with partial success message

### 2. Check Database After Upload
```sql
-- Check document exists with status
SELECT id, filename, status, error_message, page_count, created_at
FROM documents
ORDER BY created_at DESC
LIMIT 5;

-- Check if borrowers were persisted
SELECT b.name, b.confidence_score, d.filename
FROM borrowers b
JOIN source_references sr ON sr.borrower_id = b.id
JOIN documents d ON d.id = sr.document_id
ORDER BY b.created_at DESC;
```

### 3. Monitor Logs
```bash
# Tail application logs during upload
tail -f /private/tmp/fastapi-test.log

# Look for these log messages:
# - "Document record committed before processing" (Fix 1)
# - Detailed error logs with extra fields (Fix 2)
# - "Document completed with partial borrower persistence" (Fix 3)
```

### 4. Test API Response
```bash
# Upload a document
curl -X POST http://localhost:8001/api/documents/ \
  -F "file=@test.pdf" \
  -F "method=docling" \
  -F "ocr=auto"

# Should return 201 with document details
# Then check status endpoint
curl http://localhost:8001/api/documents/{document_id}/status
```

## Expected Behavior After Fixes

### Scenario 1: Successful Upload
- API returns 201
- Document appears in list with status="completed"
- All borrowers persisted
- No error_message

### Scenario 2: Processing Failure (e.g., Docling fails)
- API returns 201 (Fix 1 ensures document is committed)
- Document appears in list with status="failed"
- error_message contains detailed error info (Fix 2)
- Can retry or diagnose issue

### Scenario 3: Partial Borrower Persistence Failure
- API returns 201
- Document appears in list with status="completed" (Fix 3)
- error_message shows "Partial success: 2/3 borrowers persisted. Failures: ..." (Fix 3)
- Successfully persisted borrowers are available in database
- Detailed logs show which borrowers failed and why (Fix 2)

## Migration Notes

- **No database migration needed**: All changes are in application code
- **Backward compatible**: Existing documents unaffected
- **Log format change**: If using log aggregators, update parsers to handle new structured fields

## Monitoring

Add alerts for:
1. High rate of documents with status="failed"
2. High rate of partial success messages in error_message field
3. Specific error types appearing frequently in logs (e.g., "SSN normalization", "constraint violation")
