---
id: WS3-01
title: Create contract-honouring severance and LLM stubs
workstream: WS3
status: claimed
owner: claude-3
priority: P0
depends_on: []
blocks: [WS1-05, WS3-02, WS3-04, WS3-06, WS4-01]
files: [skyshift/sever.py, skyshift/llm.py, skyshift/catalogue/replacements.yaml, fixtures/llm/replay.json, fixtures/ip-ranges/ranges.json, tests/ws3/__init__.py, tests/ws3/test_contract_stubs.py]
estimate: 40m
claimed_at: "2026-11-20T12:40:32+00:00"
updated_at: "2026-11-20T12:40:32+00:00"
---

## Goal
Create realistic offline WS3 module stubs that satisfy the public function signatures and envelope shapes before implementation work begins.

## Context
Use `tasks/contracts.md` headings Python API, Shared envelope and paths, Severance, Environment names only, and CLI contract and demo honesty, especially the `sever` and `complete` signatures, severance/replay shapes, and P0 stub exit behavior. Root proposal sections 3, 4, 6, 7, 9 and 10 describe the severance demo and risks; this task restates the portable requirements and does not require the untracked proposal. WS3 owns only the paths listed here and in its contract reservation. Stub results must be synthetic and `incomplete`, never PASS.

## Steps
1. Implement import-safe `sever()` and `complete()` stubs with the exact keyword-only arguments from contracts v1; avoid network, socket, or process activity at import time.
2. Return realistic synthetic attempts/events in the sever envelope with mode `stub` and status `incomplete`. The separate `complete` response has exactly mode/status/data/errors, with mode `replay` and status `incomplete`; `stub` is not an allowed completion mode. Neither function reads credentials, contacts a service or starts a process in its offline path. Non-stub unfinished behavior is explicitly incomplete, never fabricated live success.
3. Add a minimal replacement entry, a documented-format synthetic IP-range fixture, and a deterministic cached response fixture with no secrets or real endpoint data.
4. Add tests/ws3/__init__.py and focused tests proving imports are side-effect free, signatures work, required envelope keys exist, and neither stub can report PASS.

## Acceptance criteria
- `python -m unittest tests.ws3.test_contract_stubs` exits 0 with at least four assertions covering signatures/envelopes, synthetic nonempty content, `incomplete` status and no network at import.
- `python -c "from skyshift.sever import sever; from skyshift.llm import complete; print('WS3 stubs import')"` exits 0 from repository root.
- Review the diff to confirm only listed paths changed and no credentials or live ranges/endpoints were added. Before WS4 supplies tests/__init__.py, run `python -B -m unittest discover -s tests/ws3 -p test_contract_stubs.py -v` rather than relying on dotted imports.

## Out of scope
Real proxying, live IP feeds, socket inspection, model requests, pass/fail decisions, shared contracts, product CLI, dependencies, and running the human VM gate.

## Fallback if blocked
Keep synthetic local fixtures and return the contract's incomplete envelope; record any unavailable package/tool in Log and do not simulate a live PASS.

## Log
- 2026-11-20 — Planned; no implementation or VM validation performed.
- 2026-11-20T12:40:32+00:00 — Claimed by claude-3 (Claude Code); starting offline stubs only.
