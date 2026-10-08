"""The image at the top of the README: docs/readme/pr_06_board.png, the PR-06 SPC board from its header to the end of
the per-stroke panel.

Usage: python -m analytics.readme_image
The page is rendered at 1280 px wide with Playwright in the installed Edge or Chrome, or in Playwright's own Chromium
where neither is installed; where no browser is available the committed image is left as it is. The image is not part
of the build, since a browser's rendering is not byte-stable across machines."""
from playwright.sync_api import sync_playwright

from analytics.style.style import DOCS

WIDTH = 1280
PAGE = DOCS / "spc_board" / "pr_06.html"
OUT = DOCS / "readme" / "pr_06_board.png"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = None
        for channel in ("msedge", "chrome", None):
            try:
                browser = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
                break
            except Exception:
                continue
        if browser is None:
            print("no browser available; docs/readme/pr_06_board.png left as committed")
            return
        page = browser.new_page(viewport={"width": WIDTH, "height": 900}, device_scale_factor=1)
        page.goto(PAGE.as_uri())
        page.wait_for_load_state("networkidle")
        height = int(page.evaluate("Math.ceil(document.querySelector('#checks').getBoundingClientRect().top + window.scrollY) - 12"))
        page.screenshot(path=str(OUT), full_page=True, clip={"x": 0, "y": 0, "width": WIDTH, "height": height})
        browser.close()
    print(f"wrote {OUT.relative_to(DOCS.parent).as_posix()} ({WIDTH} x {height})")


if __name__ == "__main__":
    main()
