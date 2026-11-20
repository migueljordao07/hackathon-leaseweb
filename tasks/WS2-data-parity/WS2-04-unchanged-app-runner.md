---
id: WS2-04
title: Bounded unchanged-application runner
workstream: WS2
status: todo
owner: null
priority: P0
depends_on: [WS0-01, WS2-02]
blocks: [WS2-05, WS3-07]
files: [skyshift/parity.py, tests/ws2/test_run_app.py]
estimate: 45m
claimed_at: null
updated_at: null
---

## Goal

Replace the run stub with a bounded runner that exercises the original fixture application against the target using configuration only and proves the file stayed unchanged.

## Context

Original proposal sections 3, 6–7, 9–11 and the `run_app`/`run` data contract require the same `fixtures/aws_workload/app.py` on the target, configuration-only endpoint changes, functional checks, before/after file hashes, process cleanup, and an honest host-network observation. The runner is not a persistent daemon. It must not edit or copy-rewrite the fixture app, expose credentials, or call the target at import time.

Unavoidable cross-workstream dependency: WS0-01 must confirm a usable target endpoint and VM network-check method before live acceptance. A public IP or Leaseweb range observation is evidence with stated provenance and scope, not a universal sovereignty guarantee. The hidden telemetry dependency remains in the app for WS3 severance; this task does not disable or patch it.

Future executor: `gemini`. Carolina supervises functional parity and unchanged-app proof; Miguel supervises endpoint configuration, process lifetime, and host-network evidence.

## Steps

1. Validate workload path and hash `app.py` before execution with streamed SHA-256.
2. Build a minimal child environment from explicit contract key names; route S3 through `AWS_ENDPOINT_URL`, inject secrets only into the child, and redact them from logs/errors.
3. Start the app with an argument list and bounded timeout, capture structured output, terminate then kill on timeout, wait for cleanup, and remove temporary files.
4. Run required put/get/list/app checks against the target and convert child exit/output into deterministic check records.
5. Hash the same `app.py` afterward and fail if its bytes changed. Record `endpoint_changed` from sanitized source/target identity, never from secret-bearing URLs.
6. Gather a bounded host public-IP/network-owner observation only through the human-approved VM method and record source/time/limitations; unavailable evidence yields incomplete.
7. Test success, functional failure, malformed output, timeout, signal escalation, child cleanup, app mutation, secret redaction, and missing network evidence with fake processes/clients.

## Acceptance criteria

- `python -m unittest tests.ws2.test_run_app -v` exits 0 and leaves no child process or temporary file.
- The runner's before/after hashes are equal for the normal path and equal the direct SHA-256 of the committed fixture. A test that mutates the file during execution returns FAIL and restores the test copy without touching the repository fixture.
- Functional results include required put/get/list checks and preserve failures as findings. Timeout, malformed child JSON, or incomplete host-network evidence cannot yield PASS.
- Tests prove arguments do not use a shell, timeout escalation reaps the child, and returned/logged errors contain none of the configured secrets or signed URL query values.
- The returned record contains exactly the shared envelope keys and all run data fields from `tasks/contracts.md`; it serializes deterministically with `allow_nan=False`.
- A human-approved VM-like run records the target endpoint class and host-network observation with provenance. Without WS0-01 evidence, the task remains review/blocked and does not claim a live target run.
- `python tasks/board.py --check` exits 0.

## Out of scope

No app edits, deployment daemon, source/target provisioning, proxy enforcement, telemetry remediation, full parity table, rclone migration, evidence report, shared CLI, or claim that a single IP observation proves sovereignty.

## Fallback if blocked

If target access is unavailable, run the process lifecycle and unchanged-hash checks against a fake local S3 endpoint and return incomplete. If public-IP ownership cannot be checked, preserve the app checks and mark `host_network` incomplete with an open item. Never replace the original app with a target-specific variant.

## Log

- 2026-11-20 12:07 UTC — Planned runner. No application or target process has run.
