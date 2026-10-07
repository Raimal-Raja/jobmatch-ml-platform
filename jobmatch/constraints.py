"""Conservative requirements extraction and explicit user preference checks."""
import re
from .profiles import SKILLS

VOCABULARY = SKILLS + ("Spring", "REST APIs", "testing", "statistics", "machine learning",
                       "model evaluation", "Linux", "distributed systems", "transformers",
                       "natural language processing", "research publications", "accessibility",
                       "dashboards", "CI/CD")
NUMBERS = {word: index for index, word in enumerate(("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"))}


def evidence(text, start, end):
    return {"source": "job_description", "start": start, "end": end, "quote": text[start:end]}


def requirements(job):
    text = job["description"]
    output = {"required": [], "preferred": [], "minimum_years": None, "experience_evidence": None}
    headings = list(re.finditer(r"\b(Required|Preferred):", text, re.I))
    for index, heading in enumerate(headings):
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        segment = text[start:end]
        kind = heading.group(1).lower()
        for skill in VOCABULARY:
            match = re.search(r"(?<![\w+#])" + re.escape(skill) + r"(?![\w+#])", segment, re.I)
            if match:
                output[kind].append({"skill": skill, "evidence": evidence(text, start + match.start(), start + match.end())})
    # Only explicit numeric/word year requirements; no date arithmetic or qualification inference.
    number = r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
    match = re.search(rf"\b({number})(?:\s+to\s+{number})?\s+years?\b", text, re.I)
    if match:
        raw = match.group(1).lower()
        output["minimum_years"] = int(raw) if raw.isdigit() else NUMBERS[raw]
        output["experience_evidence"] = evidence(text, match.start(), match.end())
    return output


def validate_context(context):
    allowed = {"skills", "experience_years", "locations", "work_modes"}
    if not isinstance(context, dict) or set(context) - allowed:
        raise ValueError("Context allows skills, experience_years, locations and work_modes only")
    for key in ("skills", "locations", "work_modes"):
        if key in context and (not isinstance(context[key], list) or any(not isinstance(v, str) or not v.strip() for v in context[key])):
            raise ValueError(f"{key} must be a list of nonempty strings")
    if "experience_years" in context and (type(context["experience_years"]) not in (int, float) or not 0 <= context["experience_years"] <= 80):
        raise ValueError("experience_years must be a number from 0 to 80")
    if "work_modes" in context and set(context["work_modes"]) - {"remote", "hybrid", "onsite"}:
        raise ValueError("Unknown work mode")
    return context


def assess(job, context):
    validate_context(context)
    parsed = requirements(job)
    known = {skill.lower() for skill in context.get("skills", [])}
    def classify(items):
        return [{**item, "status": ("supported" if item["skill"].lower() in known else "not_evidenced")
                 if "skills" in context else "unknown"} for item in items]
    required, preferred = classify(parsed["required"]), classify(parsed["preferred"])
    conflicts = []
    minimum = parsed["minimum_years"]
    if minimum is not None and "experience_years" in context and context["experience_years"] < minimum:
        conflicts.append({"kind": "experience", "evidence": parsed["experience_evidence"], "message": f"Job states at least {minimum} years; user provided {context['experience_years']}"})
    if context.get("locations") and job["location"].lower() not in {v.lower() for v in context["locations"]}:
        conflicts.append({"kind": "location", "evidence": {"source": "job_location", "quote": job["location"]}, "message": "Location is outside supplied allowed locations"})
    if context.get("work_modes") and job["work_mode"] not in context["work_modes"]:
        conflicts.append({"kind": "work_mode", "evidence": {"source": "job_work_mode", "quote": job["work_mode"]}, "message": "Work mode is outside supplied preferences"})
    missing = [item for item in required if item["status"] == "not_evidenced"]
    return {"required": required, "preferred": preferred, "conflicts": conflicts,
            "required_coverage": sum(item["status"] == "supported" for item in required) / len(required) if required and "skills" in context else None,
            "learning_priorities": [{"skill": item["skill"], "evidence": item["evidence"],
                                     "action": f"Review the requirement for {item['skill']}; if relevant, study fundamentals and build a small demonstrable project."} for item in missing[:3]],
            "warning": "Not evidenced means absent from confirmed profile data, not proof that a skill is lacking. Study does not replace required work experience."}


def apply_constraints(results, context):
    enriched = [{**row, "assessment": assess(row["job"], context)} for row in results]
    # Explicit conflicts first, then required-skill coverage, then the model's raw signal.
    return sorted(enriched, key=lambda row: (len(row["assessment"]["conflicts"]),
                                           -(row["assessment"]["required_coverage"] or 0),
                                           -row["score"], row["job"]["id"]))
