---
id: WS1-05
title: Validate IaC with bounded schema-constrained AI repair
workstream: WS1
status: in_progress
owner: claude-1
priority: P0
depends_on: [WS1-04, WS3-01]
blocks: [WS4-05]
files: [skyshift/translate.py, tests/ws1/test_validation.py, tests/ws1/test_pipeline.py]
estimate: 50m
claimed_at: "2026-11-20T14:35:00+00:00"
updated_at: "2026-11-20T14:35:00+00:00"
---

## Goal
Complete translate with real bounded OpenTofu validation, one correction at most, and honest WS1 pipeline evidence for run-all.

## Context
Portable source: tasks/contracts.md Python API, llm.complete response, shared verdict rules, translated IaC, CLI and demo honesty; WS1-04 supplies approved provider templates/schema. Original proposal sections 3 step 3, 4, 6-12 require templates first, schema-constrained AI only for gaps, one validation-error correction, manual unresolved resources, no apply. Executor claude-1, Ricardo supervises provider/validation, Diogo reviews discovery-to-report traceability. Target before-lunch real discover/translate milestone; if time is lost cut scope, never fake success.

WS3-01 supplies only the stable llm.complete API stub. This task must not wait for a future live model implementation: known templates validate without AI, an unavailable model yields manual/incomplete gaps. Call `complete(task, payload, schema, config=config, replay=...)` from skyshift.llm; do not implement another client, sanitizer or fixture cache. Real/replay model adapters are consumed when WS3 later lands them, with mode preserved. Human gate dependency is inherited from WS1-04; there is no gate/stub cycle.

## Steps
1. Use tasks/README.md Git claim/push race protocol, then edit only listed files. Read channel and WS1 inbox on every pull. Request schema/model/integration changes through owning inboxes and preserve stub mode exactly.
2. Invoke tofu with explicit argument arrays, cwd limited to the generated iac directory, no shell interpolation, subprocess timeouts (30 seconds per init/validate command), bounded captured output and sanitized diagnostics. Run init with -backend=false -input=false and validate with -json. Count validation cycles, not subprocesses, in attempts; record real init_exit/validate_exit (null when not run). Never apply/plan/destroy. Importing the module and stub paths must not spawn tofu.
3. Validate approved template mappings first. For unknown-resource gaps, submit only synthetic sanitized resource fields plus the approved provider schema to llm.complete; accept structured resource proposals, not arbitrary executable model text. Define a strict JSON schema at the call site (known provider resource types/attribute types, no unknown properties); validate references and render escaped literals through existing templates/serializer. Source secrets, raw object data, environment, private addresses and credentials never enter payloads or diagnostics.
4. After a failed validation, allow at most one correction request to the shared model API using sanitized diagnostic codes/messages plus the same constrained schema. Re-render and validate once more (maximum two validation cycles). Invalid JSON/schema, model incomplete/replay, missing binary, timeout, missing schema or failed registry must never become live PASS. Preserve first diagnostics and repair history. No recursive retries or new provider/plugin installation commands from model output.
5. Report per-resource manual reasons for unresolved gaps. If final real validation fails, status FAIL; if no measured failure but manual/offline/missing checks remain, incomplete; PASS only when actual init/validate exit 0 and all required mappings/checks are measured. Real tofu with replayed explanatory text remains measured, but any unverified replay-generated mapping stays incomplete. Include all required validation fields and resource rows, no new top-level envelope keys.
6. Add default offline tests with fake subprocess/model adapters and a live integration test opt-in via SKYSHIFT_WS1_LIVE_TESTS=1. Pipeline test consumes the landed WS2 fixture when present (do not modify it) and calls discover -> choose -> translate with data objects. Live mode requires approved source/provider access; missing prerequisites fail or explicitly skip with no success claim. Keep JSON writing with CLI alone. Log actual results, environment, provider version, manual items and commit; hand off via Git-only WS1 inbox for WS4 checkpoint review.

## Acceptance criteria
- `python -B -m unittest discover -s tests/ws1 -p test_validation.py -v` exits 0. Assert exact command arguments, timeouts/cleanup, no apply, two-cycle upper bound, init failure/no validate, successful template path/no model call, one valid correction, invalid/missing model output, offline schema, missing tofu, timeout, failed second validation, manual preservation and redaction. Tests assert no invented 0 exit codes and retain initial diagnostics.
- `python -B -m unittest discover -s tests/ws1 -p 'test_*.py' -v` exits 0 with stub regression and pipeline tests; normal mode never contacts live services. Tests must not silently count a missing fixture or model as live acceptance.
- With human go/provider access and the fixture on main: `SKYSHIFT_WS1_LIVE_TESTS=1 python -B -m unittest discover -s tests/ws1 -p test_pipeline.py -v` actually measures source inventory, approved target choice and tofu init/validate. Run `python -m skyshift.cli translate --workload fixtures/aws_workload --out out` and inspect out/translate.json: real codes, resource/manual coverage and validation scope match the command output. Gate/fixture/CLI unavailability is a recorded blocker, not simulated success.
- `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out --stub` exits 2 with all eight envelopes/report; shared live `run-all` remains WS4-owned and only measured complete results may exit 0. WS1 acceptance does not assert other streams' live readiness. Record unresolved P0 manual items for WS4/humans to approve a reduced demo or block overall PASS.
- `python tasks/board.py --check` succeeds after final reciprocal links. Review requires actual commands/results in Log; done requires Linux-like acceptance, origin/main and run-all intact. Commit `[WS1-05] feat: validate translated IaC with bounded repair (claude-1)` and explicitly stage named files only.

## Out of scope
Shared model-client edits, credential handling infrastructure, provider apply, generated data committed to Git, CLI/evidence changes, production workloads and unverifiable sovereignty/compliance claims. No optional research or features after 14:30; no merges after 15:15.

## Fallback if blocked
Keep deterministic templates and labelled offline_schema/incomplete records when registry/tofu is unavailable. Model failure leaves gaps manual rather than blocking known templates. Git-only requests to WS4/WS3/humans identify missing capability by name, never secret values. If a live integration dependency remains absent, keep review/blocked and preserve runnable stubs; do not claim P0 evidence complete from mocks or cached model output.

## Log
- 2026-11-20: Planned only; no product implementation, provider execution or live model acceptance performed.
- 2026-11-20 14:35 UTC: Claimed by claude-1 under SPEED MODE (Miguel 14:30; WS1-03/04/05 claimed together, deps WS0-01/WS1-02 done per human decision).
- 2026-11-20 14:39 UTC: Validate step only (speed mode, no AI repair loop): run_tofu runs [tofu, init, -backend=false, -input=false, -no-color] then [tofu, validate, -json, -no-color] in out/iac, 30 s timeout each, argument arrays, no shell, env without AWS_/OS_/SKYSHIFT_/LEASEWEB_ variables, plugin cache ~/.skyshift/tofu-plugin-cache; attempts=1; real exit codes, null when not run; init failure skips validate (FAIL); timeout => incomplete; missing tofu => offline_schema/incomplete. tofu found on PATH or ~/skyshift-gate/bin/tofu. tests/ws1/test_validation.py 6 OK (fake runner). test_pipeline.py and the AI repair are not implemented (cut under speed mode). Live VM run pending.
- 2026-11-20 14:52 UTC: VM result (claude-3, 87139ae, Ubuntu 26.04): live translate iac_validated PASS (tofu init -backend=false exit 0, validate exit 0, openstack 3.4.0); templates_mapped incomplete (1 template, 2 manual). Overall incomplete by design; manual items escalated to inbox-humans. Status stays in_progress/review until a human decision.
