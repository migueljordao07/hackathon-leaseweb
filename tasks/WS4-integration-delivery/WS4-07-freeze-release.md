---
id: WS4-07
title: Freeze rehearse and release the verified demo path
workstream: WS4
status: todo
owner: null
priority: P0
depends_on: [WS4-03, WS4-04, WS4-06]
blocks: []
files: [README.md, demo/demo-script.md, demo/backup-recording-checklist.md, demo/rehearsal-log.md, tests/ws4/test_release.py]
estimate: 45m
claimed_at: null
updated_at: null
---

## Goal
Perform the final clean-clone/rehearsal release gate, enforce the 14:30 feature freeze and 15:15 code freeze, and leave one verified live-or-labelled-backup path for the maximum five-minute pitch.

## Context
Official rules require a public, buildable repository and a pitch no longer than five minutes; live demo operation affects scoring. Original proposal sections 7-12 require two rehearsals and backup recording after the 14:30 feature freeze, final README by 15:15, no merges after code freeze, synthetic data, cited/computed claims and explicit fallback labels. This task validates; it does not turn incomplete evidence green. Executor `claude-2`; Miguel owns release/run-all decision, Diogo owns timing/recording, and relevant human specialists sign their measured areas.

Unavoidable cross-workstream dependency is inherited through WS4-06: this release consumes the landed WS1/WS2/WS3 implementation and human WS0 decision. If the human gate selected Airlock or required checks remain incomplete, release a clearly reduced/recorded fallback approved by humans and mark SkyShift live claims incomplete; never rewrite evidence.

## Steps
1. Before 14:30, pull origin/main, read channel/inbox and triage only P0 demo blockers. Humans explicitly cut optional P1/P2 work in comms. At 14:30 record feature freeze in the rehearsal log; afterward accept only bug/demo fixes through existing scoped tasks.
2. Build a fresh Python 3.10+ Linux clone, follow README exactly, run all offline tests and run-all stub. With approved VM access, run the final live candidate and independently verify canonical JSON, object hashes/counts, unchanged app, parity, sever history, evidence chain and report hash.
3. Rehearse the exact script twice with timers and screen transitions. Keep each run <= 5:00, target <= 4:45. Record actual durations, commit, final hash, live/replay/recorded segments, failures and human verifier names in the append-only rehearsal log.
4. Produce and verify the backup according to the checklist: sanitized terminal, no secret values, explicit replay/recording banner, readable local playback without network, same commit/final hash, and duration <= 5:00. Keep the binary outside Git unless humans choose a public artifact location.
5. Update README/script only for facts confirmed by the final run. At 15:15 record code freeze and merge no more changes. Tagging/pushing is a human/release action outside this task unless explicitly authorized; never commit unrelated local files.
6. Run release assertions and inspect Git status/diff. Record exact commit on origin/main, remote/public status, remaining human-only limitations and selected stage fallback. Use the verified recording rather than a post-freeze code change.

## Acceptance criteria
- `python -B -m unittest discover -s tests -p 'test_*.py' -v` and `python -B -m unittest tests.ws4.test_release -v` exit 0 in a fresh Linux clone. Release tests validate CLI/help, stub exit 2, artifact/report schema, chain recomputation, README commands, no tracked `.env`/generated output and demo-document timing fields.
- If presented as live PASS, the final `python -m skyshift.cli run-all --workload fixtures/aws_workload --out out` exits 0 on the human-approved VM-like environment and all deterministic source checks independently match evidence. Otherwise the chosen fallback is visibly labelled replay/recorded/incomplete and the script says which checks were not live.
- `demo/rehearsal-log.md` contains two real rehearsals after feature freeze, each <= 5:00, plus commit/hash/environment/limitations and human verifiers. `demo/backup-recording-checklist.md` is completed for a locally playable <= 5:00 recording with no secret values.
- Feature freeze is recorded at 14:30; code freeze at 15:15. `git log`/remote state show no merges after the code-freeze record. Any post-freeze discovery is handled by the approved recording or human incident decision, not an unreviewed commit.
- `python tasks/board.py --check` exits 0 and `git status --short` shows no generated/staged/unrelated files. Done Log includes acceptance commands/results and origin/main commit. Commit `[WS4-07] chore: freeze and verify the demo release (claude-2)` before 15:15 with named files only.

## Out of scope
New features after 14:30, any merge after 15:15, unapproved release tag/publication (scoped task claim/code commits and pushes follow tasks/README.md), editing other workstreams, making VM checks up, hiding failures, committing credentials/generated artifacts/video and claims beyond measured evidence.

## Fallback if blocked
Cut optional scope before feature freeze with human approval. If live infrastructure/model/network fails, use the locally verified backup with clear labels and run available deterministic checks live. If the backup also fails verification, present the report/artifacts and state the limitation; do not attempt an unreviewed post-freeze fix or claim a successful live run.

## Log
- 2026-11-20: Planned only. Feature/code freeze, rehearsals, backup, clean-clone release and VM acceptance have not occurred.
