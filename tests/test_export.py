"""
Chat Export — GWT, 3× Tiefe.

GIVEN: Der aktuelle Chatverlauf
WHEN:  Der Export-Button geklickt wird
THEN:  Die Nachrichten werden als Markdown formatiert heruntergeladen.

GIVEN: Das Backend
WHEN:  Ein POST Request mit JSON-Messages auf /api/export eingeht
THEN:  Liefert das Backend den formatierten Markdown-String zurück.

GIVEN: Die UI
WHEN:  Der Button zum Exportieren im Chat-Header gesucht wird
THEN:  Existiert ein valider Export-Button.
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# ── Blickwinkel 1: Markdown Formatting ──────────────────────────────────────

class TestExportFormattingPerspective:
    """GIVEN a list of messages, WHEN formatted, THEN markdown structure is correct."""

    def test_given_messages_when_formatted_then_markdown_is_correct(self):
        """
        GIVEN: Eine Liste von Dictionaries mit 'role' und 'content'
        WHEN:  Die Formatierungs-Funktion aufgerufen wird
        THEN:  Ist der Rückgabewert gültiges Markdown
        """
        from core.export import format_chat_markdown
        
        messages = [
            {"role": "user", "content": "Hallo MiMi"},
            {"role": "assistant", "content": "Hallo Mensch!"}
        ]
        
        md = format_chat_markdown(messages)
        
        assert "## Chat Export" in md
        assert "**Nutzer:**" in md
        assert "Hallo MiMi" in md
        assert "**MiMi:**" in md
        assert "Hallo Mensch!" in md


# ── Blickwinkel 2: API Endpoint ──────────────────────────────────────────────

class TestExportApiPerspective:
    """GIVEN export API, WHEN posted with messages, THEN returns file payload."""

    def test_given_app_when_post_export_then_returns_markdown(self):
        """
        GIVEN: Der FastAPI TestClient und ein Payload mit Chat-Verlauf
        WHEN:  POST /api/export
        THEN:  Return 200 und Content-Type text/markdown
        """
        from server.main import app
        
        with TestClient(app) as client:
            payload = {
                "messages": [
                    {"role": "user", "content": "Test"}
                ]
            }
            res = client.post("/api/export", json=payload)
            
            assert res.status_code == 200
            assert "text/markdown" in res.headers.get("content-type", "")
            assert "Test" in res.text


# ── Blickwinkel 3: UI Button ─────────────────────────────────────────────────

class TestExportUiPerspective:
    """GIVEN index.html, WHEN parsed, THEN export button exists."""

    @pytest.mark.skip(reason="Legacy PWA migrated to React+Vite; source files (app/src/index.html, main.js, i18n.js, service-worker.js) and legacy UI features (export button, mode toggle, tasks tab) were removed/refactored. Test references stale paths.")
    def test_given_html_when_parsed_then_export_button_exists(self):
        """
        GIVEN: index.html
        WHEN:  Nach dem Export-Element gesucht wird
        THEN:  Ein Button mit passender ID und Event-Bindung existiert
        """
        html = (Path(__file__).parent.parent / "app" / "src" / "index.html").read_text()
        
        # Perspektive: Button im Chat-Header
        assert 'id="btn-export-chat"' in html or 'Export' in html
    @pytest.mark.skip(reason="Legacy PWA migrated to React+Vite; source files (app/src/index.html, main.js, i18n.js, service-worker.js) and legacy UI features (export button, mode toggle, tasks tab) were removed/refactored. Test references stale paths.")

    def test_given_js_when_parsed_then_export_logic_exists(self):
        """
        GIVEN: main.js
        WHEN:  Nach der Download-Logik gesucht wird
        THEN:  fetch('/api/export') und Blob-Erzeugung existieren
        """
        js = (Path(__file__).parent.parent / "app" / "src" / "main.js").read_text()
        js_modules = js
        for f in (Path(__file__).parent.parent / "app" / "src" / "modules").glob("*.js"):
            js_modules += f.read_text()
        
        assert 'exportChat' in js_modules
        assert 'Blob' in js_modules
        assert 'createObjectURL' in js_modules
