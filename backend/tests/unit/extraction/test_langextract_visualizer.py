"""Unit tests for LangExtractVisualizer."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.extraction.langextract_visualizer import LangExtractVisualizer


class TestLangExtractVisualizer:
    """Tests for LangExtractVisualizer."""

    def test_generate_html_with_none_returns_empty_placeholder(self):
        """When raw_extractions is None, return empty placeholder HTML."""
        viz = LangExtractVisualizer()
        html = viz.generate_html(None)
        assert "No Extractions Found" in html
        assert "<html>" in html

    def test_generate_empty_visualization_structure(self):
        """Empty visualization has proper HTML structure."""
        viz = LangExtractVisualizer()
        html = viz._generate_empty_visualization()
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "No Extractions Found" in html

    @patch("src.extraction.langextract_visualizer.lx")
    def test_generate_html_calls_lx_visualize(self, mock_lx):
        """Verify lx.visualize() is called with correct parameters."""
        mock_result = MagicMock()
        mock_html_obj = MagicMock()
        mock_html_obj.data = "<html>mocked</html>"
        mock_lx.visualize.return_value = mock_html_obj

        viz = LangExtractVisualizer()
        result = viz.generate_html(mock_result, animation_speed=1.0, show_legend=False)

        mock_lx.visualize.assert_called_once_with(
            data_source=mock_result,
            animation_speed=1.0,
            show_legend=False,
            gif_optimized=False,
        )
        assert result == "<html>mocked</html>"

    @patch("src.extraction.langextract_visualizer.lx")
    def test_generate_html_handles_string_return(self, mock_lx):
        """When lx.visualize returns object without .data, use str()."""
        mock_result = MagicMock()

        # Create a simple object without .data that returns string when converted
        class HtmlObjectNoData:
            def __str__(self):
                return "<html>string</html>"

        mock_lx.visualize.return_value = HtmlObjectNoData()

        viz = LangExtractVisualizer()
        result = viz.generate_html(mock_result)

        # str() should be called since no .data attribute
        assert result == "<html>string</html>"

    @patch("src.extraction.langextract_visualizer.lx")
    def test_generate_html_default_parameters(self, mock_lx):
        """Default animation_speed=0.5 and show_legend=True."""
        mock_result = MagicMock()
        mock_html_obj = MagicMock()
        mock_html_obj.data = "<html></html>"
        mock_lx.visualize.return_value = mock_html_obj

        viz = LangExtractVisualizer()
        viz.generate_html(mock_result)

        mock_lx.visualize.assert_called_once_with(
            data_source=mock_result,
            animation_speed=0.5,
            show_legend=True,
            gif_optimized=False,
        )

    def test_save_html_writes_file(self, tmp_path):
        """save_html() writes HTML content to file."""
        viz = LangExtractVisualizer()
        output_file = tmp_path / "test.html"

        viz.save_html(None, output_file)  # Will use empty placeholder

        assert output_file.exists()
        content = output_file.read_text()
        assert "No Extractions Found" in content

    @patch("src.extraction.langextract_visualizer.lx")
    def test_save_html_with_extractions(self, mock_lx, tmp_path):
        """save_html() writes lx.visualize output to file."""
        mock_result = MagicMock()
        mock_html_obj = MagicMock()
        mock_html_obj.data = "<html>test content</html>"
        mock_lx.visualize.return_value = mock_html_obj

        viz = LangExtractVisualizer()
        output_file = tmp_path / "extraction.html"

        viz.save_html(mock_result, output_file, animation_speed=2.0)

        assert output_file.exists()
        content = output_file.read_text()
        assert content == "<html>test content</html>"

    @patch("src.extraction.langextract_visualizer.lx")
    def test_save_html_passes_parameters(self, mock_lx, tmp_path):
        """save_html() passes all parameters to generate_html."""
        mock_result = MagicMock()
        mock_html_obj = MagicMock()
        mock_html_obj.data = "<html></html>"
        mock_lx.visualize.return_value = mock_html_obj

        viz = LangExtractVisualizer()
        output_file = tmp_path / "test.html"

        viz.save_html(
            mock_result,
            output_file,
            animation_speed=3.0,
            show_legend=False
        )

        mock_lx.visualize.assert_called_once_with(
            data_source=mock_result,
            animation_speed=3.0,
            show_legend=False,
            gif_optimized=False,
        )
