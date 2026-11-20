---
id: WS1-01
title: Contract-honouring discovery choice and translation stubs
workstream: WS1
status: todo
owner: null
priority: P0
depends_on: []
blocks: [WS1-02, WS4-01]
files: [skyshift/discover.py, skyshift/translate.py, tests/ws1/__init__.py, tests/ws1/test_stubs.py]
estimate: 25m
claimed_at: null
updated_at: null
---

## Goal
Give run-all realistic offline discover, choose and translate records before any provider, model or VM access is available.

## Context
Portable source: tasks/contracts.md, Python API, shared envelope, data map, target choice, translated IaC and CLI sections. Original proposal sections 3 steps 1-3, 4, 6, 8-11: discover AWS dependencies, choose only Leaseweb deployment options, translate known resources before AI gaps. This task does not require the untracked original proposal. Suggested future executor: claude-1 (Claude Code), supervised by Ricardo for translation/provider and Diogo for discovery/catalogue. Moving Ricardo's CLI to WS4 and Diogo's report to WS4 separates file ownership while retaining their specialist review. This is an independent P0 stub, not the human VM gate.

## Steps
1. In a clean personal clone, read tasks/README.md, contracts.md, channel and WS1 inbox; run `python tasks/board.py --ready WS1`. Claim only this task, set owner/timestamps, commit `[WS1-01] chore: claim task (claude-1)` and push before implementation. On rejection pull --rebase, recheck and respect the accepted claim.
2. Implement `discover(workload: Path, *, config: dict, stub: bool = False) -> dict` and `choose(data_map: dict, *, config: dict, stub: bool = False) -> dict` in discover.py; implement `translate(data_map: dict, target: dict, *, output_dir: Path, config: dict, stub: bool = False) -> dict` in translate.py. Inputs for choose/translate are the preceding envelope's data objects, not the envelopes. Do not create skyshift/__init__.py, CLI, requirements or shared helpers; the owned test-package marker is allowed.
3. In stub mode return schema_version 1 and exactly step, mode, status, checks, data, errors alongside schema_version. Use mode stub/status incomplete, explicitly synthetic checks, realistic instance/security-group/bucket resources, put/get/list calls plus a visible AWS telemetry dependency, one bucket with synthetic counts, computed readiness, Leaseweb self-hosted choice, null unverified prices and all required nested fields. Do not import optional libraries in the offline stub path.
4. Write only generated `output_dir/iac/main.tf` for translation (output_dir is the run root, normally out). Label it synthetic and non-deployable; list that actual path in translate.data.files. Use method offline_schema with null init/validate codes, attempts 0 and diagnostic explaining no tofu execution. Non-stub paths return an explicit not-implemented incomplete envelope, never a fabricated live result.
5. Add tests/ws1/__init__.py and stdlib unittest tests using temporary directories and synthetic workload files. Preserve future stub behavior through every replacement task. Hand off signatures, data-input convention, generated-path convention, tests and commit reference through the task Log and Git-only WS1 inbox; WS4 reads these in Git for run-all integration.

## Acceptance criteria
- `python -B -m unittest discover -s tests/ws1 -p test_stubs.py -v` exits 0 without credentials, network, tofu, llm.py, fixtures or CLI. Assert exact envelope keys, required nested keys, nonempty resources/calls/buckets, visible telemetry, synthetic counts and no PASS records.
- Tests chain discover -> choose -> translate with `.data` inputs; verify main.tf exists inside a temporary run-root/iac directory, output files are not canonical JSON, config secret sentinel is absent from all records/artifacts, and imports do not start services.
- After WS4-01 lands, `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out --stub` must exit 2, not 0, with eight complete records and HTML; record this as an integration follow-up, not a dependency preventing this stub from landing.
- Run `python tasks/board.py --check`; review only after actual test results/environment are appended to Log. Done requires Linux-like acceptance, code on origin/main and run-all intact per tasks/README.md. Stage named files only, never unrelated files; no force-push.

## Out of scope
Live inventory, model calls, provider assumptions, real tofu execution, provisioning/apply, CLI serialization, fixture creation and shared dependencies. No VM or WS4 dependency may be added to this first task.

## Fallback if blocked
Keep stub code standard-library-only and synthetic. Request integration or shared-file changes through inbox-WS4; never edit WS4 files. If the framework is not released or a claim race is lost, do not implement; append a Git-only blocker and choose another ready task. Never relabel a stub as live proof.

## Log
- 2026-11-20: Planned only; no implementation or VM acceptance performed. Claim timestamps remain null.
