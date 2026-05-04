"""
Task UI Integration — GWT, 3× Tiefe.

GIVEN: Die API für Tasks
WHEN:  GET /api/tasks aufgerufen wird
THEN:  Liefert eine Liste der Tasks aus dem Manager

GIVEN: Das DOM im Frontend
WHEN:  Der Tasks-Tab aufgerufen wird
THEN:  Es existiert ein Container für die Liste und ein Nav-Link

GIVEN: Die JS Logik
WHEN:  Die UI gerendert wird
THEN:  Render-Funktion für Tasks existiert und verarbeitet JSON Status
"""
import pytest
from pathlib import Path

# ── Blickwinkel 1: API Endpoint ──────────────────────────────────────────────

class TestTasksApiPerspective:
    """GIVEN tasks API, WHEN fetched, THEN returns JSON task list."""

    def test_given_app_when_get_tasks_then_returns_json(self):
        """
        GIVEN: Der FastAPI TestClient
        WHEN:  GET /api/tasks
        THEN:  Return 200 und eine JSON Liste
        """
        from fastapi.testclient import TestClient
        from server.main import app
        
        with TestClient(app) as client:
            res = client.get("/api/tasks")
            assert res.status_code == 200
            data = res.json()
            assert isinstance(data, list)


# ── Blickwinkel 2: HTML DOM ──────────────────────────────────────────────────

class TestTasksHtmlPerspective:
    """GIVEN index.html, WHEN parsed, THEN task tab and container exist."""

    def test_given_html_when_parsed_then_task_tab_exists(self):
        """
        GIVEN: index.html
        WHEN:  Nach Task-Elementen gesucht wird
        THEN:  Nav-Item und Content-Tab vorhanden
        """
        html = (Path(__file__).parent.parent / "app" / "src" / "index.html").read_text()
        
        # Perspektive 1: Navigationslink
        assert 'data-target="view-tasks"' in html or 'href="#tasks"' in html or 'id="nav-tasks"' in html or 'nav.tasks' in html
        
        # Perspektive 2: Tab-Content Bereich
        assert 'id="view-tasks"' in html
        
        # Perspektive 3: Liste für Tasks
        assert 'id="tasks-list"' in html or 'id="task-list"' in html


# ── Blickwinkel 3: JS Rendering ──────────────────────────────────────────────

class TestTasksJsPerspective:
    """GIVEN main.js, WHEN parsed, THEN task render logic exists."""

    def test_given_js_when_parsed_then_render_logic_exists(self):
        """
        GIVEN: main.js
        WHEN:  Aufgaben-Render-Code gesucht wird
        THEN:  Code für loadTasks und Checkbox-Binding existiert
        """
        js = (Path(__file__).parent.parent / "app" / "src" / "main.js").read_text()
        
        # Perspektive 1: API-Call
        assert 'fetch(`${API}/tasks`)' in js or "fetch(API + '/tasks')" in js
        
        # Perspektive 2: Render-Funktion
        assert 'renderTasks' in js or 'loadTasks' in js
        
        # Perspektive 3: Checkbox / Status toggle handler
        assert 'toggleTask' in js or 'updateTask' in js or 'status=' in js
