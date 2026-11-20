---
id: WS3-05
title: Add replacement catalogue and bounded severance retry loop
workstream: WS3
status: done
owner: claude-3
priority: P0
depends_on: [WS3-03, WS3-04]
blocks: [WS3-07]
files: [skyshift/sever.py, skyshift/catalogue/replacements.yaml, tests/ws3/test_replacement_loop.py]
estimate: 45m
claimed_at: "2026-11-20T12:54:19+00:00"
updated_at: "2026-11-20T12:57:19+00:00"
---

## Goal
Catalogue a demo-safe European/open replacement for the blocked telemetry dependency and implement a bounded, evidence-preserving severance retry flow.

## Context
Use `tasks/contracts.md` headings Python API and Severance. Replacements are deterministic catalogue entries; model explanation is advisory and never decides checks. Preserve red initial events when a later config-only retry becomes green. Default maximum is two attempts; exhaustion returns `blocked`, and unknown dependencies remain manual. Root proposal sections 3, 4, 6, 7, 9 and 10 specify the telemetry fixture, AI recommendation and fallback. Dependencies on WS3-03 and WS3-04 are required to compose enforcement and radar evidence.

## Steps
1. Add a small YAML replacement catalogue with stable IDs, replacement descriptions, allowed config-key names and explicit synthetic/demo provenance; do not invent tested availability. Implement a bounded loopback-only demo telemetry receiver in sever.py compatible with the fixture's configured telemetry protocol, with explicit startup/cleanup and a deterministic receipt check. Describe it honestly as a local demo replacement, not a deployed OpenTelemetry collector. No external service deployment is required; unknown protocols remain manual/incomplete.
2. Implement deterministic selection of a catalogue entry for a known blocked dependency; unknown dependency yields a manual/open item.
3. Implement a maximum-attempt-bounded loop using config-only changes, preserving initial blocked events and each attempt in the final contract envelope. Request explanatory/catalogue-choice proposals only through `skyshift.llm.complete`, validate the selected ID/config-key names against the local catalogue, and never accept arbitrary model endpoints or commands. Missing client/schema leaves proposals incomplete; deterministic code owns every check. Consume WS2 run_app through the stable contract when integrated at WS3-07; use injected adapters here, never edit WS2 files.
4. Test success on the allowed retry, exhaustion, unknown dependency, invalid attempt limits and retention of the original denial.

## Acceptance criteria
- `python -m unittest tests.ws3.test_replacement_loop` exits 0 with at least five cases.
- A two-attempt fixture run preserves first-attempt blocked event and reports final `green` only when the second attempt's required deterministic checks pass; exhaustion reports `blocked`.
- No live service call, real provider claim, model verdict or edit to `app.py` occurs.

## Out of scope
Editing fixture application code, deployment of OpenTelemetry, LLM prompting/client implementation, real external endpoint testing and modifying shared contracts.

## Fallback if blocked
Return `blocked` with manual action needed and preserve evidence; ask WS4 through its inbox for shared interface changes rather than changing shared files.

## Log
- 2026-11-20 — Planned; no implementation or VM validation performed.
- 2026-11-20T12:54:19+00:00 — Claimed by claude-3 (Claude Code); loop composes WS3-03 proxy + WS3-04 radar with an injected app runner (fixture app not yet on main), loopback receiver, replay-only proposals.
- 2026-11-20T12:57:19+00:00 — Done (offline/loopback scope). Code in ac7a0f8: replacements.yaml local-otel gains host patterns (monitoring[.*].amazonaws.com), protocol http-post, config template http://127.0.0.1:{port}, allowed_config_keys, synthetic/demo provenance, code_change false. sever.py adds load_catalogue, select_replacement (deterministic fnmatch), TelemetryReceiver (127.0.0.1 HTTP POST, 1 MiB cap, counts path/bytes, discards bodies; explicitly not an OTel collector), run_severance (1..5 attempts; per attempt: receiver + EgressProxy + background radar sampler around one injected app_runner call; NO_PROXY empty; first denial preserved; unknown host -> manual + blocked; same fix twice/exhaustion -> blocked; runner crash or unavailable radar -> incomplete; proposals only via llm.complete-shaped proposer, schema enum-limited to catalogue IDs/keys, deterministic choice kept on disagreement/failure). sever() public envelope unchanged; non-stub sever() stays incomplete until WS3-07 wires WS2 run_app.
  - Acceptance on fresh WSL2 Ubuntu clone at ac7a0f8 (Python 3.12.3): `python3 -B -m unittest tests.ws3.test_replacement_loop` 10 OK (red->config-only->green with denial retained and receiver receipt, exhaustion max 1 and stubborn app, unknown dependency manual/blocked, invalid limits, rogue/broken/absent proposer, radar bypass FAIL, crashing runner/unavailable radar incomplete, sever entry unchanged); all tests/ws3 63 OK; board --check OK. Windows/Python 3.14.5: 2 full runs OK.
  - Limitations: app runner is a test fake, not the fixture app (fixtures/aws_workload not on main yet); synthetic ranges only; no live DNS/feed/model/VM. Live PASS is possible from run_severance only with a real runner; WS3-07 owns that verification. Executor-verified; Francisco may reopen.
