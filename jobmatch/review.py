"""Prepare human review; validate complete grades and exact evidence before applying."""
import csv
import json
from pathlib import Path

FIELDS = ("profile_id", "job_id", "grade", "reviewer", "rationale", "resume_quote", "job_quote")


def export_review(jobs, fixture, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS + ("profile_text", "job_description"))
        writer.writeheader()
        for profile in fixture["profiles"]:
            for job in jobs:
                writer.writerow({"profile_id": profile["id"], "job_id": job["id"],
                                 "profile_text": profile["text"], "job_description": job["description"]})
    return {"pairs_to_review": len(jobs) * len(fixture["profiles"]), "output": str(target)}


def apply_review(jobs, fixture, source, target):
    profiles = {profile["id"]: profile["text"] for profile in fixture["profiles"]}
    descriptions = {job["id"]: job["description"] for job in jobs}
    expected = {(profile, job) for profile in profiles for job in descriptions}
    seen, reviewers, records = set(), set(), []
    judgments = {profile: {} for profile in profiles}
    with Path(source).open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            pair = (row.get("profile_id"), row.get("job_id"))
            if pair not in expected or pair in seen:
                raise ValueError("Review contains an unknown or duplicate pair")
            if row.get("grade") not in ("0", "1", "2", "3") or any(not row.get(key, "").strip() for key in FIELDS[3:]):
                raise ValueError("Every pair needs grade 0–3, reviewer, rationale and two evidence quotes")
            if row["resume_quote"] not in profiles[pair[0]] or row["job_quote"] not in descriptions[pair[1]]:
                raise ValueError("Evidence quotations must match the supplied sources exactly")
            seen.add(pair)
            reviewers.add(row["reviewer"])
            records.append({key: row[key] for key in FIELDS})
            judgments[pair[0]][pair[1]] = int(row["grade"])
    if seen != expected:
        raise ValueError("Review must cover all profile–job pairs")
    output = {**fixture, "judgments": judgments, "review_status": "reviewer_declared_human_review",
              "reviewers": sorted(reviewers), "review_records": records}
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return {"reviewed_pairs": len(seen), "output": str(target)}
