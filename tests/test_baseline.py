import unittest
from jobmatch.retrieval import TfidfRetriever, load_jobs
from jobmatch.evaluation import evaluate, ndcg, precision


class BaselineTests(unittest.TestCase):
    def test_exact_match_and_unknown_query(self):
        retriever = TfidfRetriever(load_jobs())
        self.assertEqual(retriever.search("Java Spring")[0]["job"]["id"], "j12")
        self.assertEqual(retriever.search("unseenword"), [])
        with self.assertRaises(ValueError):
            retriever.search(" ")

    def test_metrics_known_values(self):
        labels = {"a": 3, "b": 2, "c": 0}
        self.assertAlmostEqual(ndcg(["a", "b", "c"], labels), 1)
        self.assertLess(ndcg(["c", "b", "a"], labels), 1)
        self.assertEqual(precision(["a", "b"], labels), 0.4)
        self.assertEqual(ndcg([], {"a": 0}), 0)

    def test_incomplete_labels_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(load_jobs(), [{"id": "p", "text": "Python"}], {"p": {"j01": 3}})


if __name__ == "__main__":
    unittest.main()
