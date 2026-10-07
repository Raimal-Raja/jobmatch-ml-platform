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
