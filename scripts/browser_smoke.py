"""CI browser verification against a task-owned demo server."""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent.parent
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "jobmatch.api:app", "--host", "127.0.0.1", "--port", "8765", "--no-access-log"], cwd=root)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Demo server did not start")
    with sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8765")
        page.locator("#pdf").set_input_files(str(root / "data/sample_resume.pdf"))
        page.locator("#upload").click()
        page.locator("#editor").wait_for(state="visible")
        assert "Python" in page.locator("#skills").input_value()
        page.locator("#save").click()
        page.get_by_role("status").filter(has_text="Profile confirmed").wait_for()
        page.locator("#years").fill("2")
        page.locator("#locations").fill("Karachi, Pakistan")
        page.locator("#search").click()
        page.locator(".match").first.wait_for()
        assert page.locator(".match").count() > 0
        page.get_by_text("View source evidence", exact=True).first.click()
        assert "Résumé page" in page.locator(".match").first.inner_text()
        page.screenshot(path=str(root / "reports/ui-demo.png"), full_page=True)
        page.reload()
        page.locator("#editor").wait_for(state="visible")
        page.locator("#delete").click()
        page.get_by_role("status").filter(has_text="profile deleted").wait_for()
        assert not page.locator("#editor").is_visible()
        assert not errors, errors
        browser.close()
    print("Browser upload, correction, evidence, session recovery and deletion passed")
finally:
    server.terminate()
    server.wait(timeout=10)
