"""Single-user local demonstration API and evidence-based interface."""
import threading
import os
from importlib.util import find_spec
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .constraints import apply_constraints, validate_context
from .profiles import ProfileStore
from .retrieval import ROOT, load_jobs
from .semantic import make_retriever


class Corrections(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skills: list[str]
    experience: list[str]
    education: list[str]


class Search(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(default="", max_length=10000)
    profile_id: str | None = None
    approach: Literal["tfidf", "semantic", "reranked"] = "tfidf"
    context: dict = Field(default_factory=dict)
    limit: int = Field(default=5, ge=1, le=10)


class TargetJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=30000)
    source_url: str = Field(default="", max_length=2000)
    location: str = Field(default="", max_length=200)
    work_mode: Literal["", "remote", "hybrid", "onsite"] = ""


class TargetComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str
    listing: TargetJob
    additional_skills: list[str] = Field(default_factory=list, max_length=50)
    context: dict = Field(default_factory=dict)
    minutes_per_day: int = Field(default=90, ge=15, le=240)


class DiscoveryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(min_length=1, max_length=120)
    company: str = Field(default="", max_length=200)
    country: str = Field(default="", max_length=200)
    city: str = Field(default="", max_length=200)
    work_mode: Literal["", "remote", "hybrid", "onsite"] = ""
    provider: Literal["auto", "all", "remotive", "arbeitnow", "arbeitnow-uk", "google"] = "auto"
    profile_id: str | None = None


class IntegrationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nvidia_key: str = Field(default="", max_length=500)
    search_key: str = Field(default="", max_length=500)


class AIRewrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent: bool = False


class ResumeExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=50000)


def create_app(store=None, jobs=None, discovery=None):
    app = FastAPI(title="JobMatch", version="0.5.0", docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
    store = store or ProfileStore()
    from .discovery import JobDiscovery
    discovery = discovery or JobDiscovery(store.root.parent / 'provider_cache')
    jobs = jobs or load_jobs(os.environ.get("JOBMATCH_JOB_DATA", ROOT / "data/jobs.json"))
    cache = {}
    lock = threading.RLock()
    search_locks = {name: threading.RLock() for name in ("tfidf", "semantic", "reranked")}

    @app.middleware("http")
    async def local_origin_and_privacy(request, call_next):
        # A local personal-data demo: refuse cross-origin browser writes.
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin access denied"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Profile not found"}, status_code=404)

    @app.get("/")
    def index():
        return FileResponse(ROOT / "web/index.html")

    @app.get("/assets/{name}")
    def asset(name: Literal["app.js", "style.css"]):
        return FileResponse(ROOT / "web" / name)

    @app.get("/health")
    def health():
        model_dependencies = all(find_spec(name) is not None for name in ("torch", "sentence_transformers"))
        return {"status": "ok", "jobs": len(jobs),
                "search_modes": {"tfidf": True, "semantic": model_dependencies, "reranked": model_dependencies},
                "integrations": {"google_jobs": bool(os.environ.get('SERPAPI_API_KEY')), "nvidia": bool(os.environ.get('NVIDIA_API_KEY'))},
                "model_notice": "Model modes need installed dependencies and a first-use model download; availability does not guarantee cached models."}

    @app.post('/integrations')
    def configure_integrations(body: IntegrationSettings):
        if not body.nvidia_key.strip() and not body.search_key.strip():
            raise ValueError('Enter a replacement NVIDIA key or a SerpAPI search key')
        for name, value in (('NVIDIA_API_KEY', body.nvidia_key), ('SERPAPI_API_KEY', body.search_key)):
            if value.strip():
                if any(character.isspace() for character in value.strip()):
                    raise ValueError('Keys cannot contain whitespace')
        for name, value in (('NVIDIA_API_KEY', body.nvidia_key), ('SERPAPI_API_KEY', body.search_key)):
            if value.strip():
                os.environ[name] = value.strip()
        return {'message': 'Configured for this server session only. Keys are not saved to files or returned.',
                'integrations': {'google_jobs': bool(os.environ.get('SERPAPI_API_KEY')), 'nvidia': bool(os.environ.get('NVIDIA_API_KEY'))}}

    @app.get("/sample-resume")
    def sample():
        return FileResponse(ROOT / "data/sample_resume.pdf", media_type="application/pdf")

    @app.post("/profiles")
    async def upload(request: Request):
        chunks = bytearray()
        async for chunk in request.stream():
            chunks.extend(chunk)
            if len(chunks) > 10 * 1024 * 1024:
                raise HTTPException(413, "PDF exceeds 10 MiB limit")
        # Parse off the event loop. Local demo still needs process isolation before public uploads.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(store.create_bytes, bytes(chunks))

    @app.get("/profiles/{profile_id}")
    def get_profile(profile_id: str):
        return store.get(profile_id)

    @app.get('/profiles/{profile_id}/ats-check')
    def ats_check(profile_id: str):
        from .ats import check_resume
        return check_resume(store.get(profile_id))

    @app.get('/profiles/{profile_id}/rewrite')
    def rewrite(profile_id: str):
        from .rewrite import draft_resume
        return draft_resume(store.get(profile_id))

    @app.post('/profiles/{profile_id}/rewrite-export')
    def rewrite_export(profile_id: str, body: ResumeExport):
        from .rewrite import docx_bytes
        if not store.get(profile_id).get('reviewed'):
            raise ValueError('Confirm your profile before exporting a rewrite')
        return Response(docx_bytes(body.text), media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        headers={'Content-Disposition': 'attachment; filename="ResumeDraft.docx"'})

    @app.post('/profiles/{profile_id}/ai-rewrite')
    def ai_rewrite(profile_id: str, body: AIRewrite):
        from .optional_ai import generate_draft
        return generate_draft(store.get(profile_id), body.consent)

    @app.post('/discover-jobs')
    def discover_jobs(body: DiscoveryQuery):
        query = body.model_dump(exclude={'profile_id'})
        profile = store.get(body.profile_id) if body.profile_id else None
        if profile and not profile.get('reviewed'):
            raise ValueError('Confirm your résumé before finding matches')
        if body.provider == 'google' or body.provider == 'auto' and os.environ.get('SERPAPI_API_KEY'):
            from .google_jobs import search_google
            result = search_google(query)
            if result['status'] in ('setup_required', 'source_unavailable'):
                fallback = discovery.search({**query, 'provider': 'all'})
                fallback['google_url'] = result['google_url']
                fallback['message'] = result['message'] + ' Checked permitted providers instead. ' + fallback['message']
                result = fallback
        else:
            result = discovery.search({**query, 'provider': 'all' if body.provider == 'auto' else body.provider})
            if body.provider == 'auto' and body.company and not os.environ.get('SERPAPI_API_KEY'):
                from .google_jobs import search_google
                result['google_url'] = search_google(query)['google_url']
                result['message'] = 'Company web search needs a SerpAPI key. Only limited permitted-provider records were checked. ' + result['message']
        if profile:
            from .targeted import compare_target
            for job in result['jobs']:
                comparison = compare_target(profile, {'title': job['title'], 'company': job['company'], 'description': job['description'],
                    'source_url': job['source_url'], 'location': job['location'], 'work_mode': job['work_mode']})
                job['match_preview'] = {'supported': [item['skill'] for item in comparison['skills'] if item['status'] == 'supported'],
                    'not_evidenced': [item['skill'] for item in comparison['skills'] if item['status'] != 'supported'],
                    'notice': 'Recognized skills only; select the listing for exact evidence and your preparation week.'}
        return result

    @app.put("/profiles/{profile_id}")
    def update_profile(profile_id: str, body: Corrections):
        with lock:
            return store.update(profile_id, body.model_dump())

    @app.delete("/profiles/{profile_id}")
    def delete_profile(profile_id: str):
        with lock:
            store.delete(profile_id)
        return {"deleted": profile_id}

    @app.post("/search")
    def search(body: Search):
        context = dict(body.context)
        validate_context(context)
        profile = None
        query = body.query
        if body.profile_id:
            profile = store.get(body.profile_id)
            if not profile.get("reviewed"):
                raise ValueError("Review and confirm your résumé before finding matches")
            query = store.search_text(body.profile_id) + ("\n" + query if query else "")
            context["skills"] = [item["value"] for item in profile["skills"] if item["confirmed"]]
        if not query.strip():
            raise ValueError("Enter a query or confirm a résumé profile")
        with search_locks[body.approach]:
            if body.approach not in cache:
                try:
                    cache[body.approach] = make_retriever(jobs, body.approach)
                except (ImportError, OSError, RuntimeError) as exc:
                    raise HTTPException(503, "Model loading failed. Check model dependencies and downloads; keyword search remains available.") from exc
            results = cache[body.approach].search(query, min(20, len(jobs)))
        results = apply_constraints(results, context)[:body.limit]
        if profile:
            for row in results:
                for requirement in row["assessment"]["required"] + row["assessment"]["preferred"]:
                    requirement["resume_evidence"] = [item for item in profile["skills"] if item["confirmed"] and item["value"].lower() == requirement["skill"].lower()]
        return {"approach": body.approach, "score_notice": "Ranking signals, not probabilities of getting hired", "results": results}

    @app.post("/compare-target")
    def compare_target_job(body: TargetComparison):
        from .targeted import compare_target
        return compare_target(store.get(body.profile_id), body.listing.model_dump(), body.context,
                              body.additional_skills, body.minutes_per_day)

    return app


app = create_app()
