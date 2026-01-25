"""LangExtract HTML visualization wrapper.

Generates interactive HTML with highlighted source spans from extraction results.
"""

import langextract as lx
from langextract.core.data import AnnotatedDocument
from pathlib import Path


class LangExtractVisualizer:
    """Generate HTML visualizations of LangExtract extraction results."""

    def generate_html(
        self,
        raw_extractions: AnnotatedDocument | None,
        animation_speed: float = 0.5,
        show_legend: bool = True,
    ) -> str:
        """Generate interactive HTML visualization with highlighted source spans.

        LXTR-07: LangExtract generates HTML visualization with highlighted source spans

        Args:
            raw_extractions: LangExtract AnnotatedDocument result (from LangExtractResult.raw_extractions)
            animation_speed: Seconds between extraction highlights (default 0.5)
            show_legend: Show extraction class color legend (default True)

        Returns:
            HTML string with embedded JavaScript for interactivity
        """
        if not raw_extractions:
            return self._generate_empty_visualization()

        html_obj = lx.visualize(
            data_source=raw_extractions,
            animation_speed=animation_speed,
            show_legend=show_legend,
            gif_optimized=False,  # Not for video capture
        )

        # Handle both Jupyter and standalone contexts
        if hasattr(html_obj, 'data'):
            return html_obj.data
        return str(html_obj)

    def save_html(
        self,
        raw_extractions: AnnotatedDocument | None,
        output_path: Path,
        animation_speed: float = 0.5,
        show_legend: bool = True,
    ) -> None:
        """Generate and save HTML visualization to file.

        Args:
            raw_extractions: LangExtract AnnotatedDocument result
            output_path: Path to write HTML file
            animation_speed: Seconds between extraction highlights
            show_legend: Show extraction class color legend
        """
        html_content = self.generate_html(
            raw_extractions=raw_extractions,
            animation_speed=animation_speed,
            show_legend=show_legend,
        )
        output_path.write_text(html_content)

    def _generate_empty_visualization(self) -> str:
        """Generate placeholder HTML when no extractions exist."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Extraction Visualization</title>
    <style>
        body { font-family: system-ui, sans-serif; padding: 2rem; }
        .empty { color: #666; text-align: center; margin-top: 4rem; }
    </style>
</head>
<body>
    <div class="empty">
        <h1>No Extractions Found</h1>
        <p>LangExtract did not find any entities in this document.</p>
    </div>
</body>
</html>'''
