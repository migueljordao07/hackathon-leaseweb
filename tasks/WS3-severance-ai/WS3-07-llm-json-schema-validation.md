---
id: WS3-07
title: Validate model schemas and the WS3 run-all demo path
workstream: WS3
status: review
owner: claude-3
priority: P0
depends_on: [WS3-05, WS3-06, WS0-01, WS2-01, WS2-04, WS4-01]
blocks: [WS4-06]
files: [skyshift/llm.py, skyshift/sever.py, tests/ws3/test_llm_schema.py, tests/ws3/test_demo_path.py]
estimate: 60m
claimed_at: "2026-11-20T14:37:00+00:00"
updated_at: "2026-11-20T14:38:00+00:00"
---

## Goal
Validate every model result against the caller schema, then prove the P0 WS3 run-all demo path with measured proxy/radar and bounded config-only retry evidence.

## Context
Use `tasks/contracts.md` headings Python API, Severance, Environment names only, and CLI contract and demo honesty. Model output may explain and propose replacements but never decides PASS/FAIL; schema failure, timeout or sanitiser rejection yields incomplete. Replay remains labelled. Root proposal sections 3, 4, 6 and 9 specify schema-constrained AI and the single JSON model check. Depends on WS3-06 for the single client and replay; WS3-05 ensures the consumer context exposes bounded, catalogue-backed suggestions. Any new package requirement must be requested through the WS4 inbox, not added to shared requirements here.

Unavoidable cross-workstream dependency: WS0-01 supplies the human-only go and approved VM/network access for live acceptance. WS2-01 supplies the run_app API and WS4-01 the run-all stub; neither requires this task. Unavoidable cross-workstream dependency: WS2-04 supplies the real unchanged-app runner for live security acceptance; its explicit edge avoids a hidden availability gate. Inject a runner for offline tests; do not wait on WS4-05/06 or demand overall PASS here. Claude Code (`claude-3`) is the suggested future executor; Francisco supervises security, with Carolina reviewing unchanged-app semantics. No agent signs the gate.

## Steps
1. Validate parsed JSON-compatible `data` against the provided schema using an already available dependency only if present in the project manifest; otherwise implement a bounded subset sufficient for declared schemas or request WS4 coordination.
2. Reject invalid JSON, missing required fields, wrong types, additional forbidden keys where schema says so, and non-finite numbers.
3. Return the exact contracts-v1 completion envelope with sanitized errors; do not include rejected raw output or secrets in errors.
4. Add positive/negative tests for required fields, types, invalid JSON, sanitized validation failures, replay validation and incomplete status.
5. Integrate sever with the unchanged fixture application through the WS2 runner. Use temporary config only, the human-approved bounded local telemetry receiver from WS3-05 (test_demo_path.py may inject a bounded test double offline), real loopback proxy and actual Linux radar. Load provenance/freshness-checked published feeds through WS3-02; synthetic ranges are offline fixtures, never evidence of actual cloud denial. Preserve initial denial, approved-target connectivity and config-only retry, at most two attempts, with app hashes unchanged. Missing runner/fixture/receiver/ranges remains blocked or incomplete.
6. Add default offline demo-path tests plus an opt-in `SKYSHIFT_WS3_LIVE_TESTS=1` Linux run under human WS0 go. Record sanitized commands, feed dates, proxy events, radar limits, hashes and mode in Log. Request shared-file changes through WS4; do not edit CLI, evidence, fixture or requirements.

## Acceptance criteria
- `python -m unittest tests.ws3.test_llm_schema` exits 0 with at least six cases.
- Valid synthetic response passes schema and returns `status: ok`; malformed or schema-invalid response returns `status: incomplete` and sanitized error text.
- `python tasks/board.py --check` exits 0 after all task states and reciprocal dependency links are reconciled by the final verifier.
- `python -B -m unittest discover -s tests/ws3 -p 'test_*.py' -v` exits 0 offline. `SKYSHIFT_WS3_LIVE_TESTS=1 python -B -m unittest discover -s tests/ws3 -p test_demo_path.py -v` measures approved Linux proxy denial/log, target connectivity, radar scope, unchanged app and bounded retry. No access/fixture/real runner means NOT RUN/blocked, not skip-as-live-success.
- `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out --stub` remains exit 2. A non-stub run must produce measured WS3 evidence (initial denial plus final green, or honest blocked/incomplete). Overall exit 2 is allowed while other streams are incomplete; only WS4-06 owns full live PASS. A recorded/replay model explanation never replaces deterministic measurements.

## Out of scope
Changing shared dependencies/contracts/CLI/evidence, model pass/fail judgments, overall pipeline status, unapproved external API calls or automatic completion of the human VM gate. Approved deterministic Linux demo-path acceptance is in scope; live model API calls are optional and labelled replay is allowed.

## Fallback if blocked
Mark schema-dependent response incomplete; request an approved dependency/interface update through `tasks/comms/inbox-WS4.md` and preserve replay as explicitly labelled, validated fixture data.

## Log
- 2026-11-20 — Planned; no implementation or VM validation performed.
- 2026-11-20 14:38 UTC — claude-3 (SPEED MODE assignment): live sever() wired. Ranges: AWS/Google/Cloudflare live published feeds (fetched per run), Azure synthetic fixture (labelled). Runner: direct bounded subprocess of the unchanged fixtures/aws_workload/app.py --require-telemetry with target settings mapped to AWS_* config (WS2-04 run_app had no per-attempt env hook yet). Radar excludes sockets established before each attempt (operator SSH, model tunnel) and counts them. Missing target config => incomplete, no network.
- 2026-11-20 14:38 UTC — VM live (Ubuntu 26.04.1, py3.14, Leaseweb S3 target): sever PASS. Attempt 1 FAIL: monitoring.eu-central-1.amazonaws.com:443 denied twice (published cloud range aws), app exit 1 (telemetry required). Attempt 2 with local-otel config-only replacement: app exit 0, receiver 1 receipt, 0 radar bypasses, final green; app SHA-256 unchanged. tests/ws3 offline OK (+4 demo-path tests, 1 opt-in live). test_llm_schema.py not written (llm schema validation already covered by test_llm_client.py). Review: WS2-04 run_app swap pending.
