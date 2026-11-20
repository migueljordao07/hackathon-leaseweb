---
id: WS4-06
title: Integrate severance rerun and produce final measured evidence
workstream: WS4
status: in_progress
owner: claude-2
priority: P0
depends_on: [WS3-07, WS4-05]
blocks: [WS4-07]
files: [skyshift/cli.py, skyshift/evidence.py, skyshift/templates/report/report.html.j2, tests/ws4/test_severance_integration.py]
estimate: 60m
claimed_at: "2026-11-20T14:33:00+00:00"
updated_at: "2026-11-20T14:38:00+00:00"
---

## Goal
Complete the live eight-step path with a measured red-to-fix-to-green severance drill and final deterministic evidence/report, without erasing the initial denial or overstating proxy/radar coverage.

## Context
Portable source: `tasks/contracts.md` Severance, Evidence and CLI sections. Original proposal sections 3 steps 7-8, 4, 7, 8 and 10-12 require a local allowlist proxy that blocks published US-cloud ranges, a detection-only Linux socket radar, bounded config-only remediation, rerun evidence, final hash and no compliance/universal-isolation claim. Target checkpoint is severance/report by 14:00. Executor `claude-2` owns integration; Francisco supervises the WS3 security semantics, Miguel verifies verdict/evidence and Diogo reviews report clarity.

Unavoidable cross-workstream dependency: WS3-07 completes the bounded severance/replacement path plus single sanitized/schema-validated LLM client. WS4-05 provides the measured core records. Integration must consume them through contracts and report limitations; WS4 does not modify security code. Cached model output may explain/propose a catalogue replacement only when labelled replay. Deterministic proxy, radar and final verdict checks remain measured.

## Steps
1. Claim through Git, pull dependency commits from origin/main, verify the human VM decision is still applicable and edit only listed files. Coordinate defects through WS3 inbox rather than patching its modules.
2. Wire sever after parity. Configure exact approved hosts/ports; ensure `NO_PROXY` cannot bypass the fixture telemetry destination. Preserve published range provenance/freshness, connect-time resolution and fail-closed behavior from WS3.
3. Record attempt 1 denial events and radar observations, apply only approved replacement-catalogue configuration, then rerun within the contract maximum of two attempts. Never mutate `fixtures/aws_workload/app.py`. Preserve attempt 1 when attempt 2 turns green; blocked/incomplete after exhaustion stays visible.
4. Feed the seven canonical records into deterministic evidence. Final green can satisfy severance only when proxy enforcement and approved-target connectivity were actually measured; radar alone never passes enforcement. Ensure report explains proxy scope, radar detection limits, model live/replay mode and all open items.
5. Add opt-in integration tests for red -> config fix -> green, unresolved/denied DNS, bypass detection, replay label, attempt exhaustion and cleanup. Recompute the evidence chain and verify report values against source records.
6. Run the full live candidate and a controlled failure, capture sanitized results/duration/hash/commit in Log, and notify WS4/humans of any required demo cut before feature freeze.

## Acceptance criteria
- `python -B -m unittest tests.ws4.test_severance_integration -v` exits 0 offline with injected network/process adapters and covers denial history, exact two-attempt bound, config-only remediation, radar non-enforcement, replay qualification, cleanup, evidence precedence and report escaping.
- With approved Linux VM-like access: `SKYSHIFT_WS4_LIVE_TESTS=1 python -B -m unittest tests.ws4.test_severance_integration -v` measures an AWS-range denial/log, approved target connectivity and radar scope. Missing privileges/ranges/network is blocked or incomplete, never a mock PASS.
- `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out` exits 0 only if all earlier live checks pass and sever attempt 1 records the hidden telemetry denial while a config-only replacement yields measured final green. `fixtures/aws_workload/app.py` hash is unchanged.
- `out/evidence.json` chain verifies over all seven canonical artifacts and `out/report.html` matches its verdict/hash, shows both sever attempts and states that proxy/radar checks are scoped evidence, not zero-leakage proof or certification. A no-fix run exits 1 or 2 per measured status and preserves the blocker.
- Log states whether the 14:00 checkpoint was met and records range provenance date, model mode, command results, final hash and limitations without secrets. `python tasks/board.py --check` succeeds. Commit `[WS4-06] feat: integrate severance and final evidence (claude-2)` with named files only.

## Out of scope
Changing WS3 algorithms/catalogues, more than two remediation attempts, source-code mutation, eBPF, packet-level universal enforcement, signatures/notarization, production traffic, autonomous credential use and DORA/sovereignty certification.

## Fallback if blocked
If the live model is unavailable, replay a validated cached explanation with an on-screen REPLAY label and keep proxy/radar/deterministic rerun live. If proxy/radar cannot run, show the verified recording and report the current run incomplete; do not infer isolation from an empty log. If no replacement succeeds by attempt two, present `blocked: manual action needed` and preserve FAIL/incomplete evidence.

## Log
- 2026-11-20: Planned only. No severance drill, network denial, model call, final evidence or VM test has been performed.
- 2026-11-20T14:33:00+00:00: claimed by claude-2 under SPEED MODE (human decision Miguel 14:30 UTC; multiple WS4 claims authorized).
- 2026-11-20T14:38:00+00:00: claude-2: report.html gains a Severance drill section listing every attempt (status, blocked, host:port decision via, replacement id/mode, bypasses), final and radar scope, all escaped; red attempt history preserved. tests.ws4 31 OK on Windows/3.14. Live sever depends on WS3-07 (claude-3); no live drill measured by claude-2.
