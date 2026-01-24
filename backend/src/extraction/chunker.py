"""Document chunking for LLM processing of large documents.

This module provides paragraph-aware chunking with overlap to:
- Keep documents within LLM token limits (~4000 tokens)
- Avoid splitting data entities across chunk boundaries
- Maintain context via overlapping text between chunks

EXTRACT-20: 4000 tokens max, 200 tokens overlap
16000 chars ~ 4000 tokens (at 4 chars/token average)
800 chars ~ 200 tokens overlap
"""

from dataclasses import dataclass


@dataclass
class TextChunk:
    """A chunk of document text with position metadata.

    Attributes:
        text: Chunk content
        start_char: Start position in original document
        end_char: End position in original document
        chunk_index: 0-based chunk index
        total_chunks: Total number of chunks in document
    """

    text: str
    start_char: int
    end_char: int
    chunk_index: int
    total_chunks: int


class DocumentChunker:
    """Splits documents into overlapping chunks for LLM processing.

    Uses character-based chunking with paragraph-aware boundaries.
    Attempts to split on paragraph breaks (\n\n) when possible to
    avoid cutting through data entities.

    Example:
        chunker = DocumentChunker(max_chars=16000, overlap_chars=800)
        chunks = chunker.chunk(long_document_text)
        for chunk in chunks:
            result = llm.extract(chunk.text)
    """

    def __init__(
        self,
        max_chars: int = 16000,  # ~4000 tokens at 4 chars/token
        overlap_chars: int = 800,  # ~200 tokens overlap
    ) -> None:
        """Initialize chunker with size and overlap parameters.

        Args:
            max_chars: Maximum characters per chunk (default: 16000)
            overlap_chars: Characters to overlap between chunks (default: 800)
        """
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> list[TextChunk]:
        """Split text into overlapping chunks.

        Attempts to split on paragraph boundaries when possible.
        If no paragraph break is found in the last 20% of a chunk,
        splits at max_chars boundary.

        Args:
            text: Full document text to chunk

        Returns:
            List of TextChunk objects with position metadata
        """
        if len(text) <= self.max_chars:
            return [
                TextChunk(
                    text=text,
                    start_char=0,
                    end_char=len(text),
                    chunk_index=0,
                    total_chunks=1,
                )
            ]

        chunks: list[TextChunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.max_chars, len(text))

            # Try to find paragraph boundary near end (if not at document end)
            if end < len(text):
                # Look for paragraph break in last 20% of chunk
                search_start = end - int(self.max_chars * 0.2)
                para_break = text.rfind("\n\n", search_start, end)
                if para_break > start:
                    end = para_break + 2  # Include the newlines

            chunk_text = text[start:end]
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    start_char=start,
                    end_char=end,
                    chunk_index=chunk_index,
                    total_chunks=0,  # Updated after all chunks created
                )
            )

            # Move start with overlap
            if end >= len(text):
                break
            start = end - self.overlap_chars
            chunk_index += 1

        # Update total_chunks on all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks
