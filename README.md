# AI Job Matching and Skill-Gap Platform

An incremental Python project that will retrieve jobs for an editable résumé profile, compare keyword and semantic ranking, and explain strengths and gaps using source evidence. Match scores are ranking signals, never probabilities of getting hired.

## Current status: Steps 1–9 implemented; human evaluation and public deployment remain

The working sample provides TF-IDF retrieval, local PDF profiles, semantic retrieval, cross-encoder reranking, explicit constraints, a FastAPI evidence interface, permitted manual ingestion, optional PostgreSQL/pgvector storage, Docker packaging and CI. The 12 fictional jobs and three fictional profiles form 36 provisional evaluation pairs; human label review and public-release validation remain.

GitHub repository: [Raimal-Raja/jobmatch-ml-platform](https://github.com/Raimal-Raja/jobmatch-ml-platform).

Start with the [short user guide](docs/user-guide.md). The default task is to compare your résumé with a job description you paste. Sample-catalog search is a separate demonstration tab.

## Step 8: compare your chosen job and prepare for interviews

### Step 9: a simpler daily workflow

The app opens on **Compare a job**: (1) upload/review/confirm the résumé, (2) paste the selected title/company/description, (3) compare and read the preparation plan. Confirmed profile fields collapse under **Review or edit extracted information**. Optional inputs stay collapsed. Sample-catalog search has its own **Try sample-job search** tab and a **Search sample jobs** button, explicitly identifying its 12 fictional listings. It does not search Indeed or the web.

Comparison is disabled until the profile is confirmed; unsaved edits require reconfirmation. The API also rejects partially confirmed profiles instead of silently searching a subset of fields. Buttons display **Working…**, and errors appear beside the action that failed. Validation: 34 local tests passed with five optional model/database tests skipped, including the partial-confirmation regression; browser CI checks the primary flow, tab switching, confirmation gating, sample search and selected-job comparison.

The [Application checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37758398877) and [model-enabled benchmark/tests](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37758398828) passed at implementation commit `80febe0`. A local sample search with a confirmed profile returned five results. The default comparison workflow and the sample search remain separate tasks.

The catalog search ranks 12 fictional listings and displays the top five by default. **Compare the job you choose** instead analyzes the specific title, company and full description you paste from a listing. Supply an optional source link, job location/work mode, unfamiliar skill names and a daily preparation budget (15–240 minutes). Confirm the résumé first, then click **Compare this job & prepare my week**. A link alone does not import the listing, and no job-board scraping is implemented. The pasted job is analyzed locally for this request; it is not added to training/evaluation data or the catalog.

The result separates recognized required/preferred/unclear skills, retains exact job quotations and shows confirmed résumé support. Missing evidence is not proof of missing ability. Mixed required/preferred wording is marked unclear. Degree, certification, employment-duration and eligibility statements remain available for manual review; explicit required experience statements can be compared with your supplied years. The limited vocabulary can miss unfamiliar requirements, so review the full job text and supply additional exact skill names. Additional skill names must occur in the pasted description to produce a match.

The interview section offers evidence-linked questions, concrete exercises for supported topics, an adjustable mock-interview agenda and a **seven-day preparation timetable**. Each day totals the chosen daily budget. Up to three skill priorities focus practice; required skills without evidence come first. These deterministic practice suggestions do not predict an employer's actual interview questions, stages, hiring decision or what can be mastered in one week. Company metadata is user-supplied and unverified. The platform never adds qualifications to the résumé.

API: `POST /compare-target` takes `profile_id`, `listing` (`title`, `company`, `description` and optional `source_url`, `location`, `work_mode`), `additional_skills`, `context` and `minutes_per_day`. It rejects unconfirmed profiles, unsafe source schemes and invalid budgets. Changes to/deletion of the profile clear the derived browser comparison. Specific overlapping phrases such as `unit testing` are counted once. Validation: 33 local tests passed with five optional model/database tests skipped, including exact source offsets, qualifier ambiguity, unknown-skill review, interview budget totals and the selected-job API flow. Browser CI additionally checks comparison, a not-evidenced skill, all seven timetable days and deletion cleanup.

The final [Application checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37755796179) and [model-enabled benchmark/tests](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37755796284) passed at implementation commit `24db13b`. View the [fictional selected-job comparison and seven-day timetable](reports/target-job-demo.png). A local API check also used a confirmed profile with a clearly fictional Python-developer listing; no personal résumé or comparison report was published. Targeted practice templates and skill vocabularies have not been evaluated against real employer interview outcomes.

## Step 10 — Résumé readiness feedback

Upload a text PDF to see a transparent **0–100 local readiness estimate**: extractable text (35), email/phone (20), recognized section headings (20), year mentions (10), and readable characters (15). Inspect every component beside the score. This is not an employer's ATS test, hiring probability or acceptance guarantee. The text checks do not verify columns, graphics or reading order; headings and contact heuristics can miss international formats. Correct the extracted profile before comparing jobs.

## Step 11 — Permitted job discovery

Enter a role, optional company, country/city and remote/onsite/hybrid preference, then select **Find jobs**. Automatic discovery uses the [Remotive public API](https://github.com/remotive-com/remote-jobs-api) and [Arbeitnow API](https://www.arbeitnow.com/blog/job-board-api), with source attribution and original listing links. Remotive covers remote roles and delays data 24 hours; Arbeitnow primarily covers Europe, with a separate UK endpoint. Results cover at most 500 fetched records per source and 20 displayed candidates. Any country/city can be entered; worldwide coverage is not promised. Unknown arrangements and remote eligibility require employer confirmation.

Provider responses are cached locally for six hours, with bounded downloads and a retry cooldown. Only search criteria go to discovery; résumé data stays local. Selecting a candidate fills its description and compares it with the confirmed profile. Failed providers are reported separately from no matches. No matches means no matching fetched records, never proof that a company has no vacancy. Indeed is a filtered search link, not an automatically fetched source; pasted Indeed descriptions remain supported. No paid credentials are required.

## Step 12 — Reviewed Word résumé draft

After confirming the profile, expand the advanced option beneath readiness feedback. Prepare a source-preserving draft, edit it, confirm that you reviewed it, and download an editable single-column DOCX. The draft normalizes headings and bullets while retaining source claims. Apply profile corrections manually to the draft; no missing skills, employers, metrics or qualifications are invented. This feature reformats source text rather than generating new accomplishments or guaranteeing ATS acceptance. Export is generated in memory and not stored as an additional résumé file.

Verification adds provider/cache/failure/privacy tests, readiness and export tests, browser download and selected-discovery comparison checks, and a separate CI job rendering a fictional DOCX to PDF/PNG for layout review. Local unit verification: **41 passed, five optional model/database tests skipped**. Browser and rendered-export verification must pass before this increment is considered verified. Expanded human-reviewed evaluation and public deployment remain outstanding.

## Step 13 — Optional Google Jobs and NVIDIA rewrite

Select **Google Jobs** in the job-source menu to discover descriptions through [SerpAPI's Google Jobs API](https://serpapi.com/google-jobs-api). Set `SERPAPI_API_KEY` in the server environment and restart. Without a key, the interface provides a filtered Google search link and a setup message. This key is separate from an LLM key. Candidates include descriptions and application links; indexing may be stale and location/work arrangement require confirmation. No résumé is sent for discovery. This increment does not fetch arbitrary web pages or bypass Indeed access controls.

Optional AI rewriting uses [NVIDIA's chat-completions endpoint](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-ultra-550b-a55b-infer). Set a fresh `NVIDIA_API_KEY` locally and restart. The default model is `nvidia/nemotron-3-ultra-550b-a55b`; `NVIDIA_MODEL` can override it. Never paste secrets in source, GitHub or browser fields. No credentials from the conversation are stored or used. The app requires explicit consent to send original résumé text and confirmed corrections to NVIDIA. It checks exact source quotations for each suggested paragraph, rejects incomplete/invalid responses and hides provider error details. Quotations alone cannot validate all paraphrased claims: manually review every suggestion before export. No automatic retries incur extra requests.

The supplied [Google Docs template](https://docs.google.com/document/d/1tbnWMFkKT0c4Mh_IKhrobi_yK8qtjL6vkCgvXWCIKI0/edit) was inspected: one tab, centered Spectral name/contact opening, experience with project bullets, education and skills. Its sample employers, metrics and qualifications must never become candidate facts. The app links to the native template for exact formatting; its existing Word export remains the documented single-column layout. Automatic native-template filling is not implemented. OpenRouter is not configured in this increment. Local fallback remains available without credentials. Live paid-service verification requires locally configured replacement/search keys; mocked tests do not prove live provider access.

Verification: **43 local tests passed, five optional model/database tests skipped**. [Application checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37777268335) and [model checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37777268328) passed at `2f18c71`, including browser AI-consent/review gating and the Google setup fallback with fictional responses. The subsequent numeric-claim rejection passed its local regression test. The development server also returned `setup_required` and a filtered Google URL without a search key; no live AI/provider access is claimed.

## Incremental fix — Automatic company search and usable setup

The previous interface offered Google/AI actions without showing whether keys were configured, and Compare stopped when no description was pasted. The default source is now **Automatic**: Google Jobs is used when a SerpAPI key is configured; otherwise the limited public providers are checked and company-search limitations are stated explicitly. Google failures/setup problems fall back to these providers with a visible explanation, not a vacancy-absence claim. A confirmed résumé gives each candidate a preview of recognized strengths and skills without evidence; select one to view exact evidence and the preparation week. Clicking Compare with a role but no description starts discovery.

The local interface reports integration status and offers masked key inputs under optional configuration. Keys stay only in server-process memory, are cleared from browser fields after submission, are not returned, and disappear on restart. Use a replacement NVIDIA key; SerpAPI is a separate search credential. The existing local-only host and same-origin restrictions apply. AI writing is disabled until configured and consented. This is a single-user loopback demo, not a public credential-management service. Configuration does not prove provider credentials are valid until a real request succeeds. No Google search key was configured when this fix was verified, so automatic Google access remained unavailable; the UI states this rather than claiming the requested worldwide company-search feature is fully operational.

Validation: **45 local tests passed, five optional model/database tests skipped**. [Application checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37778648651) and [model checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37778648751) passed at `a285726`, including role-only Compare starting discovery, session configuration with cleared masked fields, listing selection and comparison. Additional credential-error redaction passed all 11 API checks locally. A live local Google-company query reproduced the missing search key and correctly reported limited-source coverage.

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

### Step 3 measured comparison

Measured on the same 12 jobs, three fictional profiles and 36 provisional pairs, with 300 warm queries per method, in [successful GitHub Actions run 37585828984](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37585828984). The runner used Ubuntu 24.04, Python 3.12.15, CPU PyTorch 2.8.0 and one inference thread.

| Metric | TF-IDF | Semantic |
| --- | ---: | ---: |
| NDCG@10 | 0.9867 | 0.9929 |
| Precision@5 | 0.4667 | 0.4667 |
| p95 warm retrieval | 0.0449 ms | 10.5201 ms |
| Paid API cost/search | US$0 | US$0 |
| Infrastructure cost/search | Not measured | Not measured |

Semantic NDCG improved by **0.0061 absolute** on this fixture, with unchanged Precision@5 and substantially higher retrieval latency. This small, provisional benchmark does not establish generalization. Semantic search still ranks the senior backend job third for the two-year backend profile despite its six-year requirement; constraint handling remains Step 4 work.

**All 13 tests passed on GitHub Actions**, including three real-model tests using the offline cached model. Locally, 10 tests passed with the three model tests skipped; the local semantic dependency download was too slow to complete, so measured semantic results come from the Linux runner. Core keyword and résumé workflows remain verified locally.

The committed [comparison report](reports/comparison.json) is recovered from that run's JSON stdout and includes its source commit/run provenance. [Installed dependency versions](reports/benchmark-requirements.txt) are reconstructed from the successful installation log. The workflow also publishes the original report and `pip freeze` snapshot as a downloadable artifact; artifacts expire, while the committed results remain available. To reproduce the Linux package snapshot, install `python -m pip install -r reports/benchmark-requirements.txt`, then run commands from the checkout. The default extra pins the main ML packages; the snapshot pins transitive versions for Python 3.12 on Linux and may not suit other Python/platform versions.

The [retrieval benchmark workflow](.github/workflows/retrieval-benchmark.yml) runs on relevant pushes to `main` and supports manual runs in GitHub's Actions tab. It installs the CPU wheel, benchmarks all three methods and tests offline model reuse. Application CI also verifies the browser, Docker and PostgreSQL integrations.

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
| 4 | Cross-encoder reranking and constraint handling | Compare all three methods; record latency and costs; test required/preferred distinctions | Implemented |
| 5 | FastAPI and browser evidence/skill-gap interface | Quotes trace to sources; gaps and learning priorities do not invent qualifications | Verified by browser CI |
| 6 | PostgreSQL/pgvector, ingestion, Docker and CI | Permitted provenance, validation, duplicate controls, privacy and integration checks | Implemented; Docker/database CI passed |
| 7 | Review workflow, MLflow, architecture and demo materials | Human review and deployment validation before public release | Release materials implemented; human review/public deployment pending |
| 8 | User-selected job comparison and weekly interview preparation | Exact listing evidence, gaps, manual qualification review, practice questions and seven-day budget | Implemented; API and browser CI passed |
| 9 | Simplified user workflow and confirmation handling | Separate task tabs, clear feedback, no searches on partially confirmed profiles | Implemented; browser and API verification passed |

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

## Step 4: cross-encoder and explicit constraints

```sh
python -m jobmatch search "Python Django backend" --approach reranked
python -m jobmatch search "Python Django backend" --context data/sample_context.json
python -m jobmatch compare --output reports/three-way-comparison.json
```

Semantic retrieval shortlists up to 20 jobs; a fixed `cross-encoder/ms-marco-MiniLM-L6-v2` revision reranks query–description pairs using raw logits. Scores are not hiring probabilities. The initial corpus has only 12 jobs, so all are shortlisted; larger-corpus shortlist recall remains unmeasured.

The [successful Step 4 run](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37591312648) passed all 18 tests. All timings below come from the same Linux run, with 300 queries per method:

| Approach | NDCG@10 | Precision@5 | p95 retrieval |
| --- | ---: | ---: | ---: |
| TF-IDF | 0.9867 | 0.4667 | 0.0520 ms |
| Embeddings | 0.9929 | 0.4667 | 18.5767 ms |
| Retrieval + cross-encoder | 0.9909 | 0.4667 | 248.8277 ms |

Reranking underperformed embeddings on this provisional fixture and was slower. Paid API cost remains US$0; infrastructure cost is unmeasured. [Full report and provenance](reports/three-way-comparison.json).

Context JSON accepts confirmed skill names, explicit relevant years, allowed locations and work modes. Explicit conflicts are demoted, then required-skill coverage is considered, followed by model score. This rule layer is separate from the three-model benchmark and has no measured accuracy improvement claim. Unknown preferences remain unknown. Location comparison is exact; country-wide remote jobs still need the relevant allowed location. Requirement extraction supports labeled `Required:`/`Preferred:` sections and a limited vocabulary. Complex negation, alternatives, headings and role-specific experience still need manual review.

## Step 5: working local interface

```sh
python -m pip install -e ".[resume,web]"
python -m uvicorn jobmatch.api:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open [the local demo](http://127.0.0.1:8000). Download the fictional sample, upload it, correct the skills/experience/education fields and confirm the profile. Then search, choose an approach and enter optional constraints. Each match shows required versus preferred requirements, quotations, supported strengths, not-evidenced requirements and up to three learning priorities. New user-entered qualifications have no fabricated PDF quotations.

The UI uses HTML/CSS/JavaScript served by FastAPI rather than Streamlit, keeping the editable profile and evidence flow in one application. Keyword mode needs no model packages; semantic/reranked modes require `.[semantic]`. Routes include `/health`, `/profiles`, `/profiles/{id}`, `/search` and `/openapi.json`. The API rejects invalid payloads, foreign origins and unrecognized hosts, and uses `Cache-Control: no-store`. The UI renders text without interpreting résumé/job content as HTML.

Deletion removes stored PDF/profile files and clears the browser view. The tab remembers only the profile ID in session storage to recover after refresh. Closing the tab does not delete server files; use deletion or the CLI. This single-user local demo has no authentication, encrypted storage or resource-isolated PDF workers. Bind to loopback and do not expose personal résumé uploads publicly.

Local verification passed 16 tests, including API upload → confirm → evidence/search → delete; four model tests skip locally. The [browser CI run](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37596398785) passed upload, correction, evidence, refresh recovery and deletion checks, with no JavaScript errors. Its `interface-proof` artifact contains a full-page screenshot. The desktop helper was unavailable; visual automation ran in CI.

## Step 6: ingestion, optional database and packaging

Import only listings you are permitted to use. The manual JSON format requires `provenance.kind`, `source` and `permission`; the software records your declaration rather than independently establishing a legal permission. No scraping is implemented.

```sh
python -m jobmatch ingest data/sample_listing_import.json
```

This writes a separate catalog under ignored `private_data/`, leaving the evaluation corpus unchanged. Set `JOBMATCH_JOB_DATA` to that catalog's absolute path before starting the API, and restart after changes. Imports reject invalid work modes, duplicate IDs, normalized exact duplicate listings and lexical near duplicates (token-set Jaccard >= 0.90). This is a limited duplicate heuristic, not a semantic duplicate detector.

```sh
docker compose up --build -d
```

The default image runs keyword matching and PDF profiles without model downloads. It runs as a non-root user, persists profiles in a named volume and publishes only on loopback. Open `http://127.0.0.1:8000`. For optional models set `ENABLE_SEMANTIC=true` before building; the Docker build installs the CPU wheel. Model downloads occur on first semantic use and persist in their own volume. `docker compose down` retains data volumes; profile deletion operates within the app volume. Do not remove volumes unless you intend to erase their contents. Docker is unavailable in this desktop environment; build/runtime checks run in GitHub Actions.

The optional database service is started separately:

```sh
docker compose --profile postgres up -d postgres
python -m pip install -e ".[database,semantic]"
```

Set `DATABASE_URL` to the local demo database (`postgresql://jobmatch:local_demo_only@localhost:5432/jobmatch` with the default local-only configuration), then run `python -m jobmatch index-postgres`. Set `JOBMATCH_PGVECTOR=1` before running semantic search or the API to use persisted cosine search. For an imported catalog use `index-postgres --jobs private_data/jobs.json` and the same catalog when starting the API. All SQL values use bound parameters. Catalog fingerprints and the model revision prevent stale/mismatched embeddings being returned. The local default password is a demonstration value, not a production credential.

The pgvector implementation performs exact search. It still constructs an in-memory encoder/index during startup; removing that redundant startup encoding and adding approximate indexes are future scale improvements. Old versioned catalogs remain stored; there is no database retention policy yet. Résumé profiles stay in the local file store rather than PostgreSQL. See the [pgvector reference](https://github.com/pgvector/pgvector) for its cosine operator and exact/approximate search behavior.

Application CI verifies keyword/PDF/API tests, a Chromium workflow, a Docker health/page smoke check and an ephemeral PostgreSQL vector ordering/stale-catalog check. The separate retrieval workflow downloads both real models and benchmarks all three methods. Database tests and model tests skip unless explicitly enabled, so a dependency-free local test run is not equivalent to full CI.

## Step 7: release materials and honest completion status

### Incremental step: portable model setup

If direct Hugging Face transfers are unreliable, manually run **Portable model bundle** in GitHub Actions and download its `portable-model-bundle` artifact. The workflow checks the public model cards' Apache-2.0 declarations, retains attribution/license material and bundles the exact pinned revisions. It contains model files only, with no profiles or résumés. Install an artifact from this repository's trusted workflow with `python scripts/install_model_bundle.py path/to/portable-model-bundle.zip`. The installer validates identities, paths, size limits and every file checksum before writing the local cache; it does not establish trust in an arbitrary third-party manifest. Dependencies from `.[semantic]` are still required. Restart the app after installation. The bundle expires after seven days and can be regenerated.

Interrupted runtime model downloads now return an actionable JSON error and leave keyword search available. These setup changes have dedicated checksum/path and download-error tests. Full local model verification is reported separately after actual searches succeed.

The [portable bundle run](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37731607365), [Application checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37731504775), and [real-model benchmark](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37731504746) passed at implementation commit `6781712`. Locally, 28 tests passed with five optional model/database tests skipped. Generated bundles, caches and private profiles are excluded from Git.

After installing the bundle in the development workspace, all three approaches passed actual API searches with a confirmed local résumé profile: each returned five matches, and every returned résumé evidence quotation matched its stored source text exactly. The model-enabled offline test suite passed **32 tests**, with only the PostgreSQL integration test skipped locally. No résumé/profile data or private verification reports were committed.

Warm local API timing over 20 sequential searches per approach, using one profile and the 12 fictional jobs:

| Approach | Warm p95 response time |
| --- | ---: |
| TF-IDF | 44 ms |
| Embeddings | 227 ms |
| Retrieval + reranker | 2,927 ms |

These small-sample timings include HTTP, profile loading, ranking, constraints and evidence assembly on this desktop. They are not deployed latency or relevance measurements. Initial embedding-model loading took about 33 seconds before warming; first-use initialization is excluded from the table. Paid API cost was zero; infrastructure cost remains unmeasured. Reranking is slower and does not necessarily improve this fixture's ordering.

To use the installed bundle without model-network requests, set `HF_HUB_OFFLINE=1` before starting the server. To run model tests after installing dependencies and cache files:

```powershell
$env:JOBMATCH_RUN_MODEL_TESTS = '1'
$env:HF_HUB_OFFLINE = '1'
python -m unittest discover -s tests -v
```

### Incremental fix: real résumé upload feedback

Each search approach now has its own initialization/inference lock. A slow semantic model download no longer holds the keyword search lock. Validation: 25 local tests passed, with five optional model/database tests skipped; a concurrency regression test holds semantic initialization open and confirms a keyword request still completes. Optional model dependencies are installed in the development workspace; first-use model-weight verification remains separate from installation.

The interface now disables semantic/reranked choices when their optional model dependencies are missing and labels them `setup required`. `/health` reports dependency availability; it does not claim models are downloaded or usable until a search succeeds. The interface script is UTF-8. Validation: 24 local tests passed, with five optional model/database tests skipped, including missing-dependency reporting.

Browser verification targets the search status explicitly because profile feedback has its own live status region. Local semantic/reranked installation and first-use downloads must finish before these modes are considered locally verified; a successful CI model benchmark does not establish that a particular desktop has installed them.

The [follow-up Application checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37607925398) passed the corrected UTF-8 interface and browser confirmation/evidence flow, Docker checks and PostgreSQL integration at implementation commit `688556c`.

Summary employment extraction now recognizes explicit role-at-employer statements when no experience section was extracted. It keeps an exact source sentence (including PDF line wrapping) as evidence and displays a single-line draft for correction. These entries are unconfirmed; no dates, duration or employment from projects are inferred. Validation: 23 local tests passed, with five optional model/database tests skipped, including a regression check for wrapped summary statements.

PDF selection, extraction, profile confirmation and job search are separate actions. Upload feedback now appears beside the profile controls, including extraction progress and the next action. Common headings such as `Professional Summary`, `Key Projects` and `Education & Certifications` are recognized. Combined education/certification entries remain source lines requiring review, and projects are not converted into employment experience. Existing confirmed profiles are preserved; parser changes apply to new imports. Validation: 22 local tests passed, with five optional model/database tests skipped.

The [architecture diagram](docs/architecture.md), [two-minute demo instructions](docs/demo.md), failure cases and [36-pair human review worksheet](data/review_worksheet.csv) are prepared. Watch the [captioned two-minute demo](reports/two-minute-demo.webm) or view the [interface screenshot](reports/ui-demo.png), recorded with fictional data by Application CI. These are also available in its `interface-proof` artifact. A blank worksheet cannot be applied as reviewed evaluation; grade, reviewer, rationale and exact evidence are required for every pair. Use the [review commands](docs/evaluation.md) to produce a reviewed fixture and benchmark it separately.

Optional local experiment tracking:

```sh
python -m pip install -e ".[semantic,tracking]"
python -m jobmatch compare --output reports/experiment.json --mlflow-dir private_data/experiments
```

MLflow stores metrics, fixture fingerprint, label status and the JSON report in a local experiment database/artifact store. Tracking is optional and needs no paid credentials. CI verifies logging while running the real-model benchmark.

Release verification: 21 local tests passed, with five model/database tests skipped locally. The [Application checks](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37599353568) passed browser upload/correction/search/evidence/refresh/deletion, Docker startup and PostgreSQL checks. The [Retrieval benchmark](https://github.com/Raimal-Raja/jobmatch-ml-platform/actions/runs/37599353582) passed real-model verification, three-method evaluation and SQLite MLflow logging. These runs verified implementation commit `2db59b3`; the subsequent release update adds documentation and recorded media.

The functional local demo and engineering release materials are implemented. **The original full release is not yet complete:** an expanded human-reviewed evaluation, production upload isolation/authentication, a configured public hosting target and deployed end-to-end latency/cost measurements remain. The current corpus remains 12 fictional jobs and three profiles. Docker/loopback deployment is the supported demo mode; no public deployment or validated real-world accuracy is claimed. Résumé achievement numbers must keep these qualifications.

---

## Setup and repository reference

### Project structure

- [Dockerfile](Dockerfile)
- [compose.yaml](compose.yaml)
- [data](data)
- [docs](docs)
- [jobmatch](jobmatch)
- [pyproject.toml](pyproject.toml)
- [reports](reports)
- [scripts](scripts)
- [tests](tests)
- [web](web)

### Getting started

```bash
git clone https://github.com/Raimal-Raja/jobmatch-ml-platform.git
cd jobmatch-ml-platform
```

Create an isolated Python environment and follow the existing workflow sections above. Core installation:

```bash
python -m venv .venv
python -m pip install -e .
```

Activate the virtual environment before installing or running commands. Optional capabilities need the extras listed in pyproject.toml.

Start the API with the web extra installed: `python -m uvicorn jobmatch.api:app --host 127.0.0.1 --port 8000`. Follow the original workflow sections above for profile review, job comparison, and evaluation.

### Configuration and limitations

Keyword mode runs without model weights. Semantic/reranked search needs the semantic extra and downloaded models. PostgreSQL checks are optional. Follow the profile confirmation, private-data and evaluation limitations documented above.

### Validation

Audit: 2026-10-08. Repository structure, setup instructions and description were reviewed. 34 existing Python files passed syntax checks; changed files and new regression tests were checked separately. 1 JavaScript files passed node --check; JSX/TypeScript production builds were not run. 41 regression tests passed; 5 optional model/database tests were skipped. Syntax checks do not establish full runtime correctness. External APIs, live scraping, GUI interaction, notebook training and production deployment were not comprehensively exercised.

```bash
python -m unittest discover -s tests -v
```

### Repository description

The short GitHub description is provided in [REPOSITORY_DESCRIPTION.md](REPOSITORY_DESCRIPTION.md).

### Contributions

Describe the issue, reproduction steps, environment, and expected behavior when proposing a change. Keep generated environments, credentials, and unnecessary build artifacts out of new commits.

### License

No top-level license file was found during this review.
