---
id: WS4-01
title: Integrate the eight-step contract stubs end to end
workstream: WS4
status: todo
owner: null
priority: P0
depends_on: [WS1-01, WS2-01, WS3-01]
blocks: [WS2-06, WS3-07, WS4-02, WS4-03, WS4-04]
files: [skyshift/__init__.py, skyshift/cli.py, skyshift/evidence.py, skyshift/templates/report/report.html.j2, tests/__init__.py, tests/ws4/__init__.py, tests/ws4/test_stub_run_all.py]
estimate: 60m
claimed_at: null
updated_at: null
---

## Goal
Create the first runnable SkyShift integration: all eight contract-honouring stubs execute in pipeline order, write deterministic JSON artifacts and a clearly qualified HTML report, and exit incomplete rather than claiming live proof.

## Context
Portable source: `tasks/contracts.md` Python API, shared envelope, canonical paths, evidence chain and CLI contract. Original proposal sections 3, 4, 6-10 require discover -> choose -> translate -> migrate -> run -> parity -> sever -> evidence, early stub readiness within 90 minutes, and no model-generated verdicts. This is the WS4 P0 run-all demo-path task. It consumes WS1-01, WS2-01 and WS3-01 only; it must not depend on the human VM gate, so offline integration cannot form a gate/stub cycle. Suggested executor is `claude-2` (Claude Code), with Miguel supervising integration/evidence and Diogo reviewing report/demo clarity. This corrects the decomposer's conflicting Gemini suggestion: the parent requires integration on Claude, while Gemini CLI owns WS2 to preserve exactly two Claude, one Codex and one Gemini executor.

Stub readiness is not real readiness. A stub run uses realistic synthetic records, writes all artifacts, returns exit 2 and labels every unmeasured check incomplete. It never proves a migration, OpenTofu validation, target parity, proxy enforcement, VM location, sovereignty or DORA compliance.

## Steps
1. Follow `tasks/README.md`: pull/rebase, read `tasks/comms/channel.md` and `tasks/comms/inbox-WS4.md`, claim and push this task before implementation, then edit only listed files. Coordinate interface mismatches through append-only inboxes; do not edit another stream.
2. Add an import-safe package and CLI with subcommands `discover`, `choose`, `translate`, `migrate`, `verify`, `sever`, `report` and `run-all`. Accept `--workload`, `--out` and `--stub`; build config from documented environment names without logging values. Do not start services or perform network calls on import/help.
3. In `run-all`, call returned Python objects in the exact eight-step order. `verify` emits run and parity. Catch step exceptions, sanitize them, create incomplete records and stop downstream work from consuming stale files. Overwrite the current run's canonical outputs atomically with UTF-8, sorted keys and `allow_nan=False`; never reuse a prior run.
4. Implement the minimum evidence/report adapter needed for the stub path. Build the seven-artifact SHA-256 chain exactly as `tasks/contracts.md` specifies, write `out/evidence.json`, then render `out/report.html`. The report visibly states STUB / INCOMPLETE / NOT VM VALIDATED and lists open items; HTML escaping prevents record content from becoming markup.
5. Map overall exit codes deterministically: 1 if any measured required check is FAIL, otherwise 2 for any incomplete/stub result, and 0 only when later live integration has all required PASS checks. The initial task must exercise only the exit-2 path; no special case turns synthetic output green.
6. Add tests/__init__.py and tests/ws4/__init__.py so dotted unittest commands and recursive discovery resolve the local test packages. Add offline tests that inject the three workstream stubs, verify call order/data flow, output replacement, exception handling, deterministic JSON and chain, HTML qualification and exit code. Record actual commands/results in Log and hand off via Git only.

## Acceptance criteria
- `python -B -m unittest tests.ws4.test_stub_run_all -v` exits 0 offline. Tests run from a temporary output directory, make no network/service calls, and assert exact order, eight schema-v1 envelopes, canonical filenames, no NaN, no secret-value leakage, escaped report text and deterministic reruns.
- `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out --stub` exits 2 and freshly creates `out/discover.json`, `choose.json`, `translate.json`, `migrate.json`, `run.json`, `parity.json`, `sever.json`, `evidence.json`, `iac/main.tf` and `report.html`. Every stub record is `mode: stub`, `status: incomplete`; the report says no VM validation occurred.
- `python -m skyshift.cli --help` exits 0 without creating files or contacting services. A forced stub exception returns 2, records a sanitized incomplete error and cannot consume artifacts from a previous run.
- Recomputing the seven-record chain from canonical JSON bytes produces `evidence.data.final_hash`; mutating one record changes verification. This is stub-chain correctness, not live evidence.
- `python tasks/board.py --check` succeeds after reciprocal links are reconciled. Review Log names the OS/Python version, commands and results; done also requires code on origin/main and run-all intact. Commit `[WS4-01] feat: integrate contract stubs end to end (claude-2)` with named files only.

## Out of scope
Real VM/provider calls, target deployment, real migration/parity/severance, final evidence verdict policy, polished report, dependency installation, jury README, license, recording and production data. Do not edit shared contracts unless the broadcast/acknowledgment protocol authorizes a later WS4 change.

## Fallback if blocked
If one stub has not landed, keep this task blocked and request the missing contract implementation in that stream's inbox; do not recreate its module in WS4. A temporary test double may prove CLI control flow locally but cannot satisfy done. If report templating is unavailable, render safe stdlib HTML while keeping the same file and visible STUB label. Never wait on VM access for this offline task.

## Log
- 2026-11-20: Planned only. Stub run-all, product files and VM checks have not been implemented or executed.
