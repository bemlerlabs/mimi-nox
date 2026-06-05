"""Optional Deck Engine v2 adapter discovery.

The local renderer remains the default. External/open-source presentation
engines can be enabled later without becoming hard runtime dependencies.
"""
from __future__ import annotations

import os
import shutil


def optional_adapter_status() -> dict:
    presenton_url = os.environ.get("MIMI_NOX_PRESENTON_URL", "").strip()
    pptxgenjs_enabled = os.environ.get("MIMI_NOX_ENABLE_PPTXGENJS", "").strip().lower() in {"1", "true", "yes"}
    return {
        "active": "local_engine_v2",
        "hard_dependency": False,
        "adapters": {
            "presenton": {
                "available": bool(presenton_url),
                "configured_by": "MIMI_NOX_PRESENTON_URL" if presenton_url else "",
                "hard_dependency": False,
            },
            "pptxgenjs": {
                "available": bool(pptxgenjs_enabled and shutil.which("node")),
                "configured_by": "MIMI_NOX_ENABLE_PPTXGENJS" if pptxgenjs_enabled else "",
                "hard_dependency": False,
            },
        },
    }
