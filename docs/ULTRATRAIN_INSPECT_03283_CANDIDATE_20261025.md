# UltraTrain / Inspect AI 0.3.283 — STAGING 2026-10-25

Missed upstream release (2026-10-21), not a new release on 2026-10-25.

Source: https://github.com/UKGovernmentBEIS/inspect_ai/releases/tag/0.3.283
Schema PR: https://github.com/UKGovernmentBEIS/inspect_ai/pull/5411
Sandbox PR: https://github.com/UKGovernmentBEIS/inspect_ai/pull/6006

Guard reserved dataset field checkpoint; eval_set resume prior-log sandbox injection before 0.3.283; eval_retry remains log-sandbox based; mixed old/new sandbox samples need per-sample provenance. Candidate-only pure-Python policy; 6 synthetic tests committed, not executed on GitHub. Separate full local staging ZIP includes 239/239 offline synthetic tests; do not conflate the two. Neither package is deployed or merged into Compatibility Core. No actual Inspect runtime, sandbox or dataset canary has run. No changes to main.

NEXT: compare real Compatibility Core; run branch CI, isolated Inspect dataset round-trip and sandbox resume canaries, validate lockfile and trust boundaries, review before promotion.
