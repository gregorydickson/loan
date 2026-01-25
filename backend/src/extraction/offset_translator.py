"""Offset translation between Docling markdown and raw text.

Docling converts PDF/DOCX to structured markdown with formatting changes.
Character positions in the markdown don't correspond directly to positions
in the original document. This module provides translation between the two.
"""

from difflib import SequenceMatcher

from rapidfuzz import fuzz


class OffsetTranslator:
    """Translate character offsets between Docling markdown and raw text.

    Docling's markdown output has different character positions than the
    raw PDF text due to:
    - Added markdown formatting (headers, lists, bold)
    - Whitespace normalization
    - Section reorganization

    This class finds anchor points (exact substring matches) between the
    two texts and interpolates positions between anchors.
    """

    def __init__(self, docling_markdown: str, raw_text: str | None = None):
        """Initialize with Docling markdown and optional raw text.

        Args:
            docling_markdown: Markdown text from Docling processor
            raw_text: Original raw text if available, None if only markdown
        """
        self.markdown = docling_markdown
        self.raw = raw_text
        self._matches: list[tuple[int, int, int]] = []

        if raw_text:
            self._build_alignment_map()

    def _build_alignment_map(self) -> None:
        """Build bidirectional character position mapping using difflib."""
        if not self.raw:
            return

        matcher = SequenceMatcher(None, self.markdown, self.raw, autojunk=False)
        self._matches = matcher.get_matching_blocks()

    def markdown_to_raw(self, start: int, end: int) -> tuple[int | None, int | None]:
        """Convert markdown character positions to raw text positions.

        Args:
            start: Start position in markdown (inclusive)
            end: End position in markdown (exclusive)

        Returns:
            Tuple of (raw_start, raw_end) or (None, None) if not mappable
        """
        if not self.raw or not self._matches:
            return (None, None)

        # Find the matching blocks that contain or are nearest to our positions
        raw_start = self._find_raw_position(start)
        raw_end = self._find_raw_position(end)

        return (raw_start, raw_end)

    def _find_raw_position(self, markdown_pos: int) -> int | None:
        """Find the raw text position corresponding to a markdown position."""
        if not self._matches:
            return None

        # Search through matching blocks
        for md_start, raw_start, length in self._matches:
            if length == 0:  # Skip empty matches
                continue
            if md_start <= markdown_pos < md_start + length:
                # Position is within this matching block
                offset = markdown_pos - md_start
                return raw_start + offset

        # Position not in a matching block - interpolate from nearest
        return self._interpolate_position(markdown_pos)

    def _interpolate_position(self, markdown_pos: int) -> int | None:
        """Interpolate raw position from nearest matching blocks."""
        if not self._matches or len(self._matches) < 2:
            return None

        # Find the blocks before and after the position
        before = None
        after = None

        for md_start, raw_start, length in self._matches:
            if length == 0:
                continue
            if md_start + length <= markdown_pos:
                before = (md_start + length, raw_start + length)
            elif md_start > markdown_pos and after is None:
                after = (md_start, raw_start)
                break

        if before and after:
            # Linear interpolation
            md_before, raw_before = before
            md_after, raw_after = after
            md_range = md_after - md_before
            if md_range == 0:
                return raw_before
            ratio = (markdown_pos - md_before) / md_range
            return int(raw_before + ratio * (raw_after - raw_before))

        return None

    def verify_offset(
        self,
        char_start: int,
        char_end: int,
        expected_text: str,
        threshold: float = 0.85,
    ) -> bool:
        """Verify that offsets correctly locate the expected text.

        Args:
            char_start: Start position (inclusive)
            char_end: End position (exclusive)
            expected_text: Text expected at this position
            threshold: Minimum fuzzy match ratio (0.0 to 1.0)

        Returns:
            True if the text at offsets matches expected text
        """
        if char_start < 0 or char_end > len(self.markdown):
            return False

        actual = self.markdown[char_start:char_end]

        # Exact match
        if actual == expected_text:
            return True

        # Fuzzy match using rapidfuzz (already in project)
        ratio = fuzz.ratio(actual, expected_text) / 100.0
        return ratio >= threshold

    def get_markdown_substring(self, char_start: int, char_end: int) -> str:
        """Get substring from markdown at given offsets.

        Args:
            char_start: Start position (inclusive)
            char_end: End position (exclusive)

        Returns:
            Substring or empty string if positions invalid
        """
        if char_start < 0 or char_end > len(self.markdown) or char_start >= char_end:
            return ""
        return self.markdown[char_start:char_end]
