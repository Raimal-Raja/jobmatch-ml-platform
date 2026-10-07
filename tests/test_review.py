import tempfile
import csv
import json
import unittest
from pathlib import Path
from jobmatch.review import export_review, apply_review


class ReviewTests(unittest.TestCase):
    def test_blank_worksheet_cannot_be_presented_as_reviewed(self):
        jobs = [{"id": "j", "description": "Required: Python"}]
        fixture = {"profiles": [{"id": "p", "text": "Python experience"}]}
        with tempfile.TemporaryDirectory() as directory:
            worksheet = Path(directory) / "review.csv"
            target = Path(directory) / "reviewed.json"
            export_review(jobs, fixture, worksheet)
            with self.assertRaisesRegex(ValueError, "Every pair"):
                apply_review(jobs, fixture, worksheet, target)
            self.assertFalse(target.exists())

    def test_complete_review_keeps_sources_and_rejects_invented_quotes(self):
        jobs = [{"id": "j", "description": "Required: Python"}]
        fixture = {"profiles": [{"id": "p", "text": "Python experience"}]}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "review.csv"
            target = Path(directory) / "reviewed.json"
            row = {"profile_id": "p", "job_id": "j", "grade": "3", "reviewer": "Test reviewer",
                   "rationale": "Test case", "resume_quote": "Invented qualification", "job_quote": "Python"}
            def write():
                with source.open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(row))
                    writer.writeheader()
                    writer.writerow(row)
            write()
            with self.assertRaisesRegex(ValueError, "quotations"):
                apply_review(jobs, fixture, source, target)
            row["resume_quote"] = "Python"
            write()
            apply_review(jobs, fixture, source, target)
            result = json.loads(target.read_text())
            self.assertEqual(result["profiles"], fixture["profiles"])
            self.assertEqual(result["judgments"]["p"]["j"], 3)
            self.assertEqual(result["review_status"], "reviewer_declared_human_review")
