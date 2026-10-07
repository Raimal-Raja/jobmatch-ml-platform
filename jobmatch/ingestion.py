"""Explicitly permitted manual JSON listing imports, never scraping."""
import json
from pathlib import Path
from .retrieval import ROOT, tokenize, validate_jobs


def ingest(path, output=ROOT / "private_data/jobs.json"):
    source = Path(path)
    if source.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("Listing import exceeds 5 MiB")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Import must be an object with provenance and jobs")
    provenance = payload.get("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError("Provenance must be an object")
    if provenance.get("kind") != "manual" or not all(isinstance(provenance.get(key), str) and provenance[key].strip() for key in ("source", "permission")):
        raise ValueError("Manual import requires provenance.kind=manual, source and permission declarations")
    jobs = validate_jobs(payload.get("jobs"))
    if len(jobs) > 1000:
        raise ValueError("Import supports up to 1,000 listings")
    seen = []
    for job in jobs:
        words = set(tokenize(job["title"] + " " + job["description"]))
        for prior_id, prior_words in seen:
            if len(words & prior_words) / max(1, len(words | prior_words)) >= 0.90:
                raise ValueError(f"Near-duplicate listings: {prior_id} and {job['id']}")
        seen.append((job["id"], words))
        job["provenance"] = dict(provenance)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(jobs, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return {"imported": len(jobs), "output": str(target), "provenance": provenance}
