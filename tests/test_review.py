import tempfile
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
