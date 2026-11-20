---
id: WS3-06
title: Implement one LLM client with local sanitization and cached replay
workstream: WS3
status: done
owner: claude-3
priority: P0
depends_on: [WS3-01]
blocks: [WS3-07]
files: [skyshift/llm.py, fixtures/llm/replay.json, tests/ws3/test_llm_client.py]
estimate: 50m
claimed_at: "2026-11-20T12:57:54+00:00"
updated_at: "2026-11-20T13:00:15+00:00"
---

## Goal
Implement one provider-neutral client path that sanitizes locally before transmission and supports deterministic, visibly labelled cached-response replay.

## Context
Follow `tasks/contracts.md` headings Python API, Environment names only, and CLI contract and demo honesty: `complete(task, payload, schema, *, config, replay=False)` returns the fixed envelope; only synthetic locally sanitized data may leave the VM; no raw environment, source data, credentials or private addresses; replay is visibly labelled and cannot masquerade as live. Root proposal sections 3, 4, 6, 7, 9 and 10 motivate AI explanations, local sanitization and cache fallback. API availability/latency are unverified, so all tests are offline and do not imply a successful live call.

## Steps
1. Implement one client/configuration route only; avoid multiple SDK clients or network calls at import time.
2. Add deterministic local sanitization for known secret-like values, environment key/value material, credentials, signed query strings, and private addresses before any request construction.
3. Load replay responses from the committed synthetic fixture and label mode `replay`; bound timeouts/retries for a live adapter and return `incomplete` on unavailable credentials or transport failure.
4. Add tests proving sanitization occurs before transport, replay is deterministic and labelled, and error paths return incomplete without exposing payload secrets.

## Acceptance criteria
- `python -m unittest tests.ws3.test_llm_client` exits 0 with at least five cases and no external API/network access.
- A fake transport verifies the request receives only the sanitized synthetic payload; assert known secret markers, private IPs and signed query values are absent.
- Replay output contains `mode: replay`; unavailable live credentials/transport produce `status: incomplete`, never PASS.

## Out of scope
Multiple provider clients, model selection policy, live API validation, pass/fail decisions, changes to `.env.example` or shared dependencies, and logging raw prompts/responses.

## Fallback if blocked
Use the committed synthetic replay and label it clearly; preserve deterministic checks as live and report model API unavailability through the WS3 inbox.

## Log
- 2026-11-20 — Planned; no implementation or VM validation performed.
- 2026-11-20T12:57:54+00:00 — Claimed by claude-3 (Claude Code); single OpenAI-compatible stdlib route with injected fake transport in tests, no live API call.
- 2026-11-20T13:00:15+00:00 — Done (offline scope). Code in 5bf6221: skyshift/llm.py now has one route only: OpenAI-compatible POST {SKYSHIFT_LLM_BASE_URL}/chat/completions via stdlib urllib (https required, plain http only for loopback, no URL credentials/query), temperature 0, 20 s timeout, at most 2 transport attempts, 256 KiB response cap. sanitize() runs before request construction: config values, sensitive keys, credential patterns (AKIA/ASIA, bearer, private keys, sk-/pk-, 40-char secret shape), KEY=value env assignments, URL query/userinfo (signed URLs) and non-global IPv4/IPv6 are redacted; 32 KiB payload bound. Live output must parse and validate -> mode live/status ok; malformed/schema failure -> live/incomplete; missing credentials, rejected endpoint, oversized payload or transport failure -> labelled replay/incomplete. Replay (replay=True or SKYSHIFT_LLM_REPLAY) is always replay/incomplete. Errors carry exception types/key names only. fixtures/llm/replay.json unchanged.
  - Acceptance on fresh WSL2 Ubuntu clone at 5bf6221 (Python 3.12.3): `python3 -B -m unittest tests.ws3.test_llm_client` 11 OK (sanitizer categories/determinism, fake transport sees only sanitized body, fenced JSON, schema/malformed incomplete, bounded retries then replay, missing creds no call, insecure/credentialed base URL no call, oversized no call, deterministic labelled replay, unknown task); `tests.ws3.test_contract_stubs` 13 OK; all tests/ws3 74 OK; board --check OK.
  - Limitations: no live API call was made; provider compatibility, EU hosting and latency are unverified (WS3-07/humans). Executor-verified; Francisco may reopen.
