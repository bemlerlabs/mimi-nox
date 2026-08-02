"""MiMi Nox – manage_tasks tool."""

from __future__ import annotations


async def manage_tasks(action: str, title: str = None, task_id: str = None, status: str = None, project: str = None) -> str:
    from core.tasks import task_manager

    if action == "add":
        if not title:
            return "[Error: title required for add]"
        tid = task_manager.add_task(title=title, project=project)
        return f"Task erfolgreich hinzugefügt. ID: {tid}"
    elif action == "update":
        if not task_id:
            return "[Error: task_id required for update]"
        found = task_manager.update_task(task_id, status=status, title=title, project=project)
        return f"Task {task_id} erfolgreich aktualisiert." if found else f"[Error: Task {task_id} nicht gefunden]"
    elif action == "delete":
        if not task_id:
            return "[Error: task_id required for delete]"
        found = task_manager.delete_task(task_id)
        return f"Task {task_id} erfolgreich gelöscht." if found else f"[Error: Task {task_id} nicht gefunden]"
    elif action == "list":
        tasks = task_manager.get_tasks()
        if not tasks:
            return "Keine Aufgaben vorhanden."
        return "\n".join(f"- [{t['status']}] {t['title']} (ID: {t['id']})" for t in tasks)
    return f"[Error: unknown action '{action}']"
