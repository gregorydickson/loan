"""Database resilience and transaction safety tests.

Tests transaction rollback, concurrent updates, constraint violations,
and data consistency under adverse conditions.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.storage.database import get_db_session
from src.storage.models import (
    AccountNumber,
    Borrower,
    Document,
    DocumentStatus,
    IncomeRecord,
    SourceReference,
)
from src.storage.repositories import BorrowerRepository, DocumentRepository


class TestTransactionRollback:
    """Tests for transaction rollback scenarios."""

    @pytest.mark.asyncio
    async def test_rollback_on_constraint_violation(self, db_session):
        """Transaction rolls back on constraint violation without partial commits."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        # Create initial document
        doc1 = Document(
            id=uuid4(),
            filename="doc1.pdf",
            file_hash="hash1",
            gcs_path="gs://bucket/doc1.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc1)
        await db_session.commit()

        # Create borrower with SSN
        borrower1 = Borrower(
            id=uuid4(),
            name="John Doe",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
        )
        await borrower_repo.create(
            borrower1,
            income_records=[],
            account_numbers=[],
            source_references=[
                SourceReference(
                    id=uuid4(),
                    document_id=doc1.id,
                    page_number=1,
                    snippet="John Doe",
                )
            ],
        )
        await db_session.commit()

        # Try to create duplicate SSN (should fail)
        borrower2 = Borrower(
            id=uuid4(),
            name="Jane Doe",
            ssn="123-45-6789",  # Duplicate SSN
            confidence_score=Decimal("0.8"),
        )

        with pytest.raises(IntegrityError):
            await borrower_repo.create(
                borrower2,
                income_records=[],
                account_numbers=[],
                source_references=[
                    SourceReference(
                        id=uuid4(),
                        document_id=doc1.id,
                        page_number=2,
                        snippet="Jane Doe",
                    )
                ],
            )
            await db_session.commit()

        await db_session.rollback()

        # Verify first borrower still exists
        borrower_check = await borrower_repo.get_by_id(borrower1.id)
        assert borrower_check is not None
        assert borrower_check.name == "John Doe"

        # Verify second borrower was not created
        borrower2_check = await borrower_repo.get_by_id(borrower2.id)
        assert borrower2_check is None

    @pytest.mark.asyncio
    async def test_rollback_preserves_previous_data(self, db_session):
        """Rolling back transaction preserves data from previous commits."""
        doc_repo = DocumentRepository(db_session)

        # Create and commit document 1
        doc1 = Document(
            id=uuid4(),
            filename="doc1.pdf",
            file_hash="hash1",
            gcs_path="gs://bucket/doc1.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc1)
        await db_session.commit()

        doc1_id = doc1.id

        # Try to create invalid document 2 (will fail)
        doc2 = Document(
            id=uuid4(),
            filename="doc2.pdf",
            file_hash="hash1",  # Duplicate hash - should fail unique constraint
            gcs_path="gs://bucket/doc2.pdf",
            mime_type="application/pdf",
        )

        with pytest.raises(IntegrityError):
            await doc_repo.create(doc2)
            await db_session.commit()

        await db_session.rollback()

        # Document 1 should still exist
        doc1_check = await doc_repo.get_by_id(doc1_id)
        assert doc1_check is not None
        assert doc1_check.filename == "doc1.pdf"

    @pytest.mark.asyncio
    async def test_complex_transaction_rollback(self, db_session):
        """Complex multi-entity transaction rolls back completely on failure."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        # Create document
        doc = Document(
            id=uuid4(),
            filename="loan.pdf",
            file_hash="hash_complex",
            gcs_path="gs://bucket/loan.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)

        # Create borrower with multiple related entities
        borrower = Borrower(
            id=uuid4(),
            name="Complex Borrower",
            ssn="111-22-3333",
            confidence_score=Decimal("0.95"),
        )

        income_records = [
            IncomeRecord(
                id=uuid4(),
                year=2023,
                amount=Decimal("75000.00"),
                source="W2",
                employer="Company A",
            )
        ]

        account_numbers = [
            AccountNumber(id=uuid4(), account_number="ACC123456", account_type="checking")
        ]

        source_refs = [
            SourceReference(
                id=uuid4(),
                document_id=doc.id,
                page_number=1,
                snippet="Complex Borrower",
            )
        ]

        await borrower_repo.create(borrower, income_records, account_numbers, source_refs)

        # Now try to add a duplicate SSN borrower (should fail entire transaction)
        borrower2 = Borrower(
            id=uuid4(),
            name="Duplicate Person",
            ssn="111-22-3333",  # Same SSN
            confidence_score=Decimal("0.8"),
        )

        with pytest.raises(IntegrityError):
            await borrower_repo.create(
                borrower2,
                income_records=[],
                account_numbers=[],
                source_references=[
                    SourceReference(
                        id=uuid4(),
                        document_id=doc.id,
                        page_number=2,
                        snippet="Duplicate",
                    )
                ],
            )
            await db_session.commit()

        await db_session.rollback()

        # First borrower and all relations should still be in pending state (not committed)
        # Since we never committed, neither should exist
        borrower_check = await borrower_repo.get_by_id(borrower.id)
        assert borrower_check is None


class TestConcurrentUpdates:
    """Tests for concurrent update scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_document_status_updates(self, db_session):
        """Multiple concurrent status updates don't cause data loss."""
        doc_repo = DocumentRepository(db_session)

        # Create document
        doc = Document(
            id=uuid4(),
            filename="concurrent.pdf",
            file_hash="hash_concurrent",
            gcs_path="gs://bucket/concurrent.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)
        await db_session.commit()
        doc_id = doc.id

        # Simulate concurrent status updates
        async def update_status(status: DocumentStatus, delay_ms: int):
            # Get fresh session for each concurrent operation
            async for session in get_db_session():
                repo = DocumentRepository(session)
                await asyncio.sleep(delay_ms / 1000)
                await repo.update_status(doc_id, status)
                await session.commit()
                break

        # Run concurrent updates
        await asyncio.gather(
            update_status(DocumentStatus.PROCESSING, 0),
            update_status(DocumentStatus.COMPLETED, 10),
        )

        # Verify final state is deterministic (last write wins)
        doc_check = await doc_repo.get_by_id(doc_id)
        assert doc_check is not None
        # Status should be one of the two (depending on race)
        assert doc_check.status in [DocumentStatus.PROCESSING, DocumentStatus.COMPLETED]

    @pytest.mark.asyncio
    async def test_concurrent_borrower_reads_are_consistent(self, db_session):
        """Concurrent reads of same borrower return consistent data."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        # Create document and borrower
        doc = Document(
            id=uuid4(),
            filename="read_test.pdf",
            file_hash="hash_read",
            gcs_path="gs://bucket/read_test.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)

        borrower = Borrower(
            id=uuid4(),
            name="Read Test",
            ssn="222-33-4444",
            confidence_score=Decimal("0.9"),
        )
        await borrower_repo.create(
            borrower,
            income_records=[],
            account_numbers=[],
            source_references=[
                SourceReference(
                    id=uuid4(),
                    document_id=doc.id,
                    page_number=1,
                    snippet="Read Test",
                )
            ],
        )
        await db_session.commit()
        borrower_id = borrower.id

        # Concurrent reads
        async def read_borrower():
            async for session in get_db_session():
                repo = BorrowerRepository(session)
                result = await repo.get_by_id(borrower_id)
                await session.close()
                return result

        results = await asyncio.gather(*[read_borrower() for _ in range(5)])

        # All reads should return same data
        assert len(results) == 5
        assert all(r is not None for r in results)
        assert all(r.name == "Read Test" for r in results)
        assert all(r.ssn == "222-33-4444" for r in results)


class TestConstraintViolations:
    """Tests for database constraint violations."""

    @pytest.mark.asyncio
    async def test_duplicate_ssn_rejected(self, db_session):
        """Duplicate SSN values are rejected by unique constraint."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        doc = Document(
            id=uuid4(),
            filename="dup_ssn.pdf",
            file_hash="hash_dup_ssn",
            gcs_path="gs://bucket/dup_ssn.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)
        await db_session.commit()

        # Create first borrower
        borrower1 = Borrower(
            id=uuid4(),
            name="First Person",
            ssn="333-44-5555",
            confidence_score=Decimal("0.9"),
        )
        await borrower_repo.create(
            borrower1,
            income_records=[],
            account_numbers=[],
            source_references=[
                SourceReference(
                    id=uuid4(),
                    document_id=doc.id,
                    page_number=1,
                    snippet="First",
                )
            ],
        )
        await db_session.commit()

        # Try duplicate SSN
        borrower2 = Borrower(
            id=uuid4(),
            name="Second Person",
            ssn="333-44-5555",  # Duplicate
            confidence_score=Decimal("0.8"),
        )

        with pytest.raises(IntegrityError) as exc_info:
            await borrower_repo.create(
                borrower2,
                income_records=[],
                account_numbers=[],
                source_references=[
                    SourceReference(
                        id=uuid4(),
                        document_id=doc.id,
                        page_number=2,
                        snippet="Second",
                    )
                ],
            )
            await db_session.commit()

        assert "ssn" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_foreign_key_constraint_enforced(self, db_session):
        """Foreign key constraints prevent orphaned references."""
        # Try to create SourceReference with non-existent document_id
        source_ref = SourceReference(
            id=uuid4(),
            borrower_id=uuid4(),  # Non-existent borrower
            document_id=uuid4(),  # Non-existent document
            page_number=1,
            snippet="Orphan",
        )

        db_session.add(source_ref)

        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()

        # Should mention foreign key
        error_msg = str(exc_info.value).lower()
        assert "foreign key" in error_msg or "violates" in error_msg

    @pytest.mark.asyncio
    async def test_duplicate_document_hash_rejected(self, db_session):
        """Duplicate file hashes are rejected by unique constraint."""
        doc_repo = DocumentRepository(db_session)

        doc1 = Document(
            id=uuid4(),
            filename="original.pdf",
            file_hash="unique_hash_123",
            gcs_path="gs://bucket/original.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc1)
        await db_session.commit()

        # Try duplicate hash
        doc2 = Document(
            id=uuid4(),
            filename="duplicate.pdf",
            file_hash="unique_hash_123",  # Same hash
            gcs_path="gs://bucket/duplicate.pdf",
            mime_type="application/pdf",
        )

        with pytest.raises(IntegrityError) as exc_info:
            await doc_repo.create(doc2)
            await db_session.commit()

        assert "file_hash" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()


class TestDataConsistency:
    """Tests for data consistency across related entities."""

    @pytest.mark.asyncio
    async def test_cascade_delete_removes_all_relations(self, db_session):
        """Deleting borrower cascades to all related entities."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        # Create document
        doc = Document(
            id=uuid4(),
            filename="cascade.pdf",
            file_hash="hash_cascade",
            gcs_path="gs://bucket/cascade.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)

        # Create borrower with multiple relations
        borrower = Borrower(
            id=uuid4(),
            name="Cascade Test",
            ssn="444-55-6666",
            confidence_score=Decimal("0.9"),
        )

        income_records = [
            IncomeRecord(
                id=uuid4(),
                year=2023,
                amount=Decimal("80000.00"),
                source="W2",
            )
        ]

        account_numbers = [
            AccountNumber(id=uuid4(), account_number="CASCADE123", account_type="savings")
        ]

        source_refs = [
            SourceReference(
                id=uuid4(),
                document_id=doc.id,
                page_number=1,
                snippet="Cascade Test",
            )
        ]

        income_id = income_records[0].id
        account_id = account_numbers[0].id
        source_id = source_refs[0].id

        await borrower_repo.create(borrower, income_records, account_numbers, source_refs)
        await db_session.commit()

        borrower_id = borrower.id

        # Delete borrower
        deleted = await borrower_repo.delete(borrower_id)
        await db_session.commit()

        assert deleted is True

        # Verify borrower is gone
        assert await borrower_repo.get_by_id(borrower_id) is None

        # Verify cascaded deletions
        income_check = await db_session.get(IncomeRecord, income_id)
        assert income_check is None

        account_check = await db_session.get(AccountNumber, account_id)
        assert account_check is None

        source_check = await db_session.get(SourceReference, source_id)
        assert source_check is None

    @pytest.mark.asyncio
    async def test_document_delete_removes_borrowers(self, db_session):
        """Deleting document removes associated borrowers."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        # Create document
        doc = Document(
            id=uuid4(),
            filename="delete_doc.pdf",
            file_hash="hash_delete_doc",
            gcs_path="gs://bucket/delete_doc.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)

        # Create borrower linked to document
        borrower = Borrower(
            id=uuid4(),
            name="Will Be Deleted",
            ssn="555-66-7777",
            confidence_score=Decimal("0.9"),
        )
        await borrower_repo.create(
            borrower,
            income_records=[],
            account_numbers=[],
            source_references=[
                SourceReference(
                    id=uuid4(),
                    document_id=doc.id,
                    page_number=1,
                    snippet="Will Be Deleted",
                )
            ],
        )
        await db_session.commit()

        doc_id = doc.id
        borrower_id = borrower.id

        # Delete document (should cascade to borrower)
        deleted = await doc_repo.delete(doc_id)
        await db_session.commit()

        assert deleted is True

        # Verify document is gone
        assert await doc_repo.get_by_id(doc_id) is None

        # Verify borrower is gone (cascaded)
        assert await borrower_repo.get_by_id(borrower_id) is None

    @pytest.mark.asyncio
    async def test_income_records_stay_with_borrower(self, db_session):
        """Income records maintain association with borrower through updates."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        doc = Document(
            id=uuid4(),
            filename="income.pdf",
            file_hash="hash_income",
            gcs_path="gs://bucket/income.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)

        borrower = Borrower(
            id=uuid4(),
            name="Income Test",
            ssn="666-77-8888",
            confidence_score=Decimal("0.9"),
        )

        income_records = [
            IncomeRecord(
                id=uuid4(),
                year=2022,
                amount=Decimal("70000.00"),
                source="W2",
            ),
            IncomeRecord(
                id=uuid4(),
                year=2023,
                amount=Decimal("75000.00"),
                source="W2",
            ),
        ]

        await borrower_repo.create(
            borrower,
            income_records,
            account_numbers=[],
            source_references=[
                SourceReference(
                    id=uuid4(),
                    document_id=doc.id,
                    page_number=1,
                    snippet="Income Test",
                )
            ],
        )
        await db_session.commit()

        borrower_id = borrower.id

        # Retrieve borrower and verify income records
        borrower_check = await borrower_repo.get_by_id(borrower_id)
        assert borrower_check is not None
        assert len(borrower_check.income_records) == 2

        # Verify years are correct
        years = sorted([inc.year for inc in borrower_check.income_records])
        assert years == [2022, 2023]


class TestEdgeCaseHandling:
    """Tests for edge case database scenarios."""

    @pytest.mark.asyncio
    async def test_empty_list_relations_handled(self, db_session):
        """Creating borrower with empty relation lists works correctly."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        doc = Document(
            id=uuid4(),
            filename="empty.pdf",
            file_hash="hash_empty",
            gcs_path="gs://bucket/empty.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)

        borrower = Borrower(
            id=uuid4(),
            name="No Relations",
            ssn="777-88-9999",
            confidence_score=Decimal("0.9"),
        )

        # Empty lists for all relations
        await borrower_repo.create(
            borrower,
            income_records=[],
            account_numbers=[],
            source_references=[
                SourceReference(
                    id=uuid4(),
                    document_id=doc.id,
                    page_number=1,
                    snippet="No Relations",
                )
            ],
        )
        await db_session.commit()

        # Should succeed
        borrower_check = await borrower_repo.get_by_id(borrower.id)
        assert borrower_check is not None
        assert len(borrower_check.income_records) == 0
        assert len(borrower_check.account_numbers) == 0

    @pytest.mark.asyncio
    async def test_null_optional_fields_handled(self, db_session):
        """NULL values in optional fields are handled correctly."""
        doc_repo = DocumentRepository(db_session)

        doc = Document(
            id=uuid4(),
            filename="null_fields.pdf",
            file_hash="hash_null",
            gcs_path="gs://bucket/null_fields.pdf",
            mime_type="application/pdf",
            # error_message=None (default)
            # processed_at=None (default)
            # page_count=None (default)
        )
        await doc_repo.create(doc)
        await db_session.commit()

        doc_check = await doc_repo.get_by_id(doc.id)
        assert doc_check is not None
        assert doc_check.error_message is None
        assert doc_check.processed_at is None
        assert doc_check.page_count is None

    @pytest.mark.asyncio
    async def test_very_long_text_fields_handled(self, db_session):
        """Very long text fields are stored correctly."""
        doc_repo = DocumentRepository(db_session)

        long_error = "ERROR: " + "x" * 10000  # 10K character error

        doc = Document(
            id=uuid4(),
            filename="long_error.pdf",
            file_hash="hash_long_error",
            gcs_path="gs://bucket/long_error.pdf",
            mime_type="application/pdf",
            status=DocumentStatus.FAILED,
            error_message=long_error,
        )
        await doc_repo.create(doc)
        await db_session.commit()

        doc_check = await doc_repo.get_by_id(doc.id)
        assert doc_check is not None
        assert doc_check.error_message == long_error
        assert len(doc_check.error_message) > 10000
