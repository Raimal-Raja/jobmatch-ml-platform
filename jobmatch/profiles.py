"""Local résumé drafts with source evidence and explicit user corrections."""
import json
import re
import uuid
from io import BytesIO
from pathlib import Path

from .retrieval import ROOT

SKILLS = ("Python", "Django", "FastAPI", "PostgreSQL", "SQL", "Docker", "Git",
          "JavaScript", "TypeScript", "React", "HTML", "CSS", "pandas",
          "scikit-learn", "MLflow", "PyTorch", "Kubernetes", "AWS", "Java", "Excel")
SECTIONS = {"experience": "experience", "work experience": "experience",
            "professional experience": "experience", "education": "education",
            "skills": "skills", "technical skills": "skills", "projects": "projects",
            "summary": "summary", "certifications": "certifications"}


def extract_pages(pdf_bytes):
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Input must be a PDF")
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise ValueError("PDF exceeds 10 MiB limit")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError('Install PDF support with: pip install -e ".[resume]"') from exc
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are unsupported")
        if len(reader.pages) > 20:
            raise ValueError("PDF exceeds 20 page limit")
        pages = [{"page": index + 1, "text": page.extract_text() or ""}
                 for index, page in enumerate(reader.pages)]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Cannot read this PDF") from exc
    if not any(page["text"].strip() for page in pages):
        raise ValueError("PDF contains no extractable text; scanned PDFs need OCR")
    if sum(len(page["text"]) for page in pages) > 200_000:
        raise ValueError("Extracted text exceeds 200,000 character limit")
    return pages


def draft_profile(pages):
    fields = {"skills": [], "experience": [], "education": []}
    section = None
    for page in pages:
        text = page["text"]
        for match in re.finditer(r"[^\n\r]+", text):
            line = match.group().strip()
            if not line:
                continue
            heading = line.lower().rstrip(":")
            if heading in SECTIONS:
                section = SECTIONS[heading]
                continue
            evidence = {"page": page["page"], "start": match.start(),
                        "end": match.end(), "quote": match.group()}
            if section in ("experience", "education"):
                fields[section].append({"value": line, "origin": "extracted",
                                        "confirmed": False, "evidence": evidence})
            # Mentions are candidates, not inferred proficiency or qualifications.
            for skill in SKILLS:
                if re.search(r"(?<![\w+#])" + re.escape(skill) + r"(?![\w+#])", line, re.I):
                    fields["skills"].append({"value": skill, "origin": "extracted",
                                             "confirmed": False, "evidence": evidence})
    return {"schema_version": 1, "reviewed": False, "pages": pages, **fields,
            "warnings": ["Skill mentions may be negated or aspirational; review every candidate.",
                         "Experience and education are source lines; dates, degrees and years are not inferred."]}


class ProfileStore:
    def __init__(self, root=ROOT / "private_data/profiles"):
        self.root = Path(root)

    def _directory(self, profile_id):
        if not isinstance(profile_id, str) or not re.fullmatch(r"[a-f0-9]{32}", profile_id):
            raise ValueError("Invalid profile ID")
        directory = self.root / profile_id
        if self.root.is_symlink() or directory.is_symlink():
            raise ValueError("Profile storage cannot be a symlink")
        return directory

    def create(self, pdf_path):
        path = Path(pdf_path)
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("PDF exceeds 10 MiB limit")
        content = path.read_bytes()
        return self.create_bytes(content)

    def create_bytes(self, content):
        profile = draft_profile(extract_pages(content))
        profile["id"] = uuid.uuid4().hex
        directory = self._directory(profile["id"])
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "resume.pdf").write_bytes(content)
        self._save(profile)
        return profile

    def _save(self, profile):
        directory = self._directory(profile["id"])
        temporary = directory / "profile.tmp"
        temporary.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        temporary.replace(directory / "profile.json")

    def get(self, profile_id):
        return json.loads((self._directory(profile_id) / "profile.json").read_text(encoding="utf-8"))

    def update(self, profile_id, corrections):
        if not isinstance(corrections, dict) or not corrections or set(corrections) - {"skills", "experience", "education"}:
            raise ValueError("Corrections must contain skills, experience or education")
        for values in corrections.values():
            if not isinstance(values, list) or len(values) > 100 or any(
                not isinstance(value, str) or not value.strip() or len(value) > 2000 for value in values
            ):
                raise ValueError("Each corrected field must be a list of up to 100 nonempty strings (max 2,000 characters)")
        profile = self.get(profile_id)
        for field, values in corrections.items():
            prior = profile[field]
            profile[field] = []
            for value in dict.fromkeys(value.strip() for value in values):
                candidate = next((item for item in prior if item["value"] == value), None)
                profile[field].append({"value": value, "origin": candidate["origin"] if candidate else "user",
                                       "confirmed": True, "evidence": candidate["evidence"] if candidate else None})
        profile["reviewed"] = all(item["confirmed"] for field in ("skills", "experience", "education") for item in profile[field])
        self._save(profile)
        return profile

    def delete(self, profile_id):
        directory = self._directory(profile_id)
        # Remove only files owned by this store; never recursively delete a supplied path.
        if not directory.is_dir():
            raise FileNotFoundError("Profile not found")
        for name in ("resume.pdf", "profile.json", "profile.tmp"):
            (directory / name).unlink(missing_ok=True)
        directory.rmdir()

    def search_text(self, profile_id):
        profile = self.get(profile_id)
        values = [item["value"] for field in ("skills", "experience", "education")
                  for item in profile[field] if item["confirmed"]]
        if not values:
            raise ValueError("Confirm or correct profile fields before searching")
        return "\n".join(values)
