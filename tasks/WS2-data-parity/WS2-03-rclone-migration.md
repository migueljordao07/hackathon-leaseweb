---
id: WS2-03
title: Rclone migration with per-object SHA-256 proof
workstream: WS2
status: in_progress
owner: claude-3
priority: P0
depends_on: [WS0-01, WS2-02]
blocks: [WS2-06]
files: [skyshift/migrate.py, tests/ws2/test_migrate.py]
estimate: 60m
claimed_at: "2026-11-20T14:33:00+00:00"
updated_at: "2026-11-20T14:36:00+00:00"
---

## Goal

Replace the migration stub with a bounded rclone copy and deterministic source-versus-target proof for every synthetic object.

## Context

Original proposal sections 3–4, 6–7, 9–11 and the `migrate` contract require rclone between S3-compatible endpoints, complete paginated listings, byte-streamed SHA-256 on both sides, and honest counts for matched, missing, different, and extra objects. ETags are never accepted as content hashes. Default operation is `rclone copy`; destructive sync is allowed only for disposable synthetic targets after explicit human approval.

Unavoidable cross-workstream dependency: WS0-01 must record real VM availability, two usable endpoints, and the rclone fallback before live acceptance can become done. This dependency does not block WS2-01 or offline fixture work. Endpoint values and credentials arrive privately through contract environment names and must never appear in commands recorded in logs, exceptions, outputs, or tests.

Future executor: `gemini`. Miguel supervises rclone, endpoint safety, and checksum accounting; Carolina checks that fixture expectations remain intact.

## Steps

1. Validate required data-map/target fields and construct source/target clients explicitly from separate configuration namespaces.
2. Invoke rclone with an argument list, bounded timeout, sanitized environment, and no shell. Use copy by default and reject sync unless the target is explicitly marked disposable and a human approval flag is present.
3. Paginate both bucket listings to completion and detect duplicate/unstable keys or incomplete pages.
4. Stream each object through `hashlib.sha256` on each side without loading the full object into memory; compare key presence, byte counts, and lowercase 64-hex hashes.
5. Derive all summary counts from the per-object rows in stable key order. Mark any missing, different, or extra object FAIL; mark command/list/read failure FAIL or incomplete according to measured scope, never PASS.
6. Add unit tests with fake paginated clients and a fake rclone process for matched, missing, changed, extra, empty, pagination, timeout, partial read, command failure, secret redaction, and deterministic ordering.
7. Run a sanitized live test only on the human-approved synthetic VM endpoints and record counts/results in the task Log without object content or credentials.

## Acceptance criteria

- `python -m unittest tests.ws2.test_migrate -v` exits 0; tests prove every status/count branch, pagination, streamed reads, command timeout, and input immutability.
- The implementation invokes `rclone copy` without `shell=True`. A test proves `sync` is rejected unless both disposable-target and explicit-approval conditions are true.
- For the committed seed fixture, a successful approved run reports source_count == target_count == matched, with missing == different == extra == 0, one row per key, equal byte counts, and independently computed source/target SHA-256 values.
- Mutating one target byte produces one `different` row and overall FAIL; deleting and adding keys produce `missing` and `extra` rows. An incomplete listing or read can never yield PASS.
- Peak object handling is streaming/chunked; a test uses a body that fails on unbounded `read()`.
- Returned data matches `tasks/contracts.md`, contains no endpoint credential material or signed query strings, and serializes with `allow_nan=False`.
- `python tasks/board.py --check` exits 0. Live acceptance is logged only after WS0-01 human evidence; otherwise status remains review/blocked with the offline result and fallback.

## Out of scope

No production buckets, database migration, ETag proof, object deletion by default, S3-server installation, endpoint provisioning, shared CLI/evidence files, provider choice, or claim of application parity.

## Fallback if blocked

If rclone is unavailable, keep the deterministic Python listing/hash comparison and mark copy incomplete; the human may install a user-space rclone binary under the WS0 fallback. If one target service fails, use the human-approved self-hosted S3 alternative. If live access is unavailable before freeze, retain the tested fake-client path and clearly label the demo replay/incomplete rather than claiming migration PASS.

## Log

- 2026-11-20 12:07 UTC — Planned implementation. No rclone command, endpoint, or live checksum has run.
- 2026-11-20 14:33 UTC — Reassigned from gemini (never claimed) to claude-3 by Miguel (SPEED MODE). Claimed and in progress.
- 2026-11-20 14:36 UTC — Correction: the two entries above stamped 14:52 were written at about 14:34 UTC (clock slip); content unchanged. First VM run-all cycle at b7d46c3: migrate live PASS 4/4.
