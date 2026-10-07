"""Local sentence-transformer cosine retrieval with a fixed model revision."""
from importlib.metadata import version
from .retrieval import ROOT

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


class SemanticRetriever:
    def __init__(self, jobs, *, offline=False):
        if not jobs:
            raise ValueError("Job dataset must be nonempty")
        try:
            import numpy as np
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ValueError('Install semantic support with: pip install -e ".[semantic]"') from exc
        self.np = np
        # Fixed CPU/thread configuration keeps this small benchmark interpretable.
        torch.set_num_threads(1)
        self.jobs = jobs
        self.model = SentenceTransformer(MODEL, revision=REVISION, device="cpu",
                                         cache_folder=str(ROOT / ".model_cache"),
                                         local_files_only=offline, trust_remote_code=False)
        self.vectors = self.model.encode([job["title"] + " " + job["description"] for job in jobs],
                                         normalize_embeddings=True, show_progress_bar=False)
        self.metadata = {"model": MODEL, "revision": REVISION, "device": "cpu", "torch_threads": 1,
                         "embedding_dimension": int(self.vectors.shape[1]),
                         "max_sequence_length": self.model.max_seq_length,
                         "sentence_transformers_version": version("sentence-transformers"),
                         "torch_version": version("torch"), "numpy_version": version("numpy"),
                         "query_embedding_cache": False}

    def search(self, query, limit=10):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must contain text")
        if limit < 1:
            raise ValueError("Limit must be positive")
        vector = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        scores = self.vectors @ vector
        results = [{"job": job, "score": float(score)} for job, score in zip(self.jobs, scores)]
        # Dense similarity always ranks candidates; it does not certify relevance.
        return sorted(results, key=lambda row: (-row["score"], row["job"]["id"]))[:limit]


def make_retriever(jobs, approach="tfidf", offline=False):
    if approach == "semantic":
        return SemanticRetriever(jobs, offline=offline)
    if approach == "tfidf":
        from .retrieval import TfidfRetriever
        return TfidfRetriever(jobs)
    raise ValueError("Unknown retrieval approach")
