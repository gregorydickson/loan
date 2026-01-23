"""Document-related Pydantic models for source attribution and tracking.

This module provides models for:
- SourceReference: Tracking where extracted data came from (document, page, snippet)
- DocumentMetadata: Document tracking for ingestion pipeline
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SourceReference(BaseModel):
    """Attribution to source document for traceability.

    Every extracted data point should have a SourceReference indicating
    which document, page, and text snippet it was extracted from.
    """

    document_id: UUID = Field(..., description="UUID identifying the source document")
    document_name: str = Field(..., description="Human-readable filename")
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    section: str | None = Field(
        default=None,
        description="Section name, e.g., 'Income Verification', 'Personal Information'",
    )
    snippet: str = Field(
        ...,
        max_length=500,
        description="Text snippet that was extracted from",
    )

    model_config = ConfigDict(from_attributes=True)


class DocumentMetadata(BaseModel):
    """Metadata for tracking documents through the ingestion pipeline.

    Used to track document status from upload through processing completion.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique document identifier")
    filename: str = Field(..., min_length=1, description="Original filename")
    file_hash: str = Field(..., description="SHA-256 hash for deduplication")
    file_type: Literal["pdf", "docx", "png", "jpg", "jpeg"] = Field(
        ..., description="File type for processing dispatch"
    )
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    storage_uri: str | None = Field(
        default=None, description="GCS URI, None until uploaded"
    )
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        default="pending", description="Processing status"
    )
    error_message: str | None = Field(
        default=None, description="Error message if status is 'failed'"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when document was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when document was last updated",
    )

    model_config = ConfigDict(from_attributes=True)
