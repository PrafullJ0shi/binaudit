"""Render the README banner (light and dark) and app screenshots with Playwright.

Usage: python scripts/render_assets.py   (needs `pip install playwright` and `playwright install chromium`)
Serves web/ on a local port, loads the synthetic sample, and writes PNGs to docs/assets/.
"""

import asyncio
import functools
import http.server
import threading
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"


def serve() -> int:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "web"))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd.server_address[1]


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    port = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for scheme in ("light", "dark"):
            pg = await b.new_page(viewport={"width": 1280, "height": 320}, device_scale_factor=2)
            await pg.goto((ROOT / "scripts" / "banner.html").as_uri() + ("#dark" if scheme == "dark" else ""))
            await pg.wait_for_timeout(300)
            await pg.screenshot(path=OUT / f"banner-{scheme}.png")
            pg = await b.new_page(viewport={"width": 1040, "height": 800}, color_scheme=scheme)
            await pg.goto(f"http://127.0.0.1:{port}/index.html")
            await pg.wait_for_timeout(1200)
            for sec in ("results", "signs"):
                await pg.goto(f"http://127.0.0.1:{port}/index.html#{sec}")
                await pg.wait_for_timeout(400)
                await pg.screenshot(path=OUT / f"{sec}-{scheme}.png", full_page=True)
        pg = await b.new_page(viewport={"width": 1040, "height": 800})
        await pg.goto(f"http://127.0.0.1:{port}/index.html#log")
        await pg.wait_for_timeout(800)
        await pg.fill("#f-site", "Hostel A, floor 2")
        await pg.select_option("#f-bin", "dry")
        await pg.fill("#f-phase", "after sign")
        for item, n in (("newspaper", 6), ("plastic bottle", 4), ("tea leaves", 2), ("battery", 1)):
            await pg.fill("#f-item", item)
            await pg.dispatch_event("#f-item", "input")
            await pg.fill("#f-count", str(n))
            await pg.click("#item-form button")
        await pg.fill("#f-item", "milk pouch")
        await pg.dispatch_event("#f-item", "input")
        await pg.screenshot(path=OUT / "log-light.png", full_page=True)
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
