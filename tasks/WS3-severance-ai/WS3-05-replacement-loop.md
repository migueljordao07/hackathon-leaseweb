---
id: WS3-05
title: Add replacement catalogue and bounded severance retry loop
workstream: WS3
status: todo
owner: null
priority: P0
depends_on: [WS3-03, WS3-04]
blocks: [WS3-07]
files: [skyshift/sever.py, skyshift/catalogue/replacements.yaml, tests/ws3/test_replacement_loop.py]
estimate: 45m
claimed_at: null
updated_at: null
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
