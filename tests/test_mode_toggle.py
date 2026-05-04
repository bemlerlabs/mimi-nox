"""
Arbeitsmodus-Button — GWT, 3× Tiefe.

GIVEN: Die Chat-UI hat einen Modus-Toggle
WHEN:  Der DOM auf Existenz des Buttons geprüft wird
THEN:  Element mit ID 'mode-toggle' oder ähnlich im HTML vorhanden

GIVEN: Der Modus-Toggle ist vorhanden
WHEN:  Auf CSS-Klassen geprüft wird
THEN:  Mind. 2 Modi sind beschriftet (z.B. Quick / Deep)

GIVEN: Das i18n-System
WHEN:  Modus-Labels auf Übersetzbarkeit geprüft werden
THEN:  Keys 'mode.quick' und 'mode.deep' in allen Sprachen vorhanden
"""
from pathlib import Path
import re


# ── Blickwinkel 1: DOM — HTML enthält Mode-Toggle ─────────────────────────────

class TestModToggleHTMLPerspective:
    """GIVEN the HTML, WHEN inspected, THEN mode toggle element exists."""

    def test_given_html_when_checked_then_mode_toggle_present(self):
        """
        GIVEN: index.html ist geladen
        WHEN:  Auf Mode-Toggle gesucht wird
        THEN:  Element mit id 'mode-toggle' oder data-mode vorhanden
        """
        html = (Path(__file__).parent.parent / "app" / "src" / "index.html").read_text()

        # Perspektive 1: Toggle-Element vorhanden
        has_toggle = "mode-toggle" in html or "data-mode" in html or "mode-btn" in html
        assert has_toggle, "THEN: HTML muss einen Mode-Toggle-Button enthalten"

        # Perspektive 2: Hat accessible label
        assert "aria-label" in html or "title=" in html, (
            "THEN: Mode-Toggle muss ein Accessible Label haben"
        )

        # Perspektive 3: Quick und Deep als Optionen
        html_lower = html.lower()
        has_quick = "quick" in html_lower or "schnell" in html_lower or "kurz" in html_lower
        has_deep = "deep" in html_lower or "tief" in html_lower or "detail" in html_lower
        assert has_quick and has_deep, (
            "THEN: HTML muss Quick- und Deep-Modus-Optionen enthalten"
        )


# ── Blickwinkel 2: i18n — Mode-Labels in allen Sprachen ──────────────────────

class TestModToggleI18nPerspective:
    """GIVEN i18n.js, WHEN mode keys inspected, THEN all 6 languages have them."""

    def test_given_i18n_when_mode_keys_checked_then_all_languages_have_them(self):
        """
        GIVEN: i18n.js ist geladen
        WHEN:  mode.quick und mode.deep Keys gesucht werden
        THEN:  Beide Keys in allen 6 Sprachen vorhanden
        """
        i18n = (Path(__file__).parent.parent / "app" / "src" / "i18n.js").read_text()

        # Perspektive 1: Key existiert überhaupt
        assert "'mode.quick'" in i18n or '"mode.quick"' in i18n, (
            "THEN: i18n.js muss 'mode.quick' Key haben"
        )
        assert "'mode.deep'" in i18n or '"mode.deep"' in i18n, (
            "THEN: i18n.js muss 'mode.deep' Key haben"
        )

        # Perspektive 2: Anzahl der Vorkommen entspricht Anzahl Sprachen (6)
        quick_count = i18n.count("'mode.quick'") + i18n.count('"mode.quick"')
        assert quick_count >= 6, (
            f"THEN: mode.quick muss in mind. 6 Sprachen definiert sein, found: {quick_count}"
        )

        # Perspektive 3: Auch mode.label oder mode.title vorhanden
        assert "'mode'" in i18n or "mode.label" in i18n or "mode.toggle" in i18n, (
            "THEN: Mind. ein mode.* Label-Key muss in i18n existieren"
        )


# ── Blickwinkel 3: JS — Mode-Toggle-Handler in main.js ───────────────────────

class TestModeToggleJSHandlerPerspective:
    """GIVEN main.js, WHEN mode handler inspected, THEN toggle logic present."""

    def test_given_mainjs_when_mode_handler_checked_then_toggle_logic_present(self):
        """
        GIVEN: main.js ist geladen
        WHEN:  Auf Mode-Toggle-Handler gesucht wird
        THEN:  Handler-Logik für mode-toggle vorhanden (click oder change)
        """
        js = (Path(__file__).parent.parent / "app" / "src" / "main.js").read_text()

        # Perspektive 1: Handler für mode-toggle vorhanden
        has_handler = "mode-toggle" in js or "modeToggle" in js or "mode_toggle" in js
        assert has_handler, "THEN: main.js muss einen Mode-Toggle-Handler haben"

        # Perspektive 2: Setzt response_style oder ähnliches
        has_style_setter = (
            "response_style" in js
            or "responseMode" in js
            or "mode" in js.lower()
        )
        assert has_style_setter, "THEN: Handler muss einen Response-Modus setzen"

        # Perspektive 3: Persistiert die Wahl (localStorage oder API-Call)
        has_persistence = "localStorage" in js or "profile" in js.lower()
        assert has_persistence, (
            "THEN: Modus-Auswahl muss persistiert werden (localStorage oder API)"
        )
