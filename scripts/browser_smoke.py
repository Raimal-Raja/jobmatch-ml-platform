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
        assert page.locator('#compare-target').is_disabled()
        page.locator('.readiness-score').wait_for()
        assert '/100' in page.locator('.readiness-score').inner_text()
        moment(28, "Review and correct skills, experience and education. Source page text remains available.")
        page.locator("#save").click()
        page.locator("#profile-status").filter(has_text="Résumé confirmed").wait_for()
        moment(42, "Confirm the profile. Only confirmed fields contribute to profile search.")
        page.locator('#mode-demo').click()
        page.locator('#mode-target').click()
        page.locator('#manual-listing > summary').click()
        page.locator('#manual-listing details.optional > summary').click()
        page.locator("#years").fill("2")
        page.locator("#locations").fill("Karachi, Pakistan")
        moment(54, "Supply experience and allowed locations explicitly. Unknown preferences stay unknown.")
        page.locator('#mode-demo').click()
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
        page.locator('#target-title').fill('Selected Python Developer')
        page.locator('#target-company').fill('Example Company (fictional)')
        page.locator('#manual-listing > summary').click()
        page.locator('#manual-listing details.optional > summary').click()
        page.locator('#target-url').fill('https://example.com/selected-job')
        page.locator('#target-description').fill('Minimum qualifications\nPython and NovelFramework\nPreferred qualifications\nSQL')
        page.locator('#target-skills').fill('NovelFramework')
        page.locator('#target-minutes').fill('60')
        page.locator('#compare-target').click()
        page.locator('.target-comparison').wait_for()
        assert page.locator('.target-comparison h3').inner_text() == 'Example Company (fictional) · Selected Python Developer'
        assert 'NovelFramework · not evidenced' in page.locator('.target-comparison').inner_text()
        assert page.locator('.day-card').count() == 7
        assert 'not a prediction' in page.locator('.interview-plan').inner_text()
        page.locator('#target-results').screenshot(path=str(root / 'reports/target-job-demo.png'))
        page.locator('#ats-panel > details > summary').click()
        assert page.locator('#prepare-ai').is_disabled()
        page.locator('#integration-status').locator('..').locator('summary').click()
        page.locator('#nvidia-key').fill('fictional-browser-test-key')
        page.locator('#configure-services').click()
        page.locator('#setup-status').filter(has_text='Configured').wait_for()
        assert page.locator('#nvidia-key').input_value() == ''
        page.locator('#ai-consent').check()
        assert page.locator('#prepare-ai').is_enabled()
        page.route('**/ai-rewrite', lambda route: route.fulfill(content_type='application/json', body='{"text":"Fictional Candidate\\nPython", "notice":"Fictional AI test fixture", "review_items":["Review all facts"], "evidence":[{"text":"Python", "source_quote":"Python"}]}'))
        page.locator('#prepare-ai').click()
        page.locator('.ai-evidence').wait_for()
        assert page.locator('#download-rewrite').is_disabled()
        page.locator('#prepare-rewrite').click()
        page.locator('#rewrite-text').wait_for(state='visible')
        assert page.locator('#download-rewrite').is_disabled()
        page.locator('#rewrite-reviewed').check()
        with page.expect_download() as download:
            page.locator('#download-rewrite').click()
        import zipfile
        with zipfile.ZipFile(download.value.path()) as archive:
            assert b'Python' in archive.read('word/document.xml')
        page.locator('#ats-panel > details > summary').click()
        import json
        fixture = {'status': 'found', 'message': '1 fictional test listing found.', 'notice': 'Browser test fixture; not a live vacancy.', 'indeed_url': 'https://www.indeed.com/jobs?q=Python', 'sources': [], 'jobs': [{'title': 'Selected Python Developer', 'company': 'Example Company (fictional)', 'description': 'Minimum qualifications\nPython and NovelFramework', 'source_url': 'https://example.com/selected-job', 'location': 'Worldwide', 'work_mode': 'remote', 'provider': 'Fictional test source', 'provider_home': 'https://example.com', 'notes': []}]}
        page.route('**/discover-jobs', lambda route: route.fulfill(content_type='application/json', body=json.dumps(fixture)))
        page.locator('#target-description').fill('')
        page.locator('#compare-target').click()
        page.locator('#discovery-results button').first.wait_for()
        page.screenshot(path=str(root / 'reports/readiness-discovery-demo.png'), full_page=True)
        page.locator('#discovery-results button').first.click()
        page.locator('.target-comparison').wait_for()
        assert page.locator('.day-card').count() == 7
        google_fixture = {'status': 'setup_required', 'message': 'Google search API setup required.', 'notice': 'No resume sent.', 'google_url': 'https://www.google.com/search?q=Python+jobs', 'sources': [], 'jobs': []}
        page.route('**/discover-jobs', lambda route: route.fulfill(content_type='application/json', body=json.dumps(google_fixture)))
        page.locator('#discovery-provider').select_option('google')
        page.locator('#discover-jobs').click()
        page.locator('#discovery-status').filter(has_text='setup required').wait_for()
        assert page.locator('#discovery-results a').first.get_attribute('href').startswith('https://www.google.com/')
        moment(108, "Refresh recovers the saved profile. Delete removes the stored PDF and profile; the original file is preserved.")
        page.locator("#delete").click()
        page.locator("#profile-status").filter(has_text="profile deleted").wait_for()
        assert not page.locator("#editor").is_visible()
        assert page.locator('#target-results').inner_text() == ''
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
