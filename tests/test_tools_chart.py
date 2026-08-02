"""
◑ MiMi Nox – Phase 0.8 TDD
tests/test_tools_chart.py

Tests für core/tools/chart_tools.py: generate_chart (SVG-Generierung).

Given / When / Then – strikte Einhaltung.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.tools.chart_tools import _generate_svg_chart, generate_chart


class TestGenerateChart:

    @pytest.mark.asyncio
    async def test_returns_chart_file_path(self):
        """
        GIVEN  chart_type="bar", labels/values
        WHEN   generate_chart aufgerufen
        THEN   Rückgabe enthält "CHART_FILE:"
        """
        with patch("core.tools.chart_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text"):
            mock_home.return_value = Path("/tmp/fake_home")

            result = await generate_chart(
                chart_type="bar",
                title="Test Chart",
                labels=["A", "B"],
                values=[10, 20],
            )

            assert "CHART_FILE:" in result

    @pytest.mark.asyncio
    async def test_raises_on_mismatched_labels_values(self):
        """
        GIVEN  labels und values haben unterschiedliche Länge
        WHEN   generate_chart aufgerufen
        THEN   Rückgabe enthält Fehlermeldung
        """
        with patch("core.tools.chart_tools.Path.home") as mock_home:
            mock_home.return_value = Path("/tmp/fake_home")

            result = await generate_chart(
                chart_type="bar",
                title="Test",
                labels=["A"],
                values=[10, 20],
            )

            assert "muessen gleich lang" in result

    @pytest.mark.asyncio
    async def test_rejects_unknown_chart_type(self):
        """
        GIVEN  chart_type="unknown"
        WHEN   generate_chart aufgerufen
        THEN   Rückgabe enthält "Unbekannter Typ"
        """
        with patch("core.tools.chart_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text"):
            mock_home.return_value = Path("/tmp/fake_home")

            result = await generate_chart(
                chart_type="unknown",
                title="Test",
                labels=["A"],
                values=[10],
            )

            assert "Unbekannter Typ" in result


class TestGenerateSvgChart:

    def test_bar_chart_contains_rect(self):
        """
        GIVEN  chart_type="bar"
        WHEN   _generate_svg_chart aufgerufen
        THEN   Geschriebene SVG Datei enthält <rect>-Elemente
        """
        written = []
        def _fake_write(self, text, **kwargs):
            written.append(text)
        with patch("core.tools.chart_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text", _fake_write):
            mock_home.return_value = Path("/tmp/fake_home")
            result = _generate_svg_chart("bar", "Bar Chart", ["A", "B"], [10, 20])
        assert "CHART_FILE:" in result
        assert any("<rect" in w for w in written), "SVG sollte <rect> enthalten"

    def test_line_chart_contains_polyline(self):
        """
        GIVEN  chart_type="line"
        WHEN   _generate_svg_chart aufgerufen
        THEN   Geschriebene SVG Datei enthält <polyline>
        """
        written = []
        def _fake_write(self, text, **kwargs):
            written.append(text)
        with patch("core.tools.chart_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text", _fake_write):
            mock_home.return_value = Path("/tmp/fake_home")
            result = _generate_svg_chart("line", "Line Chart", ["A", "B"], [10, 20])
        assert "CHART_FILE:" in result
        assert any("<polyline" in w for w in written), "SVG sollte <polyline> enthalten"

    def test_pie_chart_contains_path(self):
        """
        GIVEN  chart_type="pie"
        WHEN   _generate_svg_chart aufgerufen
        THEN   Geschriebene SVG Datei enthält <path>
        """
        written = []
        def _fake_write(self, text, **kwargs):
            written.append(text)
        with patch("core.tools.chart_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text", _fake_write):
            mock_home.return_value = Path("/tmp/fake_home")
            result = _generate_svg_chart("pie", "Pie Chart", ["A", "B"], [30, 70])
        assert "CHART_FILE:" in result
        assert any("<path" in w for w in written), "SVG sollte <path> enthalten"

    def test_bar_chart_contains_single_value(self):
        """
        GIVEN  Nur ein Datenpunkt
        WHEN   _generate_svg_chart("bar", ...)
        THEN   Rückgabe enthält CHART_FILE:
        """
        with patch("core.tools.chart_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text"):
            mock_home.return_value = Path("/tmp/fake_home")
            result = _generate_svg_chart("bar", "Single", ["Only"], [42])
        assert "CHART_FILE:" in result

    def test_empty_values_returns_error(self):
        """
        GIVEN  Leere values-Liste
        WHEN   _generate_svg_chart aufgerufen
        THEN   Rückgabe enthält Fehler
        """
        with patch("core.tools.chart_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text"):
            mock_home.return_value = Path("/tmp/fake_home")
            result = _generate_svg_chart("bar", "Empty", ["A"], [])
        assert "muessen gleich lang" in result or "leer" in result
