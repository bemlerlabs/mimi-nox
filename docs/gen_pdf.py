#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("file:///Users/sanji/mimi-nox/docs/whitepaper.html", wait_until="networkidle")
        await page.pdf(
            path="/Users/sanji/mimi-nox/docs/whitepaper-mimi-nox.pdf",
            format="A4",
            print_background=True,
            margin={"top": "20mm", "right": "20mm", "bottom": "20mm", "left": "20mm"}
        )
        await browser.close()
    print("PDF generated successfully")

if __name__ == "__main__":
    asyncio.run(main())
