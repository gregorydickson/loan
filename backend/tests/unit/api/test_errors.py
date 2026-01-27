"""Unit tests for API error classes."""

import pytest

from src.api.errors import EntityNotFoundError


class TestEntityNotFoundError:
    """Test EntityNotFoundError exception class."""

    def test_initialization_with_entity_type_and_id(self):
        """Test that EntityNotFoundError stores entity_type and entity_id."""
        error = EntityNotFoundError("Document", "abc123")

        assert error.entity_type == "Document"
        assert error.entity_id == "abc123"

    def test_error_message_format(self):
        """Test that error message is formatted correctly."""
        error = EntityNotFoundError("Borrower", "xyz789")

        expected_message = "Borrower not found: xyz789"
        assert str(error) == expected_message

    def test_error_message_with_uuid(self):
        """Test error message with UUID-style ID."""
        uuid_id = "550e8400-e29b-41d4-a716-446655440000"
        error = EntityNotFoundError("Document", uuid_id)

        expected_message = f"Document not found: {uuid_id}"
        assert str(error) == expected_message

    def test_exception_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught normally."""
        with pytest.raises(EntityNotFoundError) as exc_info:
            raise EntityNotFoundError("Task", "task-456")

        assert exc_info.value.entity_type == "Task"
        assert exc_info.value.entity_id == "task-456"

    def test_inherits_from_exception(self):
        """Test that EntityNotFoundError is a proper Exception."""
        error = EntityNotFoundError("Test", "123")

        assert isinstance(error, Exception)

    def test_different_entity_types(self):
        """Test error creation with various entity types."""
        test_cases = [
            ("Document", "doc-1"),
            ("Borrower", "borrower-2"),
            ("Task", "task-3"),
            ("User", "user-4"),
        ]

        for entity_type, entity_id in test_cases:
            error = EntityNotFoundError(entity_type, entity_id)
            assert error.entity_type == entity_type
            assert error.entity_id == entity_id
            assert f"{entity_type} not found: {entity_id}" == str(error)
