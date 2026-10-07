# AI Job Matching and Skill-Gap Platform

An incremental Python project that will retrieve jobs for an editable résumé profile, compare keyword and semantic ranking, and explain strengths and gaps using source evidence. Match scores are ranking signals, never probabilities of getting hired.

## Current status: Steps 1, 2 and 3 implemented

The working sample provides dependency-free TF-IDF cosine retrieval, 12 fictional job listings, three fictional profiles, a relevance rubric, complete provisional labels for 36 pairs, reproducible metrics, and automated checks. Step 2 adds local PDF import, editable profiles, source evidence, confirmed-profile search and deletion through the CLI. Step 3 adds local sentence-transformer retrieval and a shared comparison benchmark. Human review of evaluation labels remains pending. Browser uploads, cross-encoder reranking, APIs and the UI are future steps.

GitHub repository: [Raimal-Raja/jobmatch-ml-platform](https://github.com/Raimal-Raja/jobmatch-ml-platform).

## Run the sample

Use Python 3.10 or later from the repository root. No paid credentials, model downloads or third-party packages are required. Installation is unnecessary for these commands.

```sh
python -m jobmatch search "Python Django PostgreSQL REST APIs" --limit 5
python -m jobmatch evaluate
python -m unittest discover -s tests -v
```

On Windows, use `py -3` if Python is installed through the launcher. In this Codex workspace neither `python` nor the launcher has an installed interpreter; verification used the bundled runtime:

```powershell
& 'C:\Users\Professor\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m jobmatch search 'Python Django PostgreSQL REST APIs' --limit 5
& 'C:\Users\Professor\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m jobmatch evaluate
& 'C:\Users\Professor\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -v
```

Search prints listings and cosine scores as JSON. Evaluation writes `reports/baseline.json`; use `--output path/to/report.json` to save another run. Timings vary by machine and load.

## Step 2: PDF résumés and editable profiles

Install the optional PDF dependency in a virtual environment. Step 1 continues to work without it. Commands run from a source checkout:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[resume]"
python -m jobmatch resume data/sample_resume.pdf
```

The import prints an `id` and a draft with skills, experience and education. Substitute that ID below. The supplied corrections match the fictional sample; for your own résumé, write a JSON file containing corrected lists of `skills`, `experience` and `education`. Each supplied list replaces that field, and an empty list clears it. Omitted fields retain their current values.

```sh
python -m jobmatch profile show PROFILE_ID
python -m jobmatch profile update PROFILE_ID --corrections data/sample_corrections.json
python -m jobmatch profile search PROFILE_ID
python -m jobmatch profile delete PROFILE_ID
```

Each extracted candidate has an exact quotation, page number and character offsets into that page's extracted text. Candidates start unconfirmed. Corrections confirm selected values; new user-entered values are marked `origin: user` with no fabricated PDF evidence. Search uses only confirmed fields. This is manual JSON editing through a CLI; a browser-based editor is planned in Step 5.

The store retains an imported PDF copy and its profile under ignored `private_data/profiles/`. Delete removes both stored files and the profile directory while preserving the original input PDF. Files are local and unencrypted; no résumé data is sent to a model or service. This single-user CLI has no authentication or server-side isolation yet. Avoid sharing terminal output containing personal data.

Input checks reject non-PDF, malformed, encrypted, empty/scanned PDFs, files over 10 MiB, more than 20 pages, and extracted text over 200,000 characters. OCR is not implemented. Skill extraction uses a small explicit vocabulary and detects mentions, including potentially negated mentions; confirmation is essential. Experience and education require recognized section headings and preserve source lines rather than inferring duration or degree equivalence. Multi-column PDFs may extract in the wrong order. These parser limits are not a hardened untrusted-upload sandbox; resource-isolated processing is needed before public uploads.

Validation: **8 tests passed**, including real PDF import, exact evidence spans, correction persistence, confirmed-only search, deletion preserving the original, malformed/blank/encrypted/oversized inputs, page limits and invalid IDs. The CLI import → correction → search → deletion flow was also verified with the fictional sample. Tests for PDF functionality require the optional dependency; without it those three tests skip. The bundled Codex Python already includes `pypdf`.

The fictional sample can be regenerated with `python scripts/create_sample_resume.py`, without third-party packages. See [profile design](docs/profiles.md) for the data contract.

## Step 3: semantic retrieval and comparison

Use the virtual environment from Step 2, then install the semantic extra:

```sh
python -m pip install -e ".[resume,semantic]"
python -m jobmatch search "building web APIs with relational databases" --approach semantic
python -m jobmatch compare
```

The first semantic command downloads the public `all-MiniLM-L6-v2` model into ignored `.model_cache/`. No paid credentials are required. Model inference stays local on CPU; profile text is not sent to a hosted inference API. The main ML packages and model revision are pinned. Both keyword and semantic scores are ranking signals.

After downloading, offline commands use only cached model files:

```sh
python -m jobmatch compare --offline --repeats 100
python -m jobmatch profile search PROFILE_ID --approach semantic --offline
```

The benchmark writes `reports/comparison.json` with both approaches, per-profile rankings, NDCG@10, Precision@5, p95 time, paid API cost, model metadata and a fixture fingerprint. It benchmarks fresh query embeddings, with precomputed job vectors, and does not include model setup in response latency. Setup time is reported separately. Infrastructure cost remains unmeasured.

Run the three optional real-model tests after the download:

```powershell
$env:JOBMATCH_RUN_MODEL_TESTS = '1'
python -m unittest discover -s tests -v
```

On macOS/Linux, use `JOBMATCH_RUN_MODEL_TESTS=1 python -m unittest discover -s tests -v`. Without that flag, tests never download model files. See [semantic design and limitations](docs/semantic.md).

## Step 1 measured results

Measured using Python 3.12.14 on Windows, with 12 jobs, three profiles, 36 provisional labels and 300 warm latency samples:

| Metric | Result |
| --- | ---: |
| NDCG@10 | 0.9867 |
| Precision@5 | 0.4667 |
| p95 retrieval time | 0.0526 ms |
| Paid API cost per search | US$0 |
| Infrastructure cost per search | Not measured |

These are smoke-benchmark results on a tiny, simple fictional fixture with **agent-authored labels awaiting human review**. They do not establish real-world accuracy. Latency excludes indexing, file reads, HTTP and UI overhead. The three automated tests passed. See [evaluation protocol](docs/evaluation.md) for metric definitions, review criteria and leakage controls.

## Incremental delivery plan

Each step ends with a working sample, relevant verification and a README update describing commands, results and limitations. Steps remain small enough to review separately.

| Step | Deliverable | Completion check | Status |
| --- | --- | --- | --- |
| 1 | Clean fictional data, TF-IDF retrieval and evaluation harness | Search runs; metrics saved; tests pass | Implemented; human label review pending |
| 2 | PDF parsing and editable structured profiles | Extracted text has source references; user corrections persist; deletion works | Implemented (CLI) |
| 3 | Sentence-transformer retrieval | Same evaluation compares TF-IDF and embeddings; model/version recorded | Implemented |
| 4 | Cross-encoder reranking and constraint handling | Compare all three methods; record latency and costs; test required/preferred distinctions | Next |
| 5 | FastAPI and Streamlit evidence/skill-gap interface | Quotes trace to sources; gaps and learning priorities do not invent qualifications | Planned |
| 6 | PostgreSQL/pgvector, ingestion, Docker and CI | Permitted provenance, validation, duplicate controls, privacy and integration checks | Planned |
| 7 | Expanded human-reviewed evaluation, MLflow and demo deployment | Frozen evaluation split, reproducible comparison, architecture diagram and two-minute demo | Planned |

The six-week proposal guides scheduling; these seven implementation checkpoints keep individual changes reviewable. Human review should start now and expand throughout the build. Future model selection must use development data separate from the final evaluation set.

## Files and baseline design

- `data/jobs.json`: hand-authored fictional listings; required and preferred requirements retained in source text.
- `data/evaluation.json`: fictional profiles and provisional graded judgments.
- `jobmatch/retrieval.py`: job validation, tokenization, log term frequency, smoothed IDF and cosine ranking with deterministic tie-breaking.
- `jobmatch/evaluation.py`: ranking metrics, complete-label validation and warm latency measurement.
- `reports/baseline.json`: measured baseline, per-profile rankings and environment.
- `tests/test_baseline.py`: search behavior, known metric values and incomplete-label rejection.

IDF is fitted only on job documents. Evaluation profiles do not fit the index. Normalized exact duplicate listings and duplicate IDs are rejected. Imported résumé files and profiles stay under ignored `private_data/`; only fictional sample data belongs in version control.

## Limitations

Keyword overlap misses synonyms and can reward incidental terms. The baseline does not understand negation or required versus preferred skills and does not enforce experience, location or remote-work constraints. It can rank senior jobs despite an experience gap. Near-duplicate detection is not implemented yet. No learning plans or explanations are generated in Step 1.

Publish résumé achievement numbers only after larger human-reviewed experiments. Report improvements against this baseline on the same frozen evaluation set, alongside deployed latency and measured infrastructure cost.
