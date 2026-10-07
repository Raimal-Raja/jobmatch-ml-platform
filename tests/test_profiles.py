import importlib.util
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from jobmatch.profiles import ProfileStore, draft_profile, extract_pages
from scripts.create_sample_resume import sample_pdf


class DraftTests(unittest.TestCase):
    def test_employment_in_summary_preserves_wrapped_evidence(self):
        text = "Professional Summary\nBuilds Python apps. Current Data Administrator at ExampleCo and former paid\nPython Developer Intern at SampleCo.\nKey Projects\nBuilt an app.\n"
        profile = draft_profile([{"page": 1, "text": text}])
        self.assertEqual(len(profile["experience"]), 1)
        item = profile["experience"][0]
        self.assertFalse(item["confirmed"])
        self.assertNotIn("\n", item["value"])
        proof = item["evidence"]
        self.assertEqual(text[proof["start"]:proof["end"]], proof["quote"])
        self.assertIn("paid\nPython Developer", proof["quote"])

    def test_combined_education_heading_and_project_boundary(self):
        text = "Professional Summary\nPython developer\nEducation & Certifications\nBS Computing\nKey Projects\nBuilt a Django app\n"
        profile = draft_profile([{"page": 1, "text": text}])
        self.assertEqual([item["value"] for item in profile["education"]], ["BS Computing"])
        self.assertEqual(profile["experience"], [])
        proof = profile["education"][0]["evidence"]
        self.assertEqual(text[proof["start"]:proof["end"]], "BS Computing")

    def test_mentions_are_unconfirmed_and_evidence_is_exact(self):
        text = "Skills\nNo experience with Python\nEducation\nBS Computer Science\n"
        profile = draft_profile([{"page": 1, "text": text}])
        candidate = profile["skills"][0]
        self.assertFalse(candidate["confirmed"])
        evidence = candidate["evidence"]
        self.assertEqual(text[evidence["start"]:evidence["end"]], evidence["quote"])
        self.assertEqual(profile["education"][0]["value"], "BS Computer Science")

    def test_path_traversal_and_bad_corrections_rejected(self):
        store = ProfileStore()
        with self.assertRaises(ValueError):
            store.get("../../README.md")
        with self.assertRaises(ValueError):
            store.update("a" * 32, {"skills": "Python"})
        with self.assertRaises(ValueError):
            store.update("a" * 32, {"id": []})


@unittest.skipUnless(importlib.util.find_spec("pypdf"), "Install .[resume] to test PDF support")
class PdfProfileTests(unittest.TestCase):
    def test_import_correct_search_and_delete_preserves_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original.pdf"
            original.write_bytes(sample_pdf())
            store = ProfileStore(root / "profiles")
            profile = store.create(original)
            profile_id = profile["id"]
            with self.assertRaises(ValueError):
                store.search_text(profile_id)
            corrections = {"skills": ["Python", "Rust"], "experience": [], "education": []}
            updated = store.update(profile_id, corrections)
            self.assertTrue(updated["reviewed"])
            self.assertIsNotNone(updated["skills"][0]["evidence"])
            self.assertIsNone(updated["skills"][1]["evidence"])
            self.assertEqual(updated["skills"][1]["origin"], "user")
            self.assertEqual(store.search_text(profile_id), "Python\nRust")
            self.assertEqual(store.get(profile_id), updated)
            store.delete(profile_id)
            self.assertTrue(original.exists())
            self.assertFalse((store.root / profile_id).exists())

    def test_invalid_blank_encrypted_and_oversized_pdfs(self):
        from pypdf import PdfWriter
        for data in (b"not pdf", b"%PDF-broken", b"%PDF-" + b"x" * (10 * 1024 * 1024)):
            with self.assertRaises(ValueError):
                extract_pages(data)
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buffer = BytesIO()
        writer.write(buffer)
        with self.assertRaisesRegex(ValueError, "no extractable text"):
            extract_pages(buffer.getvalue())
        writer.encrypt("test-password")
        buffer = BytesIO()
        writer.write(buffer)
        with self.assertRaisesRegex(ValueError, "Encrypted"):
            extract_pages(buffer.getvalue())

    def test_page_limit(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        for _ in range(21):
            writer.add_blank_page(width=100, height=100)
        buffer = BytesIO()
        writer.write(buffer)
        with self.assertRaisesRegex(ValueError, "20 page"):
            extract_pages(buffer.getvalue())
