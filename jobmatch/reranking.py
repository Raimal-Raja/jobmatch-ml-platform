"""Shortlist retrieval followed by a fixed cross-encoder; raw scores are signals."""
from .retrieval import ROOT
from .semantic import SemanticRetriever

MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"


class RerankedRetriever:
    def __init__(self, jobs, *, offline=False, candidate_pool=20):
        if type(candidate_pool) is not int or candidate_pool < 10:
            raise ValueError("Candidate pool must be an integer >= 10")
        from sentence_transformers import CrossEncoder
        from torch import nn
        self.retriever = SemanticRetriever(jobs, offline=offline)
        self.candidate_pool = candidate_pool
        self.model = CrossEncoder(MODEL, revision=REVISION, device="cpu", max_length=512,
                                  cache_folder=str(ROOT / ".model_cache"), local_files_only=offline,
                                  trust_remote_code=False, activation_fn=nn.Identity())
        self.metadata = {"retrieval": self.retriever.metadata, "reranker_model": MODEL,
                         "reranker_revision": REVISION, "candidate_pool": candidate_pool,
                         "max_pair_tokens": 512, "score_type": "raw logit; not hiring probability"}

    def search(self, query, limit=10):
        if limit > self.candidate_pool:
            raise ValueError("Result limit cannot exceed candidate pool")
        candidates = self.retriever.search(query, self.candidate_pool)
        pairs = [(query, row["job"]["title"] + " " + row["job"]["description"]) for row in candidates]
        scores = self.model.predict(pairs, batch_size=16, show_progress_bar=False)
        results = [{"job": row["job"], "score": float(score), "retrieval_score": row["score"]}
                   for row, score in zip(candidates, scores)]
        return sorted(results, key=lambda row: (-row["score"], row["job"]["id"]))[:limit]
