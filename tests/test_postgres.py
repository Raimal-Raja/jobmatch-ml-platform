import os
import unittest
from jobmatch.postgres import PgvectorStore, vector_text
from jobmatch.retrieval import load_jobs


class VectorValidationTests(unittest.TestCase):
    def test_bad_dimensions_nonfinite_and_zero_rejected(self):
        for vector in ([1, 2], [0] * 384, [float("nan")] * 384):
            with self.assertRaises(ValueError):
                vector_text(vector)


@unittest.skipUnless(os.environ.get("JOBMATCH_TEST_DATABASE") == "1", "Enable ephemeral PostgreSQL integration tests")
class PostgresTests(unittest.TestCase):
    def test_persist_cosine_order_and_stale_catalog_rejection(self):
        store = PgvectorStore()
        jobs = load_jobs()[:2]
        first = [1.0] + [0.0] * 383
        second = [0.0, 1.0] + [0.0] * 382
        store.upsert(jobs, [first, second])
        result = store.search(jobs, first)
        self.assertEqual(result[0]["job"]["id"], jobs[0]["id"])
        self.assertAlmostEqual(result[0]["score"], 1.0)
        self.assertAlmostEqual(result[1]["score"], 0.0)
        changed = [{**jobs[0], "description": "Changed catalog"}, jobs[1]]
        with self.assertRaisesRegex(ValueError, "stale"):
            store.search(changed, first)
