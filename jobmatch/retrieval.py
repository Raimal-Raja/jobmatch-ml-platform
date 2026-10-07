"""Dependency-free TF-IDF cosine baseline; scores are ranking signals."""
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STOPWORDS = set("a an and are as at be by for from in is of on or the to with you your".split())


def tokenize(text):
    return [token for token in re.findall(r"[a-z0-9]+(?:[+#]+)?", text.lower()) if token not in STOPWORDS]


def load_jobs(path=ROOT / "data/jobs.json"):
    jobs = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_jobs(jobs)


def validate_jobs(jobs):
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Job dataset must be a nonempty list")
    ids, fingerprints = set(), set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("Each listing must be an object")
        for field in ("id", "title", "description", "location", "work_mode"):
            if not isinstance(job.get(field), str) or not job[field].strip():
                raise ValueError(f"Job requires a nonempty {field}")
        fingerprint = tuple(tokenize(job["title"] + " " + job["description"]))
        if job["work_mode"] not in ("remote", "hybrid", "onsite"):
            raise ValueError("Unknown job work mode")
        if len(job["description"]) > 30000 or len(job["title"]) > 300 or len(job["id"]) > 100:
            raise ValueError("Job field exceeds supported length")
        if job["id"] in ids or fingerprint in fingerprints:
            raise ValueError("Duplicate job ID or normalized listing")
        ids.add(job["id"])
        fingerprints.add(fingerprint)
    return jobs


class TfidfRetriever:
    def __init__(self, jobs):
        self.jobs = jobs
        documents = [Counter(tokenize(j["title"] + " " + j["description"])) for j in jobs]
        df = Counter(term for document in documents for term in document)
        self.idf = {term: math.log((1 + len(jobs)) / (1 + count)) + 1 for term, count in df.items()}
        self.vectors = [self._vector(document) for document in documents]

    def _vector(self, counts):
        weights = {term: (1 + math.log(count)) * self.idf[term] for term, count in counts.items() if term in self.idf}
        norm = math.sqrt(sum(value * value for value in weights.values()))
        return {term: value / norm for term, value in weights.items()} if norm else {}

    def search(self, query, limit=10):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must contain text")
        if limit < 1:
            raise ValueError("Limit must be positive")
        vector = self._vector(Counter(tokenize(query)))
        results = []
        for job, document in zip(self.jobs, self.vectors):
            score = sum(value * document.get(term, 0) for term, value in vector.items())
            if score > 0:
                results.append({"job": job, "score": score})
        return sorted(results, key=lambda r: (-r["score"], r["job"]["id"]))[:limit]
