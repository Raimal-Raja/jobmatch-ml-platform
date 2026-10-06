# Step 2 profile contract

Profiles have schema version 1, a random 32-character hexadecimal ID, extracted page texts, candidate fields and warnings. Skill extraction uses a fixed vocabulary. Experience and education retain lines under recognized section headings. No model infers missing credentials, years of experience or seniority.

Every candidate has `value`, `origin`, `confirmed`, and `evidence`. Evidence contains a one-based PDF page, zero-based `start` and exclusive `end` character offsets, and an exact `quote`. Offsets reference the stored extracted page text, not PDF bytes or screen coordinates. An extracted mention is not a verified qualification.

Correction JSON accepts only `skills`, `experience`, and `education`, each a list of up to 100 nonempty strings of at most 2,000 characters. Supplied fields replace existing fields. Exact matches preserve their extraction evidence; new text is attributed to the user and has `evidence: null`. Corrections never modify the original extracted pages. The `reviewed` flag means all remaining candidates are confirmed, not externally verified.

The CLI searches confirmed values only. It rejects a profile with no confirmed text. Personal contact information in raw page text is not automatically included in search. No generated explanations are implemented yet.

The local store is intentionally single-user. It does not implement authentication, encryption, concurrent writes, backup expiry or retention scheduling. JSON replacement is atomic, but import is not a transactional database operation. Deletion removes the imported copy and profile, not originals, external copies or backups. Before public uploads, add authorization, isolated PDF workers with resource/time limits, secure storage and retention controls.
