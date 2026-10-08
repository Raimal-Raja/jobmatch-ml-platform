import importlib.util
import tempfile
import unittest
from pathlib import Path
from scripts.create_sample_resume import sample_pdf


@unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx") and importlib.util.find_spec("pypdf"), "Install .[web,resume]")
class ApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from jobmatch.api import create_app
        from jobmatch.profiles import ProfileStore
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ProfileStore(Path(self.temporary.name) / "profiles")
        self.client = TestClient(create_app(self.store))

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def test_complete_upload_edit_evidence_search_delete_flow(self):
        response = self.client.post("/profiles", content=sample_pdf(), headers={"Content-Type": "application/pdf"})
        self.assertEqual(response.status_code, 200)
        profile_id = response.json()["id"]
        self.assertEqual(self.client.post("/search", json={"profile_id": profile_id}).status_code, 400)
        corrections = {"skills": ["Python", "Django", "PostgreSQL"], "experience": ["Backend Developer"], "education": []}
        self.assertEqual(self.client.put(f"/profiles/{profile_id}", json=corrections).status_code, 200)
        result = self.client.post("/search", json={"profile_id": profile_id, "context": {"skills": ["Kubernetes"], "experience_years": 2}})
        self.assertEqual(result.status_code, 200)
        python = next(item for item in result.json()["results"][0]["assessment"]["required"] if item["skill"] == "Python")
        self.assertEqual(python["status"], "supported")
        self.assertTrue(python["resume_evidence"][0]["evidence"]["quote"])
        self.assertEqual(self.client.delete(f"/profiles/{profile_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/profiles/{profile_id}").status_code, 404)
        self.assertFalse((self.store.root / profile_id).exists())

    def test_validation_origin_and_no_store(self):
        self.assertEqual(self.client.post("/profiles", content=b"not a PDF").status_code, 400)
        self.assertEqual(self.client.post("/search", json={"query": "Python", "limit": 0}).status_code, 422)
        self.assertEqual(self.client.post("/search", json={"query": "Python", "context": {"experience_years": -1}}).status_code, 400)
        self.assertEqual(self.client.post("/search", json={"query": "Python"}, headers={"Origin": "https://unrelated.example"}).status_code, 403)
        self.assertEqual(self.client.get("/health", headers={"Host": "unrelated.example"}).status_code, 400)
        self.assertEqual(self.client.get("/health").headers["Cache-Control"], "no-store")
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/assets/app.js").status_code, 200)

    def test_health_reports_missing_model_dependencies(self):
        from unittest.mock import patch
        with patch("jobmatch.api.find_spec", return_value=None):
            modes = self.client.get("/health").json()["search_modes"]
        self.assertEqual(modes, {"tfidf": True, "semantic": False, "reranked": False})

    def test_loading_semantic_model_does_not_block_keyword_search(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from unittest.mock import patch
        from jobmatch.retrieval import TfidfRetriever
        loading, release = Event(), Event()

        def make(jobs, approach):
            if approach == "semantic":
                loading.set()
                if not release.wait(5):
                    raise RuntimeError("Test model load was not released")
            return TfidfRetriever(jobs)

        with patch("jobmatch.api.make_retriever", side_effect=make), ThreadPoolExecutor(max_workers=2) as pool:
            semantic = pool.submit(self.client.post, "/search", json={"query": "Python", "approach": "semantic"})
            try:
                self.assertTrue(loading.wait(2))
                keyword = pool.submit(self.client.post, "/search", json={"query": "Python"})
                self.assertEqual(keyword.result(timeout=2).status_code, 200)
            finally:
                release.set()
            self.assertEqual(semantic.result(timeout=2).status_code, 200)

    def test_failed_model_download_returns_actionable_json(self):
        from unittest.mock import patch
        from jobmatch.retrieval import TfidfRetriever

        def make(jobs, approach):
            if approach == "semantic":
                raise RuntimeError("Interrupted model download")
            return TfidfRetriever(jobs)

        with patch("jobmatch.api.make_retriever", side_effect=make):
            failed = self.client.post("/search", json={"query": "Python", "approach": "semantic"})
            self.assertEqual(failed.status_code, 503)
            self.assertIn("keyword search remains available", failed.json()["detail"])
            self.assertEqual(self.client.post("/search", json={"query": "Python"}).status_code, 200)

    def test_compare_selected_job_and_prepare_week(self):
        uploaded = self.client.post('/profiles', content=sample_pdf()).json()
        listing = {'title': 'Selected Python Job', 'company': 'Example Company',
                   'description': 'Minimum qualifications\nPython and SQL\nPreferred qualifications\nRedis',
                   'source_url': 'https://example.com/selected-job'}
        body = {'profile_id': uploaded['id'], 'listing': listing, 'minutes_per_day': 60}
        self.assertEqual(self.client.post('/compare-target', json=body).status_code, 400)
        self.client.put('/profiles/' + uploaded['id'], json={'skills': ['Python'], 'experience': [], 'education': []})
        response = self.client.post('/compare-target', json=body)
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report['listing'], {**listing, 'location': '', 'work_mode': ''})
        self.assertEqual(report['recognized_required_skills'], 2)
        self.assertEqual(report['required_skills_supported'], 1)
        self.assertEqual(len(report['interview_plan']['days']), 7)
        self.assertEqual(self.client.get('/health').json()['jobs'], 12)
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_partially_confirmed_profile_cannot_silently_search(self):
        uploaded = self.client.post('/profiles', content=sample_pdf()).json()
        partial = self.store.update(uploaded['id'], {'skills': ['Python']})
        self.assertFalse(partial['reviewed'])
        response = self.client.post('/search', json={'profile_id': uploaded['id']})
        self.assertEqual(response.status_code, 400)
        self.assertIn('confirm', response.json()['detail'])

    def test_readiness_and_reviewed_word_export(self):
        from io import BytesIO
        import zipfile
        uploaded = self.client.post('/profiles', content=sample_pdf()).json()
        profile_id = uploaded['id']
        check = self.client.get(f'/profiles/{profile_id}/ats-check')
        self.assertEqual(check.status_code, 200)
        self.assertIn('score', check.json())
        self.assertEqual(self.client.get(f'/profiles/{profile_id}/rewrite').status_code, 400)
        self.client.put(f'/profiles/{profile_id}', json={'skills': ['Python'], 'experience': ['Developer'], 'education': []})
        draft = self.client.get(f'/profiles/{profile_id}/rewrite').json()
        export = self.client.post(f'/profiles/{profile_id}/rewrite-export', json={'text': draft['text']})
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.headers['Cache-Control'], 'no-store')
        with zipfile.ZipFile(BytesIO(export.content)) as archive:
            self.assertIn('word/document.xml', archive.namelist())

    def test_discovery_needs_no_resume_and_does_not_forward_resume_fields(self):
        from fastapi.testclient import TestClient
        from jobmatch.api import create_app
        from jobmatch.discovery import JobDiscovery
        fetches = []
        def fetch(url):
            fetches.append(url)
            return {'jobs': [{'title': 'Python Developer', 'company_name': 'Example', 'description': '<p>Required: Python</p>',
                              'url': 'https://remotive.com/remote-jobs/example', 'candidate_required_location': 'Worldwide'}]}
        with TestClient(create_app(self.store, discovery=JobDiscovery(Path(self.temporary.name) / 'cache', fetch))) as client:
            result = client.post('/discover-jobs', json={'role': 'Python', 'provider': 'remotive'})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(len(result.json()['jobs']), 1)
            self.assertEqual(client.post('/discover-jobs', json={'role': 'Python', 'resume_text': 'private'}).status_code, 422)
        self.assertEqual(fetches, ['https://remotive.com/api/remote-jobs?limit=500'])

    def test_automatic_company_search_previews_gaps_without_forwarding_resume(self):
        from unittest.mock import patch
        import os
        uploaded = self.client.post('/profiles', content=sample_pdf()).json()
        self.client.put('/profiles/' + uploaded['id'], json={'skills': ['Python'], 'experience': [], 'education': []})
        candidate = {'title': 'Python Developer', 'company': 'Google', 'description': 'Required: Python and SQL',
                     'source_url': 'https://example.com/fictional-job', 'location': 'Karachi', 'work_mode': '', 'notes': []}
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'fictional-test-key'}), patch('jobmatch.google_jobs.search_google', return_value={'jobs': [candidate], 'status': 'found'}) as search:
            result = self.client.post('/discover-jobs', json={'role': 'Python Developer', 'company': 'Google', 'profile_id': uploaded['id']})
            self.assertEqual(result.status_code, 200)
            preview = result.json()['jobs'][0]['match_preview']
            self.assertIn('Python', preview['supported'])
            self.assertIn('SQL', preview['not_evidenced'])
            self.assertNotIn('profile_id', search.call_args.args[0])
            self.assertNotIn('resume', str(search.call_args))

    def test_session_configuration_returns_status_only(self):
        from unittest.mock import patch
        import os
        with patch.dict(os.environ, {'NVIDIA_API_KEY': '', 'SERPAPI_API_KEY': ''}):
            result = self.client.post('/integrations', json={'nvidia_key': 'fictional-test-key'})
            self.assertEqual(result.status_code, 200)
            self.assertTrue(self.client.get('/health').json()['integrations']['nvidia'])
            self.assertNotIn('fictional-test-key', result.text)
            self.assertEqual(self.client.post('/integrations', json={'search_key': 'bad key'}).status_code, 400)
            self.assertEqual(self.client.post('/integrations', json={'nvidia_key': 'another-key'}, headers={'Origin': 'https://example.com'}).status_code, 403)
