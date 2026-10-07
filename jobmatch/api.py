"""Single-user local demonstration API and evidence-based interface."""
import threading
import os
from importlib.util import find_spec
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
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


def create_app(store=None, jobs=None):
    app = FastAPI(title="JobMatch", version="0.5.0", docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
    store = store or ProfileStore()
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
                "model_notice": "Model modes need installed dependencies and a first-use model download; availability does not guarantee cached models."}

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
            query = store.search_text(body.profile_id) + ("\n" + query if query else "")
            context["skills"] = [item["value"] for item in profile["skills"] if item["confirmed"]]
        if not query.strip():
            raise ValueError("Enter a query or confirm a résumé profile")
        with search_locks[body.approach]:
            if body.approach not in cache:
                try:
                    cache[body.approach] = make_retriever(jobs, body.approach)
                except (ImportError, OSError) as exc:
                    raise HTTPException(503, "Optional model unavailable; install semantic dependencies and download the model") from exc
            results = cache[body.approach].search(query, min(20, len(jobs)))
        results = apply_constraints(results, context)[:body.limit]
        if profile:
            for row in results:
                for requirement in row["assessment"]["required"] + row["assessment"]["preferred"]:
                    requirement["resume_evidence"] = [item for item in profile["skills"] if item["confirmed"] and item["value"].lower() == requirement["skill"].lower()]
        return {"approach": body.approach, "score_notice": "Ranking signals, not probabilities of getting hired", "results": results}

    return app


app = create_app()
