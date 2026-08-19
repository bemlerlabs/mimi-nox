"""Sprint2-F2 Regression tests: venv/CI-Python-Parity + PWA-Hygiene.

DoD (SPECK, CTO-pinned):
  1. venv auf Python >=3.10, alle Tests im venv grün.
  2. CI-Python-Parity: tests.yml läuft dieselbe Python wie lokal (matrix/
     lower bound deckt requires-python ab, lokale venv-Version liegt in
     der CI-Matrix).
  3. PWA-Hygiene: app/public/llms.txt + robots.txt vorhanden (Lighthouse
     Audits llms-txt/robots-txt -> 1.0); Color-Contrast-Fix in der
     Tailwind-Config (globals.css @theme) -> Audit color-contrast 1.0.
  5. TDD: diese Tests existieren VOR der Implementierung.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "app" / "public"
GLOBALS_CSS = ROOT / "app" / "src" / "styles" / "globals.css"
PYPROJECT = ROOT / "pyproject.toml"
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
VENV_CFG = ROOT / ".venv" / "pyvenv.cfg"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"

WCAG_NORMAL_TEXT_RATIO = 4.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hsl_to_srgb(h: float, s: float, l: float) -> tuple[float, float, float]:
    """h in deg, s/l in percent -> srgb 0..1."""
    s /= 100.0
    l /= 100.0
    c = (1 - abs(2 * l - 1)) * s
    hp = h % 360 / 60
    x = c * (1 - abs(hp % 2 - 1))
    if hp < 1:
        r, g, b = c, x, 0.0
    elif hp < 2:
        r, g, b = x, c, 0.0
    elif hp < 3:
        r, g, b = 0.0, c, x
    elif hp < 4:
        r, g, b = 0.0, x, c
    elif hp < 5:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    m = l - c / 2
    return (r + m, g + m, b + m)


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    def chan(v: float) -> float:
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hsl_a: str, hsl_b: str) -> float:
    def parse(hsl: str) -> tuple[float, float, float]:
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%", hsl)
        assert m, f"unparsable hsl: {hsl!r}"
        return float(m.group(1)), float(m.group(2)), float(m.group(3))

    la = _relative_luminance(_hsl_to_srgb(*parse(hsl_a)))
    lb = _relative_luminance(_hsl_to_srgb(*parse(hsl_b)))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _theme_tokens() -> dict[str, str]:
    """Parse --color-* tokens out of the @theme block of globals.css."""
    text = GLOBALS_CSS.read_text(encoding="utf-8")
    m = re.search(r"@theme\s*\{(.*?)\n\}", text, re.DOTALL)
    assert m, "no @theme block found in globals.css"
    tokens: dict[str, str] = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"\s*--([a-z0-9-]+):\s*([^/;]+)", line)
        if mm and mm.group(1).startswith("color-"):
            tokens[mm.group(1)[6:]] = mm.group(2).strip()
    return tokens


def _requires_python_min() -> tuple[int, int]:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'requires-python\s*=\s*">=([\d.]+)"', text)
    assert m, "requires-python not found in pyproject.toml"
    parts = m.group(1).split(".")
    return int(parts[0]), int(parts[1])


def _supported_python_versions() -> list[tuple[int, int]]:
    """Klassifizierer 'Programming Language :: Python :: 3.X' = offiziell
    unterstützte Versionen. Parity-Ziel: venv & CI-Matrix ⊆ diesem Set."""
    text = PYPROJECT.read_text(encoding="utf-8")
    out = set()
    for v in re.findall(r"Programming Language :: Python :: (3\.\d+)", text):
        a, b = v.split(".")
        out.add((int(a), int(b)))
    assert out, "keine Python-Klassifizierer in pyproject.toml gefunden"
    return sorted(out)


def _ci_python_matrix() -> list[tuple[int, int]]:
    text = TESTS_WORKFLOW.read_text(encoding="utf-8")
    m = re.search(r"python-version:\s*\[([^\]]+)\]", text)
    assert m, "python-version matrix not found in tests.yml"
    out = []
    for entry in re.findall(r"'(\d+)\.(\d+)'", m.group(1)):
        out.append((int(entry[0]), int(entry[1])))
    assert out, "no python versions parsed from CI matrix"
    return out


def _venv_python() -> tuple[int, int]:
    """Version der REALEN venv-Python-Binary — nicht nur pyvenv.cfg.

    Root-Cause-Verteidigung (Sprint2-Fix, DEFEKT 2): pyvenv.cfg ist ein
    STALE-Artefakt (behält nach Rebuild/Ersetzung die alte Version), daher
    nicht die Single-Source-of-Truth. Wir fragen die tatsächliche Binary
    per subprocess ab und ASSERTEN, dass sie pyvenv.cfg gleicht. Weichen
    beide ab, FAILT dieser Helper — und damit jeder Parity-Test, der ihn
    nutzt — exakt im jetzt-entdeckten Zustand (cfg=3.13.5 stale,
    Binary=3.12.13). Eine STALE cfg wird so künftig vom Test selbst erwischt.
    """
    # (1) REALE Binary — Source of Truth
    result = subprocess.run(
        [
            str(VENV_PYTHON), "-c",
            "import sys; print(sys.version_info[0], sys.version_info[1])",
        ],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f".venv/bin/python lieferte Exit {result.returncode}: "
        f"{result.stderr.strip()}"
    )
    out = result.stdout.strip().split()
    assert len(out) == 2 and out[0].isdigit() and out[1].isdigit(), (
        f"unerwartete Versions-Output von .venv/bin/python: "
        f"{result.stdout.strip()!r}"
    )
    binary = (int(out[0]), int(out[1]))

    # (2) pyvenv.cfg — muss stimmen (STALE cfg = Root-Cause-Zustand -> FAIL)
    cfg = _venv_cfg_python()
    assert binary == cfg, (
        f".venv inkonsistent: reale Python-Binary ist {binary[0]}.{binary[1]} "
        f"aber pyvenv.cfg sagt {cfg[0]}.{cfg[1]} (STALE-Artefakt — venv wurde "
        f"rebuildet/ersetzt, ohne pyvenv.cfg zu regenerieren). venv "
        f"konsistent neu bauen: python3.{binary[1]} -m venv .venv"
    )
    return binary


def _venv_cfg_python() -> tuple[int, int]:
    """Version aus .venv/pyvenv.cfg (nur der cfg-Wert — zum Verrechnen)."""
    text = VENV_CFG.read_text(encoding="utf-8")
    m = re.search(r"^version\s*=\s*(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "version not found in .venv/pyvenv.cfg"
    return int(m.group(1)), int(m.group(2))


# ---------------------------------------------------------------------------
# DoD 1 — venv auf Python >=3.10
# ---------------------------------------------------------------------------

def test_venv_python_satisfies_requires_python() -> None:
    venv = _venv_python()
    req = _requires_python_min()
    assert venv >= req, (
        f".venv Python {venv[0]}.{venv[1]} < requires-python >= {req[0]}.{req[1]}"
    )


# ---------------------------------------------------------------------------
# DoD 2 — CI-Python-Parity
# ---------------------------------------------------------------------------

def test_ci_matrix_lower_bound_matches_requires_python() -> None:
    """CI darf nicht unterhalb von requires-python testen (diese Umgebung
    existiert für das Paket nicht) und die Matrix-Untergrenze muss die
    deklarierter Lower Bound entsprechen (kein totes Testfenster)."""
    matrix = _ci_python_matrix()
    req = _requires_python_min()
    assert min(matrix) >= req, (
        f"CI-Matrix-Minimum {min(matrix)} liegt unter requires-python "
        f">= {req[0]}.{req[1]} — CI testet eine nicht unterstützte Python"
    )


def test_local_venv_python_in_ci_matrix() -> None:
    """Parity: die lokal genutzte venv-Python muss aus dem offiziellen
    Unterstützt-Set (Klassifizierer) kommen und in der CI-Matrix liegen
    (wenn CI nur eine Version pro minor testet, ist 'unterstützt' der
    Maßstab — CI läuft dieselbe Minor-Version wie lokal)."""
    venv = _venv_python()
    matrix = _ci_python_matrix()
    supported = _supported_python_versions()
    assert venv in supported, (
        f"lokale venv Python {venv[0]}.{venv[1]} nicht in den "
        f"unterstützten Versionen {supported}"
    )
    assert venv in matrix, (
        f"lokale venv Python {venv[0]}.{venv[1]} fehlt in CI-Matrix {matrix} "
        f"— CI testet dieselbe Python nicht (Parity verletzt)"
    )
    assert set(matrix) <= set(supported), (
        f"CI-Matrix {matrix} enthält Versionen außerhalb des "
        f"unterstützten Sets {supported}"
    )


# ---------------------------------------------------------------------------
# DoD 3a — llms.txt
# ---------------------------------------------------------------------------

def test_llms_txt_exists_and_valid() -> None:
    f = PUBLIC_DIR / "llms.txt"
    assert f.is_file(), "app/public/llms.txt fehlt (Lighthouse llms-txt-Audit)"
    text = f.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines, "llms.txt ist leer"
    assert lines[0].startswith("#"), "llms.txt muss mit H1-Header beginnen"
    assert any("mimi" in ln.lower() for ln in lines), (
        "llms.txt identifiziert das Projekt nicht (MiMi Nox)"
    )
    assert len(text) >= 200, "llms.txt zu dünn (<200 chars) — kein nützlicher Kontext"
    # Lighthouse-llms-txt-Audit: braucht mindestens einen Markdown-Link
    assert re.search(r"\[[^\]]+\]\(https?://[^)\s]+[)\s]", text), (
        "llms.txt muss mindestens einen Markdown-Link [text](https://...) "
        "enthalten (Lighthouse: 'File does not appear to contain any links.')"
    )


# ---------------------------------------------------------------------------
# DoD 3b — robots.txt
# ---------------------------------------------------------------------------

def test_robots_txt_exists_and_valid() -> None:
    f = PUBLIC_DIR / "robots.txt"
    assert f.is_file(), "app/public/robots.txt fehlt (Lighthouse robots-txt-Audit)"
    text = f.read_text(encoding="utf-8")
    assert re.search(r"^User-agent:\s*\*", text, re.MULTILINE | re.IGNORECASE), (
        "robots.txt braucht eine User-agent-*-Regel"
    )
    assert re.search(r"^(Allow|Disallow):", text, re.MULTILINE | re.IGNORECASE), (
        "robots.txt braucht Allow/Disallow"
    )
    # Lighthouse validiert Sitemap-URLs strikt — nur http(s), sonst Score 0
    for m in re.finditer(r"^Sitemap:\s*(\S+)", text, re.MULTILINE | re.IGNORECASE):
        assert m.group(1).startswith(("http://", "https://")), (
            f"ungültige Sitemap-URL in robots.txt: {m.group(1)}"
        )


# ---------------------------------------------------------------------------
# DoD 3c — Color-Contrast (Tailwind v4 @theme-Tokens in globals.css)
# ---------------------------------------------------------------------------

# (foreground-token, background-token) — alle Text/Background-Kombinationen,
# die die UI aus den @theme-Tokens nutzt. WCAG 2.1 AA: 4.5:1 für Normaltext.
CONTRAST_PAIRS: list[tuple[str, str]] = [
    ("foreground", "background"),
    ("stone", "background"),
    ("mist", "background"),
    ("mist", "card"),
    ("muted-foreground", "background"),
    ("muted-foreground", "card"),
    ("firefly", "background"),
    ("firefly-glow", "background"),
    ("primary", "background"),
    ("primary-foreground", "primary"),
    ("secondary-foreground", "secondary"),
    ("accent-foreground", "accent"),
    ("destructive-foreground", "destructive"),
    # (destructive auf background: Token wird in der UI nicht als Text
    #  verwendet — kein text-/bg-destructive-Verbrauch; Lighthouse prüft
    #  nur gerenderten Text. Bewusst NICHT im Test-Pair.)
    ("card-foreground", "card"),
    ("foreground", "muted"),
]


@pytest.mark.parametrize("fg,bg", CONTRAST_PAIRS)
def test_token_contrast_meets_wcag_aa(fg: str, bg: str) -> None:
    tokens = _theme_tokens()
    assert fg in tokens, f"@theme-Token --color-{fg} fehlt"
    assert bg in tokens, f"@theme-Token --color-{bg} fehlt"
    ratio = _contrast_ratio(tokens[fg], tokens[bg])
    assert ratio >= WCAG_NORMAL_TEXT_RATIO, (
        f"--color-{fg} auf --color-{bg}: Kontrast {ratio:.2f}:1 "
        f"< {WCAG_NORMAL_TEXT_RATIO}:1 (WCAG AA Normaltext)"
    )


def test_no_low_contrast_gradient_text() -> None:
    """text-gradient-Utility: jede Gradient-Stop-Helligkeit muss als Text
    auf dem Haupt-Hintergrund lesbar bleiben (Lighthouse prüft den
    erzielbaren Mindestkontrast über den Farbverlauf)."""
    text = GLOBALS_CSS.read_text(encoding="utf-8")
    m = re.search(r"\.text-gradient\s*\{[^}]*\}", text, re.DOTALL)
    assert m, ".text-gradient Utility fehlt"
    block = re.sub(r"/\*.*?\*/", "", m.group(0), flags=re.DOTALL)  # Kommentare raus
    stops = re.findall(r"hsl\((\d+(?:\.\d+)?) (\d+(?:\.\d+)?)% (\d+(?:\.\d+)?)%\)",
                       block)
    assert stops, "keine hsl()-Stops in .text-gradient gefunden"
    tokens = _theme_tokens()
    bg = tokens["background"]
    for stop in stops:
        hsl = f"{stop[0]} {stop[1]}% {stop[2]}%"
        ratio = _contrast_ratio(hsl, bg)
        assert ratio >= WCAG_NORMAL_TEXT_RATIO, (
            f"text-gradient-Stop {hsl} auf background: {ratio:.2f}:1 "
            f"< {WCAG_NORMAL_TEXT_RATIO}:1"
        )
