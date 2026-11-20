---
id: WS2-05
title: Moto-before versus target-after parity table
workstream: WS2
status: in_progress
owner: gemini
priority: P0
depends_on: [WS2-04]
blocks: [WS2-06]
files: [skyshift/parity.py, tests/ws2/test_parity.py]
estimate: 60m
claimed_at: "2026-11-20T14:35:00+00:00"
updated_at: "2026-11-20T14:35:00+00:00"
---

## Goal

Replace the parity stub with one bounded suite that runs the same selected operations against Moto before and the approved target after, then reports every difference as data.

## Context

Original proposal sections 3–4, 6–7 and 9–11 plus the parity contract require operations detected from the fixture's `boto3` calls, mandatory put/get/list checks, application checks, and multipart/presigned checks when used. Before is Moto; after is the target. Optional AI selection may add known operations but may never remove detected or mandatory operations. Deterministic code validates the selection and computes verdicts. A difference is a finding, not a crash; both sides failing never makes PASS.

WS2-04 transitively carries the human VM gate and fixture prerequisites. The suite must isolate namespaces, clean up only its synthetic keys, use equal inputs/timeouts on both sides, and retain per-side details without secrets. Moto success proves only the emulated baseline; target success proves only the measured operations.

Future executor: `gemini`. Carolina supervises suite equivalence and S3 semantics; Miguel verifies target safety and cleanup boundaries.

## Steps

1. Build the required operation set as the union of put/get/list, AST-detected fixture operations, and app checks; add multipart/presigned URL only when the fixture uses them.
2. Accept an optional model/replay proposal through a bounded known-operation schema. Reject unknown operations and preserve the deterministic required set; missing or malformed model output yields incomplete explanation, never a reduced suite.
3. Start/use Moto with bounded setup and cleanup, then run identical operation functions and synthetic inputs against Moto and the target through explicitly separate clients.
4. Normalize each operation to PASS, FAIL, or incomplete plus a sanitized detail. Compare statuses and relevant returned behavior; never compare credentials, signed URL tokens, timestamps, or provider-specific request IDs.
5. Produce rows in stable operation order. `equal` is true only for equivalent measured behavior; overall PASS requires both sides PASS for every required operation and no missing/skipped row.
6. Add tests for detected-operation inclusion, model attempts to remove/add invalid operations, one-side failure, both-side failure, skipped checks, startup timeout, presigned URL sanitization, namespace cleanup, and deterministic output.
7. Run the same suite on the human-approved VM target and record exact operation totals and failures in the task Log.

## Acceptance criteria

- `python -m unittest tests.ws2.test_parity -v` exits 0 and proves one implementation runs against both client configurations with identical inputs.
- `selection.operations` contains put_object, get_object, list_objects_v2, every relevant AST-detected call, and conditional multipart/presigned operations. An AI/replay proposal cannot remove them or introduce an unrecognized operation.
- Each required operation has one before and one after result. A difference is emitted as a row and overall FAIL/incomplete, not raised as an unhandled exception.
- Tests prove both sides FAIL does not produce overall PASS, any missing/skipped operation produces incomplete, signed URL query strings are removed, and no target key outside the generated synthetic namespace is deleted.
- A successful measured run has PASS on both sides for every required row and `equal: true`; Moto-only, target-only, replay-only, or fake-client runs remain incomplete.
- The record follows `tasks/contracts.md`, is stable across equal runs, contains no secrets, and serializes with `allow_nan=False`.
- `python tasks/board.py --check` exits 0. Live target acceptance is claimed only with the WS0 human gate and actual recorded commands/results.

## Out of scope

No full ceph/s3-tests import, competitor API ranking, destructive bucket cleanup, source data, app modification, migration proof, proxy/severance, shared model client implementation, CLI/evidence edits, or claim of complete S3 compatibility.

## Fallback if blocked

If Moto cannot run as a server, use its in-process mode while preserving the same operation functions. If the target is unavailable, run Moto plus a fake after-client and report incomplete. If time is short, keep put/get/list and fixture-detected operations, cut optional presigned/multipart checks only when not detected, and document the cut before feature freeze.

## Log

- 2026-11-20 12:07 UTC — Planned parity implementation. Moto and target checks have not run.
- 2026-11-20 14:35 UTC — Claimed by gemini under SPEED MODE (working WS2-04 then WS2-05 in sequence).
