---
id: WS2-01
title: Contract-honouring data and parity stubs
workstream: WS2
status: claimed
owner: gemini
priority: P0
depends_on: []
blocks: [WS2-02, WS3-07, WS4-01]
files: [skyshift/migrate.py, skyshift/parity.py, tests/ws2/__init__.py, tests/ws2/test_stubs.py]
estimate: 30m
claimed_at: "2026-11-20T12:35:55+00:00"
updated_at: "2026-11-20T12:35:55+00:00"
---

## Goal

Create offline `migrate`, `run_app`, and `verify` stubs that let WS4 run the complete eight-step pipeline before real services exist.

## Context

Original proposal sections 3–4 and 6–11 require rclone migration with object-level SHA-256, the unchanged fixture application, Moto-before versus target-after parity, deterministic verdicts, and honest replay/fallback labels. Implement the Python signatures and envelopes in `tasks/contracts.md`: `migrate(data_map, target, *, config, stub=False)`, `run_app(workload, target, *, config, stub=False)`, and `verify(data_map, target, *, config, stub=False)`. This task is deliberately independent of WS0-01 and every WS4 task so there is no gate/stub cycle. WS4-01 consumes these stubs.

A stub returns realistic synthetic records with all required fields, `mode: stub`, `status: incomplete`, and at least one incomplete check explaining that no source, target, VM, or application was measured. It must make no network calls, start no process, read no credentials, and never report PASS. Use deterministic values so integration tests can compare exact JSON after WS4 serializes it.

Future executor: `gemini` through Gemini CLI. Human supervision: Carolina reviews parity/application semantics; Miguel reviews migration semantics. This differs from the original member-only split because four exclusive coding agents are required and the two Claude Code seats are reserved for translation and integration.

## Steps

1. Add the three exact contract signatures without import-time side effects.
2. Build complete synthetic migration data with one matched object, 64-character lowercase placeholder hashes, internally consistent counts, and empty missing/different/extra counts.
3. Build complete synthetic run data with equal before/after application hashes, a configuration-only endpoint-change marker, functional-check details, and an explicitly unmeasured host-network field.
4. Build complete synthetic parity data containing required put/get/list operations, before/after incomplete results, `equal: false`, and a selection record that cannot be mistaken for measured parity.
5. Add tests/ws2/__init__.py and offline unit tests that reject PASS, missing envelope/data keys, nondeterministic output, network/process calls, credentials in output, or mutation of input dictionaries.

## Acceptance criteria

- `python -B -m unittest discover -s tests/ws2 -p test_stubs.py -v` exits 0 with tests for all three functions before WS4 exists. Dotted `python -m unittest tests.ws2.test_stubs -v` is also supported after WS4 adds tests/__init__.py.
- Calling each function twice with the same synthetic inputs and `stub=True` returns equal JSON-serializable dictionaries containing exactly the shared envelope keys from `tasks/contracts.md` and every required step data field.
- Each record has `mode == "stub"`, `status == "incomplete"`, nonempty `checks`, sanitized `errors`, and no PASS check. `json.dumps(record, allow_nan=False)` succeeds.
- Tests patch socket, subprocess, and boto3/client construction boundaries to fail if invoked; all stubs still pass offline with an empty config.
- `python tasks/board.py --check` exits 0 after all planned task files are present. No claim is made that migration, parity, the VM gate, or `run-all` passed live.

## Out of scope

No fixture creation, rclone execution, object listing, byte hashing, Moto server, target service, application subprocess, CLI serialization, evidence verdict, live VM check, or product dependency edit.

## Fallback if blocked

If another product module is unavailable, keep imports local or use JSON-compatible constants; do not add a dependency or edit shared files. If a contract is ambiguous, retain the v1 shape, mark the disputed field incomplete, and request a contract change through append-only comms. Deliver the three offline stubs even when WS0 remains unrun.

## Log

- 2026-11-20 12:07 UTC — Planned as the independent WS2 stub. No product code or VM check has run.
- 2026-11-20T12:35:55+00:00 — Claimed by gemini. Read AGENTS.md, tasks/README.md, tasks/contracts.md, tasks/REVIEW.md, tasks/comms/channel.md, and tasks/comms/inbox-WS2.md; contracts v1 acknowledged. Implementation starts after claim push is accepted.
