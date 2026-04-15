"""
◑ MiMi Nox – Memory Utils (Bridge Helper)
core/memory_utils.py
"""
from core.memory import Memory

_instances = {}

def _get_memory(collection_name: str = "mimi_nox_memory") -> Memory:
    if collection_name not in _instances:
        _instances[collection_name] = Memory(collection_name=collection_name)
    return _instances[collection_name]

def store(text: str, metadata: dict = None, collection: str = "mimi_nox_memory"):
    mem = _get_memory(collection)
    mem.store(text, metadata)
    return {"status": "ok", "id": "stored"}

def search(query: str, top_k: int = 5, collection: str = "mimi_nox_memory"):
    mem = _get_memory(collection)
    return mem.search(query, top_k=top_k)

def count(collection: str = "mimi_nox_memory"):
    mem = _get_memory(collection)
    return {"count": mem.count()}

def clear(collection: str = "mimi_nox_memory"):
    mem = _get_memory(collection)
    mem.clear()
    return {"status": "cleared"}

def get_context_injection(query: str, max_entries: int = 10, collection: str = "mimi_nox_memory"):
    mem = _get_memory(collection)
    return mem.get_context_injection(query, max_entries)
