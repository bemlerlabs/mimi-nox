"""server/routes/feedback.py – POST /api/feedback/thumbs_up + thumbs_down

PDCA #4: thumbs_down schreibt jetzt auch in CorrectionJournal →
negativer Feedback-Loop ist geschlossen.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from core.feedback import FeedbackStore
from core.corrections import CorrectionJournal

router = APIRouter(tags=["Feedback"])


def _get_store() -> FeedbackStore:
    """FeedbackStore mit konfiguriertem Basispfad (testbar via ENV)."""
    base = os.environ.get("MIMI_NOX_FEEDBACK_DIR")
    return FeedbackStore(base_dir=Path(base)) if base else FeedbackStore()


def _get_journal() -> CorrectionJournal:
    """CorrectionJournal für negativen Feedback-Loop."""
    return CorrectionJournal()


# ── Pydantic Models ────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    prompt: str
    response: str
    reason: Optional[str] = None   # z.B. "Zu lang", "Falsch", "Nicht hilfreich"


class FeedbackResponse(BaseModel):
    saved: bool


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/feedback/thumbs_up", response_model=FeedbackResponse)
async def thumbs_up(request: FeedbackRequest) -> FeedbackResponse:
    """Speichert ein positives Feedback-Beispiel (👍).
    Wird bei jedem Chat-Call als Few-Shot-Kontext injiziert.
    """
    store = _get_store()
    store.thumbs_up(prompt=request.prompt, response=request.response)
    return FeedbackResponse(saved=True)


@router.post("/feedback/thumbs_down", response_model=FeedbackResponse)
async def thumbs_down(request: FeedbackRequest) -> FeedbackResponse:
    """Speichert ein negatives Feedback-Beispiel (👎).

    PDCA #4: Schließt den negativen Feedback-Loop:
      1. FeedbackStore.thumbs_down() → bad_examples/ (bestehend)
      2. NEU: CorrectionJournal.add() → wird beim nächsten Chat in
         den System-Prompt injiziert → MiMi verbessert sich
    """
    store = _get_store()
    store.thumbs_down(prompt=request.prompt, response=request.response)

    # Negativen Loop schließen: reason → CorrectionJournal
    if request.reason:
        try:
            journal = _get_journal()
            correction_text = f"Vermeide bei ähnlichen Anfragen: {request.reason}"
            journal.add(
                context=request.prompt[:200],
                correction=correction_text,
            )
        except Exception:
            pass  # Fail-safe: Feedback trotzdem gespeichert, auch wenn Journal fehlschlägt

    return FeedbackResponse(saved=True)
