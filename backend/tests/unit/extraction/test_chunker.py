"""Unit tests for DocumentChunker.

Tests document chunking for LLM processing:
- Single chunk for short documents
- Multiple chunks for long documents
- Paragraph-aware boundary splitting
- Overlap calculation between chunks
- Position metadata (start_char, end_char)
- Edge cases and boundary conditions
"""

import pytest

from src.extraction.chunker import DocumentChunker, TextChunk


class TestSingleChunkDocuments:
    """Tests for documents that fit in a single chunk."""

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create chunker with default settings."""
        return DocumentChunker()

    def test_empty_text_single_chunk(self, chunker):
        """Empty text returns single chunk."""
        chunks = chunker.chunk("")
        assert len(chunks) == 1
        assert chunks[0].text == ""
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == 0
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 1

    def test_short_text_single_chunk(self, chunker):
        """Short text (< max_chars) returns single chunk."""
        text = "This is a short document with borrower information."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 1

    def test_exactly_max_chars_single_chunk(self, chunker):
        """Text exactly at max_chars returns single chunk."""
        text = "A" * 16000  # Default max_chars
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == 16000

    def test_one_char_under_max_single_chunk(self, chunker):
        """Text one char under max_chars returns single chunk."""
        text = "A" * 15999
        chunks = chunker.chunk(text)
        assert len(chunks) == 1


class TestMultipleChunks:
    """Tests for documents split into multiple chunks."""

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create chunker with default settings."""
        return DocumentChunker()

    def test_text_over_max_creates_chunks(self, chunker):
        """Text over max_chars creates multiple chunks."""
        text = "A" * 20000  # Over 16000 default
        chunks = chunker.chunk(text)
        assert len(chunks) > 1

    def test_chunk_indices_sequential(self, chunker):
        """Chunk indices are sequential starting from 0."""
        text = "A" * 40000
        chunks = chunker.chunk(text)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_total_chunks_same_for_all(self, chunker):
        """All chunks have same total_chunks value."""
        text = "A" * 40000
        chunks = chunker.chunk(text)
        total = len(chunks)
        for chunk in chunks:
            assert chunk.total_chunks == total

    def test_last_chunk_reaches_end(self, chunker):
        """Last chunk end_char equals text length."""
        text = "A" * 40000
        chunks = chunker.chunk(text)
        assert chunks[-1].end_char == len(text)

    def test_first_chunk_starts_at_zero(self, chunker):
        """First chunk starts at position 0."""
        text = "A" * 40000
        chunks = chunker.chunk(text)
        assert chunks[0].start_char == 0


class TestChunkOverlap:
    """Tests for overlap between consecutive chunks."""

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create chunker with default settings."""
        return DocumentChunker()

    def test_consecutive_chunks_overlap(self, chunker):
        """Consecutive chunks have overlap region."""
        text = "A" * 40000
        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            # Second chunk should start before first chunk ends
            assert chunks[1].start_char < chunks[0].end_char

    def test_overlap_approximately_correct(self, chunker):
        """Overlap is approximately overlap_chars (800 default)."""
        text = "A" * 40000
        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            overlap = chunks[0].end_char - chunks[1].start_char
            # Should be close to 800 (may vary due to paragraph breaks)
            assert 0 <= overlap <= 1000  # Allow some variance

    def test_custom_overlap_respected(self):
        """Custom overlap_chars is respected."""
        chunker = DocumentChunker(max_chars=1000, overlap_chars=100)
        text = "A" * 2500
        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            overlap = chunks[0].end_char - chunks[1].start_char
            assert 0 <= overlap <= 200  # Allow variance


class TestParagraphAwareSplitting:
    """Tests for paragraph boundary detection."""

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create chunker with small max_chars for testing."""
        return DocumentChunker(max_chars=100, overlap_chars=20)

    def test_splits_at_paragraph_boundary(self, chunker):
        """Prefers splitting at paragraph breaks (\n\n)."""
        text = "A" * 70 + "\n\n" + "B" * 70
        chunks = chunker.chunk(text)
        # Should split at paragraph break if within last 20% of chunk
        if len(chunks) > 1:
            # First chunk should end at or near paragraph break
            assert "\n\n" in text[chunks[0].start_char : chunks[0].end_char] or chunks[
                0
            ].end_char >= 70

    def test_no_paragraph_splits_at_max(self, chunker):
        """Without paragraph breaks, splits at max_chars."""
        text = "A" * 200  # No paragraph breaks
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        # First chunk should be approximately max_chars
        assert 80 <= len(chunks[0].text) <= 120  # Allow for overlap adjustment

    def test_paragraph_includes_newlines(self, chunker):
        """Paragraph break split includes the newlines."""
        # Put paragraph break in last 20% of chunk (80-100 range)
        text = "A" * 85 + "\n\n" + "B" * 100
        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            # First chunk should end at or after paragraph break
            # Implementation does: end = para_break + 2 (includes "\n\n")
            first_ends_with_newline = chunks[0].text.endswith("\n")
            # At minimum, first chunk should include the paragraph break
            assert first_ends_with_newline


class TestPositionMetadata:
    """Tests for chunk position metadata accuracy."""

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create chunker with default settings."""
        return DocumentChunker()

    def test_start_end_chars_match_text(self, chunker):
        """start_char and end_char match actual text positions."""
        text = "ABCDEFGHIJ" * 4000  # 40000 chars
        chunks = chunker.chunk(text)
        for chunk in chunks:
            # Extract text using positions should match chunk text
            extracted = text[chunk.start_char : chunk.end_char]
            assert extracted == chunk.text

    def test_chunks_cover_entire_text(self, chunker):
        """All chunks together cover entire text (accounting for overlap)."""
        text = "A" * 40000
        chunks = chunker.chunk(text)
        # First chunk should start at 0
        assert chunks[0].start_char == 0
        # Last chunk should end at text length
        assert chunks[-1].end_char == len(text)

    def test_no_gaps_between_chunks(self, chunker):
        """No gaps in coverage between chunks (overlap ensures this)."""
        text = "A" * 40000
        chunks = chunker.chunk(text)
        for i in range(len(chunks) - 1):
            # Next chunk should start at or before current chunk ends
            assert chunks[i + 1].start_char <= chunks[i].end_char


class TestCustomConfiguration:
    """Tests for custom max_chars and overlap_chars settings."""

    def test_custom_max_chars_respected(self):
        """Custom max_chars is respected."""
        chunker = DocumentChunker(max_chars=1000, overlap_chars=100)
        text = "A" * 500
        chunks = chunker.chunk(text)
        assert len(chunks) == 1  # Should fit in single chunk

    def test_small_max_chars_creates_many_chunks(self):
        """Small max_chars creates many chunks."""
        chunker = DocumentChunker(max_chars=100, overlap_chars=10)
        text = "A" * 1000
        chunks = chunker.chunk(text)
        assert len(chunks) >= 5  # Should create several chunks

    def test_large_max_chars_creates_few_chunks(self):
        """Large max_chars creates fewer chunks."""
        chunker = DocumentChunker(max_chars=50000, overlap_chars=1000)
        text = "A" * 40000
        chunks = chunker.chunk(text)
        assert len(chunks) == 1  # Should fit in single chunk

    def test_zero_overlap_no_shared_content(self):
        """Zero overlap means no shared content between chunks."""
        chunker = DocumentChunker(max_chars=1000, overlap_chars=0)
        text = "A" * 3000
        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            # Next chunk should start exactly where previous ended
            assert chunks[1].start_char == chunks[0].end_char

    def test_large_overlap_heavy_duplication(self):
        """Large overlap creates heavy duplication."""
        chunker = DocumentChunker(max_chars=1000, overlap_chars=500)
        text = "A" * 3000
        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            overlap = chunks[0].end_char - chunks[1].start_char
            assert overlap >= 400  # Should be close to 500


class TestTextChunkDataclass:
    """Tests for TextChunk dataclass structure."""

    def test_chunk_has_all_fields(self):
        """TextChunk contains all required fields."""
        chunk = TextChunk(
            text="Sample text",
            start_char=0,
            end_char=11,
            chunk_index=0,
            total_chunks=1,
        )
        assert chunk.text == "Sample text"
        assert chunk.start_char == 0
        assert chunk.end_char == 11
        assert chunk.chunk_index == 0
        assert chunk.total_chunks == 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create chunker with default settings."""
        return DocumentChunker()

    def test_single_character_text(self, chunker):
        """Single character returns single chunk."""
        chunks = chunker.chunk("A")
        assert len(chunks) == 1
        assert chunks[0].text == "A"

    def test_only_newlines(self, chunker):
        """Text with only newlines is handled."""
        text = "\n\n\n\n\n"
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_many_paragraph_breaks(self, chunker):
        """Text with many paragraph breaks is handled."""
        text = ("Short para\n\n" * 2000)  # Many small paragraphs
        chunks = chunker.chunk(text)
        assert len(chunks) > 1  # Should split into multiple chunks

    def test_no_newlines_long_text(self, chunker):
        """Very long text with no newlines is handled."""
        text = "A" * 100000  # 100k chars, no newlines
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        # Verify all chunks together cover entire text
        assert chunks[0].start_char == 0
        assert chunks[-1].end_char == len(text)

    def test_unicode_text_positions_correct(self, chunker):
        """Unicode text positions are correct."""
        text = "José García " * 2000  # Unicode characters
        chunks = chunker.chunk(text)
        for chunk in chunks:
            # Extract using positions should match chunk text
            extracted = text[chunk.start_char : chunk.end_char]
            assert extracted == chunk.text

    def test_mixed_newline_types(self, chunker):
        """Mixed newline types (\n\n, \n) are handled."""
        text = "Para 1\n\nPara 2\nLine in para 2\n\nPara 3" * 1000
        chunks = chunker.chunk(text)
        # Should split preferentially at \n\n boundaries
        assert len(chunks) >= 1

    def test_overlap_larger_than_max(self):
        """Overlap larger than max_chars is handled (edge case)."""
        # This is a configuration error but should not crash
        chunker = DocumentChunker(max_chars=100, overlap_chars=200)
        text = "A" * 500
        chunks = chunker.chunk(text)
        # Should still create chunks without infinite loop
        assert len(chunks) >= 1
        assert chunks[0].start_char == 0
        assert chunks[-1].end_char == len(text)
