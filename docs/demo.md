# Two-minute demonstration

The application CI records a roughly two-minute Chromium demonstration with on-screen captions using fictional data. The `interface-proof` artifact contains `two-minute-demo.webm` and `ui-demo.png`. The same script also asserts successful browser behavior. Artifacts have GitHub's default retention and may expire; download and preserve the video for an interview demo.

To record again in a development environment:

```sh
python -m pip install -e ".[resume,web]" playwright
python -m playwright install chromium
python scripts/browser_smoke.py --record-demo
```

The recording covers upload, extraction review, confirmation, explicit preferences, ranked matches, exact evidence, learning priorities, refresh recovery and deletion. It uses keyword mode so no paid credentials or model downloads are needed. Semantic and cross-encoder performance is shown in the benchmark reports, not fabricated from the keyword demo. The video has on-screen captions and no spoken narration.

For a live demonstration, start the API and follow the same flow with `data/sample_resume.pdf`. Explain the failure case: a senior job may have strong text similarity but insufficient explicitly provided experience; constraints demote it. The cross-encoder did not outperform embeddings on this fixture. Evaluation is provisional until a human reviews the worksheet.
