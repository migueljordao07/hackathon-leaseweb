---
id: WS2-06
title: WS2 run-all demo-path verification and handoff
workstream: WS2
status: todo
owner: null
priority: P0
depends_on: [WS2-03, WS2-05, WS4-01]
blocks: [WS4-05]
files: [tests/ws2/test_demo_path.py]
estimate: 45m
claimed_at: null
updated_at: null
---

## Goal

Verify the migration, unchanged-app run, and Moto-versus-target parity path through WS4's `run-all`, preserve failures as evidence, and hand measured results to integration before freeze.

## Context

Original proposal sections 3–4 and 6–11 require a live five-minute path: migrate synthetic objects with per-object SHA-256, run the same app through configuration, compare Moto before with target after, and feed deterministic records to evidence. The contract requires canonical `out/migrate.json`, `out/run.json`, and `out/parity.json`; live overall PASS exits 0, measured FAIL exits 1, and stub/incomplete exits 2.

The cross-workstream dependency is limited to WS4-01, the approved integration stub. WS2-01 already enables early stub `run-all`; this final P0 task checks that replacing WS2 stubs does not break it. It may add only the WS2 demo-path test. Product defects return the owning WS2 task to in_progress; CLI/evidence defects are requested through `tasks/comms/inbox-WS4.md`. Feature freeze is 14:30, code freeze 15:15, and the pitch is at most five minutes.

Future executor: `gemini`. Miguel supervises end-to-end migration/integration evidence; Carolina supervises fixture, unchanged-app, and parity validity. Claude Code (`claude-2`) remains the sole WS4 integrator, avoiding shared-file collisions.

## Steps

1. Add an integration test that seeds a unique synthetic source namespace, invokes WS4 `run-all` with approved local/VM configuration, and always cleans up only that namespace.
2. Assert canonical JSON files exist, parse with no NaN, match schema version/steps, and contain internally consistent migration counts, equal app hashes, and a complete parity table.
3. Recompute each source and target seed hash independently from the reported summary. Inject a controlled target-byte mutation after rclone copy but before verification, through a test adapter; mutating before copy would be overwritten. Assert `run-all` exits 1 with the finding preserved rather than crashing.
4. Run the offline/stub path and assert exit 2 with valid incomplete records; never accept stub or replay as live PASS.
5. Run the approved WS2 live path twice before the core handoff, record durations and sanitized results in the Log, and send WS4 only paths/counts/statuses—never credentials or object content. These are component verification runs, not the two final post-14:30 stage rehearsals owned by WS4.
6. If a run fails, identify the owning task/file, update this task to blocked/review as appropriate, and use the demo-safe fallback rather than weakening checks.

## Acceptance criteria

- `python -m unittest discover -s tests/ws2 -v` exits 0 in the declared VM-like environment.
- `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out --stub` exits 2 and produces valid incomplete `out/migrate.json`, `out/run.json`, and `out/parity.json`; no record or check claims live PASS.
- With human-approved synthetic endpoints and no `--stub`, `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out` must produce measured PASS for migration/run/parity when every seed object matches, app hashes match and all required operations pass on both sides. Overall exit 2 is expected while unrelated translation/severance/evidence remains incomplete; it does not block WS2 completion when all WS2 checks are measured and reviewed. Overall exit 0 is permitted only after all workstreams' live checks pass, and is owned by WS4-06, not a prerequisite here.
- A controlled changed target object exits 1, identifies the changed key without exposing content, and remains present in canonical output/evidence. Stale output from the prior run is overwritten atomically by WS4.
- Two measured WS2 verification runs record duration, object totals, operation totals, environment class, overall exit and unrelated incomplete steps in Log. Without real VM evidence, record NOT RUN and keep the task out of done. Final timed stage rehearsals occur after 14:30 in WS4.
- `python tasks/board.py --check` exits 0. No WS2 file outside this task's `files` is edited during verification; fixes return to the owning task.

## Out of scope

No new product behavior, shared CLI/evidence/report edit, credentials in Git, production data, destructive cleanup outside the test namespace, severance implementation, provider deployment, backup recording, pitch editing, certification, or merge after 15:15.

## Fallback if blocked

If live endpoints fail, show the last labelled rehearsal/recording and rerun deterministic local checksum and Moto checks live; output remains incomplete. If WS4 `run-all` is broken, notify WS4 and execute the three WS2 functions directly for diagnosis, but do not call that a successful run-all. Cut optional operations before 14:30 only when they were neither detected nor mandatory; never cut per-object hashes, unchanged-app proof, or put/get/list parity.

## Log

- 2026-11-20 12:07 UTC — Planned final verification. No rehearsal, live endpoint, or run-all command has run.
