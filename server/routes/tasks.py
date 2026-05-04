from fastapi import APIRouter
from core.tasks import task_manager

router = APIRouter()

@router.get("/tasks", tags=["Tasks"])
async def get_tasks():
    """Gibt alle Aufgaben aus dem lokalen JSON zurück."""
    return task_manager.get_tasks()

@router.put("/tasks/{task_id}", tags=["Tasks"])
async def update_task(task_id: str, payload: dict):
    """Aktualisiert einen Task via API."""
    status = payload.get("status")
    title = payload.get("title")
    project = payload.get("project")
    found = task_manager.update_task(task_id, status=status, title=title, project=project)
    return {"success": found}

@router.delete("/tasks/{task_id}", tags=["Tasks"])
async def delete_task(task_id: str):
    """Löscht einen Task via API."""
    found = task_manager.delete_task(task_id)
    return {"success": found}
