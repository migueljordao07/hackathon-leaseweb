---
id: WS4-02
title: Build deterministic evidence verdicts hash chain and HTML report
workstream: WS4
status: todo
owner: null
priority: P0
depends_on: [WS4-01]
blocks: [WS4-05]
files: [skyshift/evidence.py, skyshift/templates/report/report.html.j2, tests/ws4/test_evidence.py, tests/ws4/test_report.py]
estimate: 55m
claimed_at: null
updated_at: null
---

## Goal
Replace the minimal stub adapter with deterministic evidence evaluation, reproducible chain verification and a safe human report that cannot turn missing, stubbed or replay-only measurements into PASS.

## Context
Portable source: `tasks/contracts.md` shared envelope and Evidence sections. Original proposal sections 3 step 8, 4, 6, 10 and 12 require machine-readable PASS/FAIL checks, per-artifact SHA-256, a final hash, DORA-style headings without a compliance claim, and AI narrative that never calculates verdicts. Miguel supervises evidence logic; Diogo reviews the report. Executor remains `claude-2` so one owner controls the shared CLI/report boundary.

Evidence hashes discover, choose, translate, migrate, run, parity and sever in that order; it does not hash itself or mutable HTML. PASS needs a complete live artifact set, actual IaC validation, measured object equality, unchanged app hash, parity with no skipped required operations and final green severance. Missing/malformed records, stubs, unverified replay mappings and offline-only validation are incomplete. Measured failures are FAIL. A recorded initial severance denial may remain evidence while a measured final retry is green.

## Steps
1. Claim through the Git-only protocol and edit only listed files. Preserve the WS4-01 API/paths; broadcast any contract change before editing `tasks/contracts.md` in a separately authorized maintenance task.
2. Validate record schema/version, exact required steps, check statuses and required data fields before calculating verdicts. Reject duplicate/wrong-order artifacts, NaN, unsafe paths and malformed hashes. Do not read arbitrary paths from untrusted records.
3. Canonicalize each record exactly with sorted compact UTF-8 JSON and `allow_nan=False`; compute artifact and linked hashes from a 64-zero genesis value. Expose verification that recomputes every link and fails on mutation, reordering or omission.
4. Derive evidence checks from inputs, not prose/model output: artifact completeness, translated IaC validation scope, object counts/hashes, app before/after hash, parity required operations and final severance state. Preserve per-step FAIL/incomplete causes and open items. Final status precedence is FAIL, then incomplete, then PASS.
5. Render an escaped, self-contained HTML report with data map, target rationale and source URLs, translated IaC summary, migration proof, parity table, severance history, costs/assumptions, open items, verdicts and final hash. Mark stub/replay/offline/manual data visibly. State that the report supports an exit-plan test and is not a certificate or DORA compliance determination.
6. Add deterministic unit and mutation tests, including hostile strings and missing fields. Log real results and hand off through Git; do not use a model or network in default tests.

## Acceptance criteria
- `python -B -m unittest tests.ws4.test_evidence tests.ws4.test_report -v` exits 0 offline and covers complete synthetic live PASS, measured FAIL, incomplete/stub/replay/offline/manual cases, duplicate/missing/reordered steps, mutation, malformed hashes/NaN and HTML escaping.
- Two identical input record lists produce byte-identical canonical evidence JSON and the same final hash. Reordering, omitting or changing one byte of a record fails verification or changes the chain. The first `previous_hash` is 64 ASCII zeroes; evidence/report are not chain inputs.
- A synthetic PASS fixture can pass only when every required deterministic condition is present. Replacing model narrative with `PASS`, using replay alone, or setting both parity sides to FAIL cannot make evidence PASS.
- Generated `out/report.html` is self-contained and visibly labels incomplete/replay/stub material, cites available target/cost URLs, displays adjustable assumptions and contains no credential values or executable unescaped record HTML.
- `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out --stub` still exits 2 and generates a qualified report. `python tasks/board.py --check` succeeds after reciprocal links. Commit `[WS4-02] feat: make evidence and report deterministic (claude-2)` with named files only.

## Out of scope
Signing/notarizing hashes, PDF export, a compliance certificate, invented prices/savings, model-based verdicts, live provider execution and edits to other workstreams. Do not weaken incomplete semantics to improve demo appearance.

## Fallback if blocked
If Jinja2 is not yet installed, use an escaped stdlib renderer while preserving the template boundary and output contract. If an upstream record lacks required data, report incomplete with an open item and request a contract fix through inboxes; never infer a PASS. Keep the stub run demonstrable while live integration remains pending.

## Log
- 2026-11-20: Planned only. Evidence/report implementation and tests have not run.
