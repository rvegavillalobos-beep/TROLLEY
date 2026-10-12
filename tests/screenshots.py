"""Take a screenshot of every tab of a running app (used by CI).

    python tests/screenshots.py http://localhost:8501 screenshots/
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "screenshots")
OUT.mkdir(parents=True, exist_ok=True)

HEIGHT_JS = "() => Math.max(...[...document.querySelectorAll('*')].map(e => e.scrollHeight))"


def settle(page, ms=2500):
    page.wait_for_timeout(ms)
    page.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60_000)


def shoot(page, width, name):
    """Grow the viewport to the content height: Streamlit scrolls inside its own container."""
    h = min(int(page.evaluate(HEIGHT_JS)) + 40, 9000)
    page.set_viewport_size({"width": width, "height": h})
    settle(page, 2000)
    page.screenshot(path=str(OUT / name))
    page.set_viewport_size({"width": width, "height": 1000})
    print("saved", name)


with sync_playwright() as p:
    browser = p.chromium.launch()
    logs = []
    for width, tag in ((1440, "desktop"), (820, "tablet")):
        page = browser.new_page(viewport={"width": width, "height": 1000}, device_scale_factor=1)
        page.on("console", lambda m: logs.append(f"{tag} {m.type}: {m.text}"))
        page.on("pageerror", lambda e: logs.append(f"{tag} pageerror: {e}"))
        page.goto(URL, wait_until="networkidle")
        page.get_by_text("Conveyor defect tracker").first.wait_for(timeout=90_000)
        page.wait_for_selector(".js-plotly-plot", timeout=90_000)
        settle(page, 4000)
        tabs = page.get_by_role("tab")
        n = tabs.count()
        for i in range(n if tag == "desktop" else 1):
            tab = tabs.nth(i)
            name = tab.inner_text().split("(")[0].strip().lower().replace(" ", "-")
            tab.click()
            settle(page)
            shoot(page, width, f"{tag}-{i + 1}-{name}.png")
        if tag == "desktop":
            # click one square on the line map: the selection should list it below the map
            tabs.nth(0).click()
            settle(page)
            pts = page.locator(".st-key-linemap .js-plotly-plot .scatterlayer .trace .points path")
            logs.append(f"line map points: {pts.count()}")
            if pts.count():
                # drag a selection box across the middle of the map; the picked defects get listed below it
                plot = page.locator(".st-key-linemap .js-plotly-plot .nsewdrag").first.bounding_box()
                page.mouse.move(plot["x"] + plot["width"] * 0.45, plot["y"] + 10)
                page.mouse.down()
                page.mouse.move(plot["x"] + plot["width"] * 0.62, plot["y"] + plot["height"] * 0.8, steps=12)
                page.mouse.up()
                settle(page, 3500)
                logs.append(f"after drag: nothing-selected={page.get_by_text('Nothing selected yet').count()}")
                shoot(page, width, "desktop-1b-overview-selected.png")
        page.close()
    (OUT / "console.txt").write_text("\n".join(logs))
    browser.close()
