"""MiMi Nox – Browser and vision tools."""

from __future__ import annotations

import base64 as base64_mod
import os
import time
from pathlib import Path


def _get_vision_click():
    from core.vision import vision_click
    return vision_click


def _get_vision_type():
    from core.vision import vision_type
    return vision_type


async def _vision_click_wrapper(target_description: str) -> str:
    fn = _get_vision_click()
    return await fn(target_description)


async def _vision_type_wrapper(text: str, press_enter: bool = False) -> str:
    fn = _get_vision_type()
    return await fn(text, press_enter)


vision_click = _vision_click_wrapper
vision_type = _vision_type_wrapper


def _get_browser_manager():
    from core.browser import browser_manager
    return browser_manager


async def browser_go(url: str) -> str:
    bm = _get_browser_manager()
    return await bm.go(url)


async def browser_screenshot() -> str:
    bm = _get_browser_manager()
    b64 = await bm.screenshot()
    image_dir = Path(os.environ.get("MIMI_NOX_IMAGE_DIR", str(Path.home() / ".mimi-nox" / "sessions" / "images")))
    image_dir.mkdir(parents=True, exist_ok=True)
    filename = f"browser_{int(time.time())}.jpeg"
    with open(image_dir / filename, "wb") as f:
        f.write(base64_mod.b64decode(b64))
    return f"Browser Screenshot aufgenommen:\n\n![Browser](/images/{filename})"


async def browser_click(target_description: str) -> str:
    bm = _get_browser_manager()
    return await bm.click(target_description)


async def browser_type(text: str) -> str:
    bm = _get_browser_manager()
    return await bm.type_text(text)


async def browser_press(key: str) -> str:
    bm = _get_browser_manager()
    return await bm.press(key)
