"""
◑ MiMi Nox – Tool Engine (compat shim)
core/tools.py

This file is now a compatibility shim.
All tool implementations have been split into core/tools/ submodules.

Importing from this module still works:
    from core.tools import web_search, execute_tool, get_tool_schemas
"""
from core.tools import *  # noqa: F401, F403
