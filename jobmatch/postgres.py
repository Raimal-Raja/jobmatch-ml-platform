"""Optional versioned pgvector catalog; exact cosine search for small datasets."""
import hashlib
import json
import math
import os
from .retrieval import validate_jobs
from .semantic import MODEL, REVISION, SemanticRetriever


def catalog_hash(jobs):
    return hashlib.sha256(json.dumps(jobs, sort_keys=True).encode()).hexdigest()


def vector_text(vector):
    values = [float(value) for value in vector]
    if len(values) != 384 or not all(math.isfinite(v) for v in values) or not any(values):
        raise ValueError("Embedding must have 384 finite values and nonzero norm")
    return json.dumps(values)


class PgvectorStore:
    def __init__(self, dsn=None):
        self.dsn = dsn or os.environ.get("DATABASE_URL")
        if not self.dsn:
            raise ValueError("Set DATABASE_URL for PostgreSQL")

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise ValueError('Install PostgreSQL support with pip install -e ".[database]"') from exc
        return psycopg.connect(self.dsn, connect_timeout=10)

    def upsert(self, jobs, vectors):
        validate_jobs(jobs)
        if len(jobs) != len(vectors):
            raise ValueError("Every listing needs an embedding")
        encoded = [vector_text(vector) for vector in vectors]
        fingerprint = catalog_hash(jobs)
        from psycopg.types.json import Jsonb
        with self._connect() as connection:
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute("CREATE TABLE IF NOT EXISTS jobmatch_embeddings (model text NOT NULL, catalog text NOT NULL, job_id text NOT NULL, payload jsonb NOT NULL, embedding vector(384) NOT NULL, PRIMARY KEY(model,catalog,job_id))")
            for job, vector in zip(jobs, encoded):
                connection.execute("INSERT INTO jobmatch_embeddings VALUES (%s,%s,%s,%s,%s::vector) ON CONFLICT(model,catalog,job_id) DO UPDATE SET payload=EXCLUDED.payload,embedding=EXCLUDED.embedding",
                                   (MODEL + "@" + REVISION, fingerprint, job["id"], Jsonb(job), vector))
        return {"indexed": len(jobs), "catalog_sha256": fingerprint, "model_revision": REVISION}

    def search(self, jobs, vector, limit=10):
        if type(limit) is not int or limit < 1:
            raise ValueError("Limit must be positive")
        encoded = vector_text(vector)
        with self._connect() as connection:
            parameters = (MODEL + "@" + REVISION, catalog_hash(jobs))
            count = connection.execute("SELECT count(*) FROM jobmatch_embeddings WHERE model=%s AND catalog=%s", parameters).fetchone()[0]
            if count != len(jobs):
                raise ValueError("PostgreSQL catalog is missing or stale; run index-postgres")
            rows = connection.execute("SELECT payload,1-(embedding <=> %s::vector) AS score FROM jobmatch_embeddings WHERE model=%s AND catalog=%s ORDER BY embedding <=> %s::vector,job_id LIMIT %s",
                                      (encoded, *parameters, encoded, limit)).fetchall()
        return [{"job": payload, "score": float(score)} for payload, score in rows]


class PgvectorRetriever:
    def __init__(self, jobs, offline=False):
        self.jobs = jobs
        self.encoder = SemanticRetriever(jobs, offline=offline)
        self.store = PgvectorStore()
        self.metadata = {**self.encoder.metadata, "storage": "postgresql_pgvector_exact", "catalog_sha256": catalog_hash(jobs)}

    def search(self, query, limit=10):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must contain text")
        vector = self.encoder.model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        return self.store.search(self.jobs, vector, limit)
