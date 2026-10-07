import unittest
from jobmatch.constraints import assess, apply_constraints, requirements
from jobmatch.retrieval import load_jobs, TfidfRetriever


class ConstraintTests(unittest.TestCase):
    def test_required_and_preferred_stay_separate_with_exact_evidence(self):
        job = load_jobs()[0]
        result = assess(job, {"skills": ["Docker"]})
        self.assertTrue(all(item["status"] == "not_evidenced" for item in result["required"]))
        self.assertEqual(result["preferred"][0]["status"], "supported")
        for item in result["required"] + result["preferred"]:
            e = item["evidence"]
            self.assertEqual(job["description"][e["start"]:e["end"]], e["quote"])

    def test_range_minimum_and_unknown_context(self):
        job = load_jobs()[1]
        self.assertEqual(requirements(job)["minimum_years"], 0)
        result = assess(job, {})
        self.assertFalse(result["conflicts"])
        self.assertIsNone(result["required_coverage"])
        self.assertTrue(all(item["status"] == "unknown" for item in result["required"]))

    def test_explicit_conflicts_demote_senior_job(self):
        jobs = load_jobs()
        results = TfidfRetriever(jobs).search("Python Django PostgreSQL", 12)
        ordered = apply_constraints(results, {"experience_years": 2, "locations": ["Karachi", "Pakistan"], "work_modes": ["remote", "hybrid"]})
        ids = [r["job"]["id"] for r in ordered]
        self.assertLess(ids.index("j01"), ids.index("j03"))
        senior = next(row for row in ordered if row["job"]["id"] == "j03")
        self.assertEqual({c["kind"] for c in senior["assessment"]["conflicts"]}, {"experience", "location", "work_mode"})

    def test_invalid_context(self):
        for context in ({"experience_years": True}, {"experience_years": -1}, {"skills": "Python"}, {"work_modes": ["anything"]}):
            with self.assertRaises(ValueError):
                assess(load_jobs()[0], context)
