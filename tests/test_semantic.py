import os
import unittest

from jobmatch.evaluation import evaluate
from jobmatch.retrieval import load_jobs, TfidfRetriever
from jobmatch.semantic import make_retriever


class EvaluationBackendTests(unittest.TestCase):
    def test_shared_evaluator_accepts_retriever_and_counts_missing_hits(self):
        jobs = load_jobs()
        profiles = [{"id": "p", "text": "Java Spring"}]
        labels = {"p": {job["id"]: 3 if job["id"] == "j12" else 0 for job in jobs}}
        report = evaluate(jobs, profiles, labels, repeats=2,
                          retriever=TfidfRetriever(jobs), approach="custom")
        self.assertEqual(report["approach"], "custom")
        self.assertEqual(report["ndcg_at_10"], 1)
        self.assertEqual(report["precision_at_5"], 0.2)
        self.assertEqual(report["latency_samples"], 2)

    def test_unknown_backend_is_rejected(self):
        with self.assertRaises(ValueError):
            make_retriever(load_jobs(), "unknown")


@unittest.skipUnless(os.environ.get("JOBMATCH_RUN_MODEL_TESTS") == "1",
                     "Set JOBMATCH_RUN_MODEL_TESTS=1 after downloading the semantic model")
class SemanticIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = make_retriever(load_jobs(), "semantic", offline=True)

    def test_real_model_finds_java_role_and_scores_are_finite(self):
        import math
        results = self.retriever.search("Java Spring backend development", 5)
        self.assertEqual(results[0]["job"]["id"], "j12")
        self.assertEqual(len(results), 5)
        self.assertTrue(all(math.isfinite(row["score"]) and -1.00001 <= row["score"] <= 1.00001 for row in results))

    def test_blank_and_invalid_limit_rejected(self):
        with self.assertRaises(ValueError):
            self.retriever.search(" ")
        with self.assertRaises(ValueError):
            self.retriever.search("Python", 0)

    def test_repeated_queries_are_stable_and_index_is_unchanged(self):
        before = self.retriever.vectors.copy()
        first = self.retriever.search("data analysis statistics SQL")
        second = self.retriever.search("data analysis statistics SQL")
        self.assertEqual([r["job"]["id"] for r in first], [r["job"]["id"] for r in second])
        self.assertTrue((before == self.retriever.vectors).all())
