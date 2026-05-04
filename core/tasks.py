"""
◑ MiMi Nox – Task Manager
core/tasks.py

Verwaltet asynchrone / synchrone Persistierung von User-Tasks in einer JSON-Datei.
"""
import json
import uuid
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

class TaskManager:
    def __init__(self, storage_path: Optional[Path | str] = None):
        if storage_path is None:
            # Fallback path if not provided
            storage_path = Path(os.path.expanduser("~")) / ".miminox" / "tasks.json"
        self.storage_path = Path(storage_path)
        self._ensure_file()
        
    def _ensure_file(self):
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text("[]", encoding="utf-8")

    def _read_tasks(self) -> List[Dict[str, Any]]:
        try:
            content = self.storage_path.read_text(encoding="utf-8")
            return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_tasks(self, tasks: List[Dict[str, Any]]):
        self.storage_path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Liest alle Tasks"""
        return self._read_tasks()

    def add_task(self, title: str, project: Optional[str] = None) -> str:
        """Fügt einen Task hinzu und gibt die neue ID zurück."""
        tasks = self._read_tasks()
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        new_task = {
            "id": task_id,
            "title": title,
            "status": "open",
            "project": project
        }
        tasks.append(new_task)
        self._write_tasks(tasks)
        return task_id

    def update_task(self, task_id: str, status: Optional[str] = None, title: Optional[str] = None, project: Optional[str] = None) -> bool:
        """Aktualisiert einen Task. Return True wenn gefunden und geändert."""
        tasks = self._read_tasks()
        updated = False
        for t in tasks:
            if t["id"] == task_id:
                if status is not None:
                    t["status"] = status
                if title is not None:
                    t["title"] = title
                if project is not None:
                    t["project"] = project
                updated = True
                break
        if updated:
            self._write_tasks(tasks)
        return updated

    def delete_task(self, task_id: str) -> bool:
        """Löscht einen Task. Return True wenn gefunden und gelöscht."""
        tasks = self._read_tasks()
        new_tasks = [t for t in tasks if t["id"] != task_id]
        if len(new_tasks) < len(tasks):
            self._write_tasks(new_tasks)
            return True
        return False

# Globaler, importierbarer Manager
task_manager = TaskManager()
