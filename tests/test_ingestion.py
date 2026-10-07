import json
import tempfile
import unittest
from pathlib import Path
from jobmatch.ingestion import ingest
from jobmatch.retrieval import ROOT, load_jobs


class IngestionTests(unittest.TestCase):
    def test_provenance_preserved_and_input_unchanged(self):
        source = ROOT / "data/sample_listing_import.json"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "jobs.json"
            result = ingest(source, target)
            self.assertEqual(result["imported"], 1)
            self.assertEqual(load_jobs(target)[0]["provenance"]["kind"], "manual")
        self.assertEqual(source.read_bytes(), original)

    def test_missing_permission_and_near_duplicates_rejected(self):
        payload = json.loads((ROOT / "data/sample_listing_import.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            target = Path(directory) / "output.json"
            payload["jobs"].append({**payload["jobs"][0], "id": "duplicate", "description": payload["jobs"][0]["description"] + " Today."})
            source.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "Near-duplicate"):
                ingest(source, target)
            self.assertFalse(target.exists())
            payload["provenance"].pop("permission")
            source.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                ingest(source, target)
