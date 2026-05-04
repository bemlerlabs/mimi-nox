"""
Task Manager — GWT, 3× Tiefe.

GIVEN: Das Task-System
WHEN:  Aufgaben erstellt, gelesen, markiert, gelöscht werden (CRUD)
THEN:  Die Änderungen werden als JSON persistiert und korrekt geladen

GIVEN: Das Tooling-System
WHEN:  Das manage_tasks Tool aufgerufen wird
THEN:  Das Tool verarbeitet die Aktion richtig und gibt Feedback an das LLM

GIVEN: Ein laufendes Chat-System
WHEN:  Ein Nutzer eine Aufgabe im Text formuliert
THEN:  Der Task wird im Hintergrund per Tool hinzugefügt
"""
import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

# ── Blickwinkel 1: Unit-Ebene — TaskManager CRUD ──────────────────────────────

class TestTaskManagerUnitPerspective:
    """GIVEN TaskManager, WHEN CRUD operations performed, THEN JSON is updated correctly."""

    @pytest.fixture
    def temp_tasks_file(self, tmp_path):
        return tmp_path / "tasks.json"

    def test_given_manager_when_add_task_then_saved_to_json(self, temp_tasks_file):
        """
        GIVEN: Ein frischer TaskManager
        WHEN:  Eine Aufgabe hinzugefügt wird
        THEN:  Die Aufgabe landet mit status 'open' in der JSON Datei
        """
        from core.tasks import TaskManager
        
        manager = TaskManager(storage_path=temp_tasks_file)
        task_id = manager.add_task("Milch einkaufen", project="Privat")
        
        # Perspektive 1: ID wird zurückgegeben
        assert task_id is not None
        
        # Perspektive 2: Im RAM vorhanden
        tasks = manager.get_tasks()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Milch einkaufen"
        assert tasks[0]["status"] == "open"
        assert tasks[0]["project"] == "Privat"
        
        # Perspektive 3: In Datei persistiert
        saved_data = json.loads(temp_tasks_file.read_text())
        assert len(saved_data) == 1
        assert saved_data[0]["id"] == task_id

    def test_given_manager_when_complete_task_then_status_done(self, temp_tasks_file):
        """
        GIVEN: Ein TaskManager mit einer offenen Aufgabe
        WHEN:  Die Aufgabe abgeschlossen wird
        THEN:  Der Status ändert sich auf 'done'
        """
        from core.tasks import TaskManager
        
        manager = TaskManager(storage_path=temp_tasks_file)
        task_id = manager.add_task("Wäsche waschen")
        
        manager.update_task(task_id, status="done")
        
        tasks = manager.get_tasks()
        assert tasks[0]["status"] == "done"

    def test_given_manager_when_delete_task_then_removed(self, temp_tasks_file):
        """
        GIVEN: Ein TaskManager mit Aufgaben
        WHEN:  Eine Aufgabe gelöscht wird
        THEN:  Sie verschwindet aus Liste und Datei
        """
        from core.tasks import TaskManager
        
        manager = TaskManager(storage_path=temp_tasks_file)
        task_id = manager.add_task("Lösch mich")
        assert len(manager.get_tasks()) == 1
        
        manager.delete_task(task_id)
        assert len(manager.get_tasks()) == 0


# ── Blickwinkel 2: Integrationsebene — Tool Calling ──────────────────────────

class TestTaskToolIntegrationPerspective:
    """GIVEN manage_tasks tool, WHEN called by LLM, THEN routes to TaskManager."""

    @pytest.fixture
    def mock_manager(self):
        with patch("core.tasks.task_manager") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_given_tool_schema_when_checked_then_manage_tasks_exists(self):
        """
        GIVEN: Die Tool-Definitionen
        WHEN:  Nach manage_tasks gesucht wird
        THEN:  Es existiert mit korrekten Parametern (action, title, task_id)
        """
        from core.tools import get_tool_schemas
        
        task_tool = next((t for t in get_tool_schemas() if t["function"]["name"] == "manage_tasks"), None)
        assert task_tool is not None, "THEN: manage_tasks muss als Tool registriert sein"
        
        props = task_tool["function"]["parameters"]["properties"]
        assert "action" in props
        assert "title" in props
        assert "task_id" in props

    @pytest.mark.asyncio
    async def test_given_tool_when_add_action_then_manager_add_called(self, mock_manager):
        """
        GIVEN: Das execute_tool System
        WHEN:  manage_tasks mit action='add' aufgerufen wird
        THEN:  task_manager.add_task wird ausgeführt
        """
        from core.tools import execute_tool
        
        mock_manager.add_task.return_value = "task-123"
        
        res = await execute_tool("manage_tasks", {"action": "add", "title": "Brot kaufen"})
        
        mock_manager.add_task.assert_called_once_with(title="Brot kaufen", project=None)
        assert "erfolgreich" in res.lower()
        assert "task-123" in res


# ── Blickwinkel 3: Systemebene — Initialisierung ─────────────────────────────

class TestTaskSystemPerspective:
    """GIVEN the application startup, WHEN initialized, THEN tasks are loaded from disk."""

    def test_given_app_startup_when_tasks_json_exists_then_loaded(self, tmp_path):
        """
        GIVEN: Eine tasks.json existiert im appDataDir
        WHEN:  Der globale TaskManager geladen wird
        THEN:  Die Aufgaben stehen sofort zur Verfügung
        """
        from core.tasks import TaskManager
        
        tasks_file = tmp_path / "tasks.json"
        tasks_file.write_text(json.dumps([{"id": "t1", "title": "Alt-Task", "status": "open", "project": None}]))
        
        manager = TaskManager(storage_path=tasks_file)
        tasks = manager.get_tasks()
        
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Alt-Task"
