"""TUI-Screenshot: Black-Forest-Theme als SVG generieren (visuelle Evidenz).

Rendert die MiMiNoxApp im Headless-Test-Modus und speichert den
export_screenshot()-SVG ab. Die SVG wird anschließend per Browser
gerastert (PNG) für die Evidenz.
"""
import asyncio
from pathlib import Path

OUT = Path("/Users/sanji/mimi-nox/docs/media/tui-black-forest.svg")


async def main():
    from ui.app import MiMiNoxApp
    from ui.widgets import ChatView
    from core.engine_config import default_engine_choice

    # Echte Engine-Auswahl (Qwen/DGX-Default) — exakt wie im echten Start.
    choice = default_engine_choice()
    print("Engine:", choice.provider, choice.model, choice.api_url)
    app = MiMiNoxApp(model=choice.model, api_url=choice.api_url)
    async with app.run_test() as pilot:
        await pilot.pause(2.0)  # Echter DGX-Health-Check + Render

        chat = app.query_one("#chat-view", ChatView)
        chat.post_message(ChatView.AddUserMessage("Wie geht's?"))
        chat.post_message(ChatView.BeginAssistantMessage())
        chat.post_message(ChatView.AppendChunk("Alles top! Ready für deinen Sprint. "))
        chat.post_message(ChatView.FinalizeAssistantMessage())
        await pilot.pause(0.7)

        svg = app.export_screenshot(title="MiMi Nox — Black Forest")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(svg, encoding="utf-8")
        print(f"SVG gespeichert: {OUT} ({len(svg)} chars)")


asyncio.run(main())
