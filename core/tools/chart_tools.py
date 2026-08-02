"""MiMi Nox – generate_chart tool (SVG fallback)."""

from __future__ import annotations

import html
import math
import re
import time
from pathlib import Path


async def generate_chart(
    chart_type: str,
    title: str,
    labels: list,
    values: list,
    xlabel: str = "",
    ylabel: str = "",
    color: str = "#22c55e",
) -> str:
    return _generate_svg_chart(chart_type, title, labels, values, xlabel=xlabel, ylabel=ylabel, color=color)


def _generate_svg_chart(
    chart_type: str,
    title: str,
    labels: list,
    values: list,
    xlabel: str = "",
    ylabel: str = "",
    color: str = "#16a34a",
) -> str:
    try:
        vals = [float(v) for v in values]
        clean_labels = [str(label)[:32] for label in labels]
        if len(clean_labels) != len(vals) or not vals:
            return "[chart: Labels und Werte muessen gleich lang und nicht leer sein]"
        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", title.strip())[:48].strip("_") or "chart"
        out = downloads / f"mimi_nox_chart_{safe_title}_{int(time.time())}.svg"
        width, height = 960, 600
        margin_left, margin_bottom, margin_top, margin_right = 94, 88, 92, 54
        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom
        max_val = max(vals) or 1.0
        min_val = min(0.0, min(vals))
        val_span = max(max_val - min_val, 1.0)
        accent = color if re.match(r"^#[0-9a-fA-F]{6}$", color) else "#16a34a"

        def sx(index: int) -> float:
            if len(vals) == 1:
                return margin_left + plot_w / 2
            return margin_left + index * (plot_w / (len(vals) - 1))

        def sy(value: float) -> float:
            return margin_top + plot_h - ((value - min_val) / val_span) * plot_h

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
            '<rect width="960" height="600" fill="#fbfcfb"/>',
            '<rect x="0" y="0" width="960" height="10" fill="#101820"/>',
            f'<text x="54" y="58" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#101820">{html.escape(title)}</text>',
            f'<text x="54" y="86" font-family="Arial, sans-serif" font-size="13" fill="#53606f">{html.escape(ylabel or "Values")} by {html.escape(xlabel or "Category")}</text>',
            f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#9ca3af" stroke-width="1"/>',
            f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#9ca3af" stroke-width="1"/>',
        ]
        for tick in range(5):
            value = min_val + val_span * tick / 4
            y = sy(value)
            parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + plot_w}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
            parts.append(f'<text x="{margin_left - 14}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#53606f">{value:g}</text>')

        ct = chart_type.lower()
        if ct == "bar":
            step = plot_w / max(len(vals), 1)
            bar_w = min(82, step * 0.58)
            for index, (label, value) in enumerate(zip(clean_labels, vals)):
                x = margin_left + index * step + (step - bar_w) / 2
                y = sy(value)
                h = margin_top + plot_h - y
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{accent}"/>')
                parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#101820">{value:g}</text>')
                parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{margin_top + plot_h + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#53606f">{html.escape(label)}</text>')
        elif ct == "line":
            points = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals))
            parts.append(f'<polyline points="{points}" fill="none" stroke="{accent}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>')
            for index, (label, value) in enumerate(zip(clean_labels, vals)):
                x, y = sx(index), sy(value)
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#fbfcfb" stroke="{accent}" stroke-width="3"/>')
                parts.append(f'<text x="{x:.1f}" y="{margin_top + plot_h + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#53606f">{html.escape(label)}</text>')
        elif ct == "pie":
            total = sum(abs(v) for v in vals) or 1.0
            x0, y0 = margin_left + 250, margin_top + 220
            start = -90.0
            palette = [accent, "#0891b2", "#d97706", "#64748b", "#22c55e", "#0f766e"]
            for index, (label, value) in enumerate(zip(clean_labels, vals)):
                angle = abs(value) / total * 360
                end = start + angle
                large = 1 if angle > 180 else 0
                x1 = x0 + 150 * math.cos(math.radians(start))
                y1 = y0 + 150 * math.sin(math.radians(start))
                x2 = x0 + 150 * math.cos(math.radians(end))
                y2 = y0 + 150 * math.sin(math.radians(end))
                fill = palette[index % len(palette)]
                parts.append(f'<path d="M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f} A150,150 0 {large},1 {x2:.1f},{y2:.1f} Z" fill="{fill}"/>')
                parts.append(f'<rect x="650" y="{150 + index * 28}" width="14" height="14" fill="{fill}"/><text x="674" y="{162 + index * 28}" font-family="Arial, sans-serif" font-size="13" fill="#101820">{html.escape(label)} ({value:g})</text>')
                start = end
        else:
            return f"[chart: Unbekannter Typ '{chart_type}'. Erlaubt: bar, line, pie]"

        parts.append('<text x="54" y="568" font-family="Arial, sans-serif" font-size="12" fill="#53606f">Generated locally by MiMi Nox - SVG fallback renderer</text>')
        parts.append("</svg>")
        out.write_text("\n".join(parts), encoding="utf-8")
        return f"CHART_FILE:{out}"
    except Exception as exc:
        return f"[chart-Fehler: {exc}]"
