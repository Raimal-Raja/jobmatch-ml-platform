"""Reproducible ranking metrics and warm in-process latency."""
import math
import time
from .retrieval import TfidfRetriever


def ndcg(ranked_ids, labels, k=10):
    def dcg(grades):
        return sum((2 ** grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades))
    ideal = dcg(sorted(labels.values(), reverse=True)[:k])
    return dcg([labels.get(job_id, 0) for job_id in ranked_ids[:k]]) / ideal if ideal else 0.0


def precision(ranked_ids, labels, k=5):
    return sum(labels.get(job_id, 0) >= 2 for job_id in ranked_ids[:k]) / k


def evaluate(jobs, profiles, judgments, repeats=100, *, retriever=None, approach="tfidf"):
    if repeats < 1 or not profiles:
        raise ValueError("Evaluation needs profiles and positive repeats")
    job_ids = {job["id"] for job in jobs}
    profile_ids = {profile["id"] for profile in profiles}
    if len(profile_ids) != len(profiles) or set(judgments) != profile_ids:
        raise ValueError("Judgments must cover each unique profile")
    for labels in judgments.values():
        if set(labels) != job_ids or any(type(grade) is not int or grade not in range(4) for grade in labels.values()):
            raise ValueError("Every job needs an integer grade from 0 to 3")
    retriever = retriever if retriever is not None else TfidfRetriever(jobs)
    rows, durations = [], []
    for profile in profiles:
        ranked = [r["job"]["id"] for r in retriever.search(profile["text"])]
        labels = judgments[profile["id"]]
        rows.append({"profile_id": profile["id"], "ndcg_at_10": ndcg(ranked, labels), "precision_at_5": precision(ranked, labels), "ranking": ranked})
        for _ in range(repeats):
            start = time.perf_counter_ns()
            retriever.search(profile["text"])
            durations.append((time.perf_counter_ns() - start) / 1_000_000)
    return {
        "approach": approach, "label_status": "provisional_not_human_reviewed",
        "jobs": len(jobs), "profiles": len(profiles), "pairs": len(jobs) * len(profiles),
        "ndcg_at_10": sum(r["ndcg_at_10"] for r in rows) / len(rows),
        "precision_at_5": sum(r["precision_at_5"] for r in rows) / len(rows),
        "p95_response_ms": sorted(durations)[math.ceil(0.95 * len(durations)) - 1],
        "latency_scope": "warm in-process retrieval, excludes indexing, file I/O, network and UI",
        "latency_samples": len(durations),
        "paid_api_cost_usd_per_search": 0,
        "infrastructure_cost_usd_per_search": None,
        "per_profile": rows,
    }


def compare(jobs, profiles, judgments, repeats=100, offline=False):
    import hashlib
    import json
    from .semantic import make_retriever
    reports = []
    for approach in ("tfidf", "semantic", "reranked"):
        start = time.perf_counter()
        retriever = make_retriever(jobs, approach, offline)
        setup = time.perf_counter() - start
        report = evaluate(jobs, profiles, judgments, repeats, retriever=retriever, approach=approach)
        report["setup_seconds"] = setup
        report["model_metadata"] = getattr(retriever, "metadata", None)
        reports.append(report)
    fixture = {"jobs": jobs, "profiles": profiles, "judgments": judgments}
    fingerprint = hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest()
    return {"fixture_sha256": fingerprint, "results": reports,
            "reranked_minus_tfidf": {metric: reports[2][metric] - reports[0][metric]
                                      for metric in ("ndcg_at_10", "precision_at_5", "p95_response_ms")},
            "semantic_minus_tfidf": {metric: reports[1][metric] - reports[0][metric]
                                      for metric in ("ndcg_at_10", "precision_at_5", "p95_response_ms")}}
