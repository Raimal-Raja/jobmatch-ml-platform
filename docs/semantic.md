# Step 3 semantic retrieval

The semantic retriever runs `sentence-transformers/all-MiniLM-L6-v2` locally on CPU. The model revision is fixed in `jobmatch/semantic.py`. It embeds job titles and descriptions once per retriever instance, then embeds each query on every search. Unit-normalized embeddings make a dot product equivalent to cosine similarity. Model loading uses `trust_remote_code=False`.

Both methods rank the same job corpus and use the same profiles, relevance labels and shared metric functions. TF-IDF drops zero-overlap listings; dense retrieval ranks all listings, including low-similarity candidates. Neither method enforces hard eligibility constraints. Cosine scores are not calibrated probabilities and are not comparable across methods.

The first semantic run downloads public model files from Hugging Face into ignored `.model_cache/`. Résumé text is encoded locally and is not sent to a hosted inference API. Use `--offline` after the model is cached to require local model files. There is no query embedding cache: timing repeated profiles still measures model inference. There is no fine-tuning or label-based parameter selection in this step.

The comparison report records the fixed model revision, package versions, device, thread count, embedding dimension and maximum token sequence length. Text beyond the model token limit is truncated by the encoder; this can omit qualifications in long profiles or descriptions. Chunking is a future improvement. Model weights and cached vectors are not committed to Git.

`setup_seconds` includes retriever construction, job encoding and, on the first run, package imports/download time. Search p95 excludes setup and includes query encoding and scoring against the precomputed corpus. Warmup occurs once per profile before latency measurement. Benchmark execution is sequential on a tiny corpus; repeat timing on the deployment hardware and representative data before drawing capacity conclusions. The fixture SHA-256 fingerprints the canonical JSON of jobs, profiles and labels.

The fixture remains agent-authored and provisional. A higher score on three toy profiles cannot demonstrate generalization, and a worse semantic result must be reported honestly. Expand human-reviewed held-out data before selecting a model. Neither synonyms nor semantic scores imply possessed skills, production experience or a hiring outcome.

Implementation reference: [SentenceTransformer API](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html).
