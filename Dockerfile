FROM python:3.12-slim
WORKDIR /app
ARG ENABLE_SEMANTIC=false
COPY pyproject.toml README.md ./
COPY jobmatch ./jobmatch
RUN pip install --no-cache-dir '.[resume,web]' && \
    if [ "$ENABLE_SEMANTIC" = "true" ]; then \
      pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir '.[semantic]'; \
    fi
COPY data ./data
COPY web ./web
RUN useradd --create-home --uid 1000 app && mkdir -p private_data .model_cache && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3)"
CMD ["python", "-m", "uvicorn", "jobmatch.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
