"""Tests for document chunking."""

import pytest

from src.extraction.chunker import DocumentChunker, TextChunk


@pytest.fixture
def chunker() -> DocumentChunker:
    """Create chunker with small sizes for testing."""
    return DocumentChunker(max_chars=100, overlap_chars=20)


@pytest.fixture
def default_chunker() -> DocumentChunker:
    """Create chunker with default production values."""
    return DocumentChunker()


class TestDocumentChunker:
    """Test suite for DocumentChunker."""

    def test_small_text_single_chunk(self, chunker: DocumentChunker):
        """Text smaller than max_chars should return single chunk."""
        text = "Short document text."
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 1

    def test_exact_max_size_single_chunk(self, chunker: DocumentChunker):
        """Text exactly at max_chars should return single chunk."""
        text = "x" * 100  # Exactly max_chars
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].total_chunks == 1

    def test_large_text_multiple_chunks(self, chunker: DocumentChunker):
        """Long text should split into multiple chunks."""
        text = "a" * 250  # More than 2x max_chars
        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        # All chunks should have correct total_chunks
        for chunk in chunks:
            assert chunk.total_chunks == len(chunks)

    def test_chunks_have_overlap(self, chunker: DocumentChunker):
        """Adjacent chunks should share text at boundary."""
        # Create text without paragraph breaks to force char-based splitting
        text = "a" * 200
        chunks = chunker.chunk(text)

        assert len(chunks) >= 2

        # Get the end of first chunk and start of second
        chunk1_end = chunks[0].end_char
        chunk2_start = chunks[1].start_char

        # Second chunk should start before first chunk ends (overlap)
        assert chunk2_start < chunk1_end
        # Overlap should be approximately overlap_chars
        overlap = chunk1_end - chunk2_start
        assert overlap == chunker.overlap_chars

    def test_paragraph_boundary_preferred(self, chunker: DocumentChunker):
        """Split should happen at paragraph boundary when in search zone.

        With max_chars=100, last 20% = positions 80-100.
        Place paragraph break at position 85 to be in search zone.
        """
        # Text with paragraph at position 85 (in last 20% search zone)
        text = "a" * 85 + "\n\n" + "b" * 60  # 147 chars total
        chunks = chunker.chunk(text)

        # Should split at paragraph break (position 87 including \n\n)
        assert len(chunks) >= 2
        # First chunk should end after paragraph break
        assert chunks[0].text.endswith("\n\n")
        assert chunks[0].end_char == 87

    def test_no_paragraph_splits_at_max(self):
        """Without paragraph breaks, should split at max_chars."""
        chunker = DocumentChunker(max_chars=50, overlap_chars=10)
        text = "a" * 120  # No paragraph breaks
        chunks = chunker.chunk(text)

        assert len(chunks) >= 2
        # First chunk should be exactly max_chars
        assert len(chunks[0].text) == 50

    def test_chunk_metadata_accurate(self, chunker: DocumentChunker):
        """start_char, end_char, and indexes should be correct."""
        text = "0123456789" * 25  # 250 chars
        chunks = chunker.chunk(text)

        for i, chunk in enumerate(chunks):
            # chunk_index should match position
            assert chunk.chunk_index == i

            # text should match the slice
            extracted = text[chunk.start_char : chunk.end_char]
            assert chunk.text == extracted

            # end_char should be start + len(text)
            assert chunk.end_char == chunk.start_char + len(chunk.text)

    def test_empty_text_single_empty_chunk(self, chunker: DocumentChunker):
        """Empty text should return single empty chunk."""
        chunks = chunker.chunk("")

        assert len(chunks) == 1
        assert chunks[0].text == ""
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == 0

    def test_chunk_indexes_sequential(self, chunker: DocumentChunker):
        """Chunk indexes should be sequential starting from 0."""
        text = "content " * 50
        chunks = chunker.chunk(text)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_default_values(self, default_chunker: DocumentChunker):
        """Default chunker should use ~4000 token limits."""
        assert default_chunker.max_chars == 16000
        assert default_chunker.overlap_chars == 800

    def test_overlap_maintains_context(self):
        """Overlap should include shared text for context."""
        chunker = DocumentChunker(max_chars=50, overlap_chars=15)
        text = "a" * 100

        chunks = chunker.chunk(text)

        # Get overlapping portion between chunk 0 and chunk 1
        overlap_start = chunks[1].start_char
        overlap_end = chunks[0].end_char

        # The overlap text should appear in both chunks
        overlap_text = text[overlap_start:overlap_end]
        assert overlap_text in chunks[0].text
        assert overlap_text in chunks[1].text

    def test_paragraph_in_search_zone_used(self):
        """Paragraph break in last 20% of chunk should be used as boundary."""
        # max_chars=100, last 20% = chars 80-100
        chunker = DocumentChunker(max_chars=100, overlap_chars=20)

        # Paragraph at position 85
        text = "a" * 85 + "\n\n" + "b" * 50
        chunks = chunker.chunk(text)

        # First chunk should end at paragraph (85 + 2 for \n\n)
        assert chunks[0].end_char == 87
        assert chunks[0].text.endswith("\n\n")

    def test_paragraph_before_search_zone_ignored(self):
        """Paragraph break before last 20% should be ignored."""
        # max_chars=100, last 20% = chars 80-100
        chunker = DocumentChunker(max_chars=100, overlap_chars=20)

        # Paragraph at position 50 (before search zone)
        text = "a" * 50 + "\n\n" + "b" * 100
        chunks = chunker.chunk(text)

        # First chunk should end at max_chars (100), not at paragraph
        assert chunks[0].end_char == 100

    def test_covers_entire_document(self, chunker: DocumentChunker):
        """Chunks should cover the entire document with no gaps."""
        text = "test content " * 30
        chunks = chunker.chunk(text)

        # First chunk starts at 0
        assert chunks[0].start_char == 0

        # Last chunk ends at len(text)
        assert chunks[-1].end_char == len(text)

        # Verify all content is covered (accounting for overlap)
        covered = set()
        for chunk in chunks:
            for i in range(chunk.start_char, chunk.end_char):
                covered.add(i)

        assert len(covered) == len(text)

    def test_textchunk_dataclass_fields(self):
        """TextChunk should have all required fields."""
        chunk = TextChunk(
            text="sample",
            start_char=0,
            end_char=6,
            chunk_index=0,
            total_chunks=1,
        )

        assert chunk.text == "sample"
        assert chunk.start_char == 0
        assert chunk.end_char == 6
        assert chunk.chunk_index == 0
        assert chunk.total_chunks == 1
