"""The README's screen images under docs/readme/: the PR-03 SPC terminal screen and the PR-03 press monitor screen, each
from its title bar to the end of its chart panels.

Usage: python -m analytics.readme_image
Each page is rendered at 1600 px wide with Playwright in the installed Edge or Chrome, or in Playwright's own Chromium
where neither is installed; where no browser is available the committed images are left as they are. The images are not
part of the build, since a browser's rendering is not byte-stable across machines."""
from playwright.sync_api import sync_playwright

from analytics.style.style import DOCS

WIDTH = 1600
SHOTS = [(DOCS / "screens" / "spc_terminal_pr_03.html", DOCS / "readme" / "spc_terminal_screen.png"),
         (DOCS / "screens" / "press_monitor_pr_03.html", DOCS / "readme" / "press_monitor_screen.png")]


def main():
    (DOCS / "readme").mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = None
        for channel in ("msedge", "chrome", None):
            try:
                browser = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
                break
            except Exception:
                continue
        if browser is None:
            print("no browser available; the images under docs/readme/ left as committed")
            return
        for page_path, out in SHOTS:
            page = browser.new_page(viewport={"width": WIDTH, "height": 900}, device_scale_factor=1)
            page.goto(page_path.as_uri())
            page.wait_for_load_state("networkidle")
            # the chart panels end where the screen's second grid (the lower panel row) begins
            height = int(page.evaluate("Math.ceil(document.querySelectorAll('.grid')[1].getBoundingClientRect().top + window.scrollY)"))
            page.screenshot(path=str(out), full_page=True, clip={"x": 0, "y": 0, "width": WIDTH, "height": height})
            page.close()
            print(f"wrote {out.relative_to(DOCS.parent).as_posix()} ({WIDTH} x {height})")
        browser.close()


if __name__ == "__main__":
    main()
