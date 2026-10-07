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
        recording = "--record-demo" in sys.argv
        options = {"viewport": {"width": 1400, "height": 1000}}
        if recording:
            options["record_video_dir"] = str(root / "reports/demo")
            options["record_video_size"] = {"width": 1400, "height": 1000}
        context = browser.new_context(**options)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8765")
        began = time.monotonic()
        def moment(seconds, message):
            if recording:
                delay = seconds - (time.monotonic() - began)
                if delay > 0:
                    time.sleep(delay)
                page.evaluate("message => { let node = document.getElementById('demo-caption'); if (!node) { node = document.createElement('div'); node.id = 'demo-caption'; Object.assign(node.style, {position:'fixed',bottom:'16px',right:'16px',maxWidth:'600px',padding:'18px',background:'#172b2a',color:'white',borderRadius:'10px',fontFamily:'Arial',fontSize:'18px',zIndex:'1000'}); document.body.append(node); } node.textContent = message; }", message)
        moment(0, "JobMatch: find relevant roles, then inspect evidence and gaps. This demonstration uses fictional data.")
        moment(12, "Upload a text PDF. Extracted mentions are drafts, never assumed qualifications.")
        page.locator("#pdf").set_input_files(str(root / "data/sample_resume.pdf"))
        page.locator("#upload").click()
        page.locator("#editor").wait_for(state="visible")
        assert "Python" in page.locator("#skills").input_value()
        moment(28, "Review and correct skills, experience and education. Source page text remains available.")
        page.locator("#save").click()
        page.get_by_role("status").filter(has_text="Profile confirmed").wait_for()
        moment(42, "Confirm the profile. Only confirmed fields contribute to profile search.")
        page.locator("#years").fill("2")
        page.locator("#locations").fill("Karachi, Pakistan")
        moment(54, "Supply experience and allowed locations explicitly. Unknown preferences stay unknown.")
        page.locator("#search").click()
        page.locator(".match").first.wait_for()
        assert page.locator(".match").count() > 0
        moment(68, "Matches combine ranking signals with explicit constraints. Scores are not hiring probabilities.")
        page.get_by_text("View source evidence", exact=True).first.click()
        assert "Résumé page" in page.locator(".match").first.inner_text()
        moment(82, "Inspect exact quotations from the résumé and job. Required and preferred skills are separate.")
        page.screenshot(path=str(root / "reports/ui-demo.png"), full_page=True)
        moment(96, "Learning priorities address requirements not evidenced in the profile. Study cannot replace required work experience.")
        page.reload()
        page.locator("#editor").wait_for(state="visible")
        moment(108, "Refresh recovers the saved profile. Delete removes the stored PDF and profile; the original file is preserved.")
        page.locator("#delete").click()
        page.get_by_role("status").filter(has_text="profile deleted").wait_for()
        assert not page.locator("#editor").is_visible()
        assert not errors, errors
        moment(116, "Three models are benchmarked honestly: reranking did not beat embeddings on the tiny provisional fixture. Human label review and public release remain pending.")
        if recording:
            time.sleep(max(0, 120 - (time.monotonic() - began)))
        video = page.video
        context.close()
        if recording:
            video.save_as(str(root / "reports/two-minute-demo.webm"))
        browser.close()
    print("Browser upload, correction, evidence, session recovery and deletion passed")
finally:
    server.terminate()
    server.wait(timeout=10)
