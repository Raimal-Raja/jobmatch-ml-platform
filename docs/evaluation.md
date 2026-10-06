# Evaluation protocol — Step 1

The sample contains 12 hand-authored fictional listings and three fictional profiles (36 fully labeled pairs). No personal résumé data or scraped listings are included. The labels are agent-authored provisional judgments, **not a manually reviewed human evaluation set**. A human reviewer must review every pair before treating the metrics as validated results.

## Relevance rubric

- **3:** Core role and required skills align, experience meets the stated minimum, and location/work mode is compatible.
- **2:** Relevant role with a small required-skill gap that can reasonably be addressed; experience and location fit.
- **1:** Some transferable skills, but a major required skill, experience, or location constraint is unmet.
- **0:** Unrelated role or negligible evidence for core requirements.

Preferred skills cannot substitute for missing required skills. Projects cannot be treated as production experience. Unstated qualifications remain unknown. Grades measure suitability under this rubric, not hiring probability.

For human review, record profile ID, job ID, final grade, exact supporting profile/job quotations, reviewer and rationale in a separate review artifact. Resolve disagreements before publishing validated results. The current fixture is small and intentionally simple; it cannot establish generalization or statistical significance.

## Metrics and leakage controls

NDCG@10 uses gains `2^grade - 1` and discounts `log2(rank + 1)`. Precision@5 counts grades >= 2, always dividing by five even when fewer results return. Metrics are macro-averaged over profiles. Unknown terms and zero-overlap jobs do not yield results.

The baseline fits IDF on the retrieval job corpus only. Evaluation profiles are never used to fit vocabulary or IDF. There is no supervised training in Step 1. Reject duplicate IDs and normalized exact listings at load time. Near-duplicate clustering and frozen train/development/test splits are required before future reranker training or model selection; keep evaluation profiles and duplicate job families outside training.

Latency is the nearest-rank p95 across 100 warm searches per profile (300 samples). It excludes index construction, disk I/O, HTTP and interface time; it is not a deployed service latency claim. Paid API cost is zero. Infrastructure cost is unknown until deployment costs and search volume are measured.

## Known failures

TF-IDF counts lexical overlap. It does not enforce location, experience or remote-work constraints, distinguish required from preferred skills, recognize synonyms, or understand negation. A senior listing can rank highly despite an experience gap. Scores are ranking signals only. This step generates no match explanations or learning plans.
