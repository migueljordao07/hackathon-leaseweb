---
id: WS4-05
title: Integrate the real pre-lunch discover translate migrate and parity path
workstream: WS4
status: in_progress
owner: claude-2
priority: P0
depends_on: [WS0-01, WS1-05, WS2-06, WS4-02]
blocks: [WS4-06]
files: [skyshift/cli.py, tests/ws4/test_core_integration.py]
estimate: 60m
claimed_at: "2026-11-20T14:33:00+00:00"
updated_at: "2026-11-20T14:37:00+00:00"
---

## Goal
Replace the core stub path with one measured run-all integration for real discovery, target choice, IaC translation/validation, synthetic data migration, unchanged application execution and Moto-before/target-after parity before lunch.

## Context
Portable source: `tasks/contracts.md` APIs, envelopes, outputs, CLI exit codes and demo honesty. Original proposal sections 3 steps 1-6, 4, 8-10 require real discover/translate/migrate/parity by 12:30, human-approved provider/endpoints, no automatic apply and explicit incomplete/failure records. Miguel supervises integration/migration evidence; Ricardo verifies provider/OpenTofu behavior; Carolina verifies fixture/parity; Diogo checks discovery traceability. Executor is `claude-2` because the parent explicitly assigns integration to Claude Code; Gemini CLI owns WS2 instead.

Unavoidable cross-workstream dependency: WS1-05 supplies the complete discovery/choice/translation path and WS2-06 verifies the migration/run/parity path through WS4-01. WS0-01 supplies the human-only go/provider/fallback decision. This task does not repeat their implementations and must not become done from stubs, mocks or unperformed VM checks. The gate may be done with a human switch-to-Airlock decision, but in that case this SkyShift live task must be cut/replanned rather than claiming PASS.

## Steps
1. Claim via the Git-only protocol, pull the named dependency commits from origin/main, read channel/WS4 inbox and edit only listed files. Confirm `tasks/WS0-setup/validation.md` has human evidence and a go/go-with-fallback decision before live execution; never sign it as an agent.
2. Wire CLI arguments/config to the landed function signatures without global endpoint leakage. Use explicit source/target clients through module config; give only the unchanged fixture app its AWS-compatible variables. Preserve environment values in memory and redact commands/errors/report records.
3. Start each run with a new run identity and atomically replace canonical artifacts. Execute discover, choose, translate, migrate, run and parity with returned objects, not stale disk inputs. Stop unsafe downstream actions after a prerequisite FAIL; emit honest incomplete records so evidence explains the stop.
4. Enforce actual live semantics: real inventory cannot assume unknown counts are zero; provider choice follows the human gate; translation records actual tofu codes or offline fallback; migration uses complete listings and per-object SHA-256; app hash before/after must match; parity includes detected plus put/get/list operations and treats both-fail as not PASS.
5. Add an opt-in Linux integration test with disposable synthetic namespaces, bounded timeouts and cleanup. Default tests remain offline. Measure one success candidate and controlled negative cases (changed object, app hash change or parity mismatch) without weakening module checks.
6. Record sanitized commands, versions, counts/statuses, elapsed time, provider mode, fallbacks and commit in Log. Hand off unresolved findings through owning inboxes; do not edit WS1/WS2 files. If 12:30 is at risk, humans cut optional scope, never core proof.

## Acceptance criteria
- `python -B -m unittest tests.ws4.test_core_integration -v` exits 0 offline with injected adapters and asserts exact order/config isolation, stop-on-unsafe-failure, output replacement, timeout/cleanup and redaction. It cannot claim live acceptance.
- With WS0 human go and disposable endpoints: `SKYSHIFT_WS4_LIVE_TESTS=1 python -B -m unittest tests.ws4.test_core_integration -v` measures the landed WS1/WS2 implementations on Linux/VM-like infrastructure. Missing access is a blocked/not-run result, not skip-as-success.
- `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out` produces measured discover/choose/translate/migrate/run/parity records. A candidate exit 0 requires actual tofu validation, all synthetic object hashes/counts matched, unchanged app hash, required operations passing on Moto and target, plus later sever/evidence checks; until those later checks are real, overall exit is 2.
- A controlled target-object difference or parity mismatch exits 1, overwrites stale artifacts and appears in evidence. A registry/model fallback remains visibly incomplete unless the contract's measured requirements are satisfied.
- Log states whether the before-lunch checkpoint was met, exact environment and limitations. `python tasks/board.py --check` succeeds after reciprocal links. Commit `[WS4-05] feat: integrate the measured core pipeline (claude-2)` with named files only.

## Out of scope
Implementing WS1/WS2 algorithms, provider apply, production data, database migration, severance behavior, credentials in Git, automatic gate completion, broad cloud-provider ranking and claims beyond measured checks.

## Fallback if blocked
If registry access alone fails under a valid 4/5 gate, use the documented offline schema path and keep translation/overall result incomplete. If model access fails, use a visibly labelled cached explanation while deterministic steps run. If endpoints fail or the gate switches to Airlock, preserve the exit-2 stub demo or approved recording, request a human cut/replan and do not call this task done as live SkyShift.

## Log
- 2026-11-20: Planned only. No live core integration, supplied-VM validation or provider/model call has been run.
- 2026-11-20T14:33:00+00:00: claimed by claude-2 under SPEED MODE (human decision Miguel 14:30 UTC; multiple WS4 claims authorized).
- 2026-11-20T14:37:00+00:00: claude-2: run-all live reads config from the environment (build_config). New: migrate/run/parity/sever are soft dependencies - they run with contract placeholder data when discover/choose are unusable, but a PASS is capped to incomplete (FAIL stays FAIL); choose/translate stay hard. Incomplete-but-valid upstream records already feed later steps. tests.ws4 29 OK on Windows/3.14; live VM run pending (claude-3).
