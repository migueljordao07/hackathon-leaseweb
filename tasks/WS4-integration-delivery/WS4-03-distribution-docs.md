---
id: WS4-03
title: Package a fresh-clone install with jury README and Apache license
workstream: WS4
status: in_progress
owner: claude-2
priority: P0
depends_on: [WS4-01]
blocks: [WS4-07]
files: [README.md, LICENSE, requirements.txt, .gitignore, .env.example, tests/ws4/test_distribution.py]
estimate: 45m
claimed_at: "2026-11-20T14:33:00+00:00"
updated_at: "2026-11-20T14:33:00+00:00"
---

## Goal
Make the public repository understandable and runnable from a clean Linux clone with declared open-source dependencies, an Apache-2.0 license, safe configuration names and concise jury-facing instructions.

## Context
Official challenge rules require a public Git repository, working checkout, concise README, build/run instructions, declared public dependencies and an open license allowing commercial and non-commercial reuse. Original proposal sections 6, 7, 9-12 define Python 3.10+, OpenTofu/rclone/S3 service prerequisites, the eight-step CLI, five-minute demo, fallbacks and honesty rules. Root `README.md` is for judges, not internal planning. WS4 owns all shared root files. Executor is `claude-2`; Miguel verifies installation/run instructions and Diogo reviews pitch clarity. Gemini CLI is assigned to WS2, not WS4, because integration must remain on the second Claude Code seat.

## Steps
1. Use the claim/push protocol, inspect current imports and executable commands on main, and edit only listed files. Pin or constrain every actual Python dependency needed by product modules; do not list unused libraries or depend on private packages.
2. Add the complete unmodified Apache License 2.0 text in `LICENSE`. Document third-party service/tool licenses and note that a separately operated S3 server may have its own license; do not imply Apache-2.0 relicenses dependencies.
3. Write a concise jury README: problem and measured claim, architecture/pipeline, requirements, Linux setup, stub quickstart, human-approved live setup, commands, output/report paths, test commands, demo/fallback labels, limitations and project structure. Never expose private vault/spec paths, credentials or unverified VM/provider results.
4. Put generated `out/`, `.env`, caches, virtual environments, coverage and local service state in `.gitignore` without ignoring `.env.example`, fixtures, tasks or required source. `.env.example` contains every contract key name with empty values/comments only; group optional/provider-specific keys and explain private secret delivery.
5. Add an offline distribution test that checks license markers, README commands/paths, required environment key names, generated-output ignores and importability after dependency installation. Test the documented stub command and its expected exit 2 rather than calling it success.
6. Verify in a clean temporary clone or archive on Linux/VM-like Python when available. Record exact commands/results and any native binaries not exercised; do not claim supplied-VM validation.

## Acceptance criteria
- `python -m pip install -r requirements.txt` succeeds in a clean Python 3.10+ virtual environment using only public packages, followed by `python -B -m unittest discover -s tests -p 'test_*.py' -v` for all available offline tests. If network installation is unavailable, task stays review/blocked; dependency syntax alone is not acceptance.
- `python -B -m unittest tests.ws4.test_distribution -v` exits 0 and verifies Apache-2.0 text, README required sections/commands, every environment name from `tasks/contracts.md`, no values/secrets in `.env.example`, and correct tracked/generated ignore boundaries.
- Following README from a fresh clone makes `python -m skyshift.cli --help` exit 0 and the documented stub `run-all` exit 2 while generating eight JSON files plus HTML. README states exit 2 means incomplete, not failure-free live evidence.
- README distinguishes Python packages from OpenTofu, rclone and the selected S3 service; it documents Docker and user-space fallbacks, human-only VM/provider decision, cached model responses labelled replay, no automatic apply and no production data.
- `git check-ignore .env out/evidence.json` matches both, while `git check-ignore .env.example fixtures/aws_workload/app.py` matches neither. `python tasks/board.py --check` succeeds after reciprocal links. Commit `[WS4-03] docs: package the public demo repository (claude-2)` with named files only.

## Out of scope
Internal planning notes in README, secrets, VM credentials, provider apply, container/image publishing, a guarantee that optional native tools exist, a compliance claim, task-framework edits and implementation of other modules.

## Fallback if blocked
If the supplied VM cannot install a Python dependency, prefer a compatible public dependency already available or document a tested user-space/stdlib path; do not silently omit required behavior. If the official target provider remains undecided, document both human-approved modes and keep live instructions conditional. A recorded demo does not replace fresh-clone installation acceptance.

## Log
- 2026-11-20: Planned only. Root files, clean installation and VM have not been changed or tested by this planner.
- 2026-11-20T14:33:00+00:00: claimed by claude-2 under SPEED MODE (human decision Miguel 14:30 UTC; multiple WS4 claims authorized).
