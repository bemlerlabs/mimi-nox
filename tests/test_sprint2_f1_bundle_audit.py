"""Sprint2-F1: Bundle-Audit-Tooling (app/scripts/bundle_audit.py) — Semantik-Tests.

SPECK (CTO-pinned): DoD (1) Initial-Bundle gzip < 500 KB, messbar via build-Output.
Dieser Test sichert die Mess-Semantik ab: dynamische `import()`-Referenzen
(React.lazy Route-Split) gehören NICHT zum Initial-Bundle, statische
Import-Closures und modulepreload-Referenzen schon. Ein Fehler in der
Initial/Lazy-Klassifikation wäre eine stille DoD-Fehlmessung (Über- oder
Unterschätzung), daher wird sie hier gegen ein synthetisches dist-Fixture
gesichert.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "app" / "scripts" / "bundle_audit.py"


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def _make_dist(dist: Path) -> None:
    """Synthetisches dist: index.html → entry.js (static closure: shared.js + css),
    entry.js lädt route.js per import() (lazy), route.js → heavy.js (lazy closure).
    Vergrößerung der lazy-Teile muss die Initial-Messung NICHT bewegen."""
    _write(
        dist / "index.html",
        '<script type="module" src="/assets/entry.js"></script>\n'
        '<link rel="stylesheet" href="/assets/style.css">\n',
    )
    _write(dist / "assets" / "style.css", "body{color:red}")
    _write(
        dist / "assets" / "entry.js",
        'import { x } from "./shared.js";'
        'const route = () => import("./route.js");'
        "export { x };\n",
    )
    _write(dist / "assets" / "shared.js", "export const x = 1;\n")
    _write(
        dist / "assets" / "route.js",
        'import { h } from "./heavy.js";export const r = h;\n',
    )
    # lazy-closure absichtlich groß halten: darf die Initial-Größe nicht bewegen
    _write(dist / "assets" / "heavy.js", "export const h = '" + "z" * 20000 + "';\n")


def _run_audit(dist: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(AUDIT), str(dist)],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout


def test_given_synthetic_dist_when_audit_then_lazy_chunks_excluded_from_initial(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _make_dist(dist)
    rc, out = _run_audit(dist)
    assert rc == 0, out
    # Initial-Closure: entry.js + shared.js + style.css (route.js/heavy.js NICHT)
    assert "entry.js" in out.split("INITIAL TOTAL")[0]
    assert "shared.js" in out.split("INITIAL TOTAL")[0]
    assert "style.css" in out.split("INITIAL TOTAL")[0]
    # Lazy-Chunks (Route-Split) werden separat gezählt
    lazy_section = out.split("LAZY chunks")[1]
    assert "route.js" in lazy_section
    assert "heavy.js" in lazy_section
    assert "entry.js" not in lazy_section


def test_given_large_lazy_chunk_when_audit_then_initial_budget_untouched(tmp_path: Path) -> None:
    """Regression-Sicherung: 20KB-Heavy-Chunk liegt NUR in der lazy-Closure →
    PASS. Würde die Klassifikation ihn initial zählen, müßte die Initial-Zeile
    entsprechend dicker ausfallen. Prüft die Budget-Entscheidung explizit."""
    dist = tmp_path / "dist"
    _make_dist(dist)
    rc, out = _run_audit(dist)
    assert rc == 0, out
    assert "PASS" in out
    initial_block = out.split("INITIAL TOTAL")[0]
    assert "heavy.js" not in initial_block
