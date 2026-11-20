# Planning release audit

Planning only. No SkyShift modules, fixtures, live services or demo recordings were implemented. The complete root planning card was recovered and reviewed; no inaccessible truncated requirement remains.

## Mapping and first claims

| Workstream | Future executor | Human supervision | First claim | Tasks |
|---|---|---|---|---|
| WS0 | human only; owner null | Ricardo and Miguel | WS0-01 | 1 |
| WS1 | claude-1 / Claude Code | Ricardo; Diogo for discovery/catalogue | WS1-01 | 5 |
| WS2 | gemini / Gemini CLI | Carolina; Miguel for migration | WS2-01 | 6 |
| WS3 | codex / OpenAI Codex | Francisco | WS3-01 | 7 |
| WS4 | claude-2 / Claude Code | Miguel; Diogo for report/pitch | WS4-01, after the three stubs | 7 |

This preserves exactly two Claude Code instances, one Codex and one Gemini CLI, with integration on Claude. Moving CLI/report ownership into WS4 avoids shared-file collisions while humans retain their specialist review roles. All 26 tasks start todo with owner/claimed_at/updated_at null; a suggested executor is not a claim.

## Reconciled findings

- Communication lives exclusively under tasks/comms/. Root comms/ is absent.
- Reconciled all reciprocal depends_on/blocks links, with independent WS0 and WS1/WS2/WS3 stubs; WS4-01 waits only for those stubs. Real cross-stream edges are explicit and justified.
- WS2-06 accepts measured WS2 component success with overall exit 2 while unrelated streams are incomplete. It does not wait for final severance PASS or form an implicit integration cycle. Negative mutation is injected after copy, not overwritten by rclone. Final stage rehearsals remain after 14:30 in WS4.
- WS3-07 now includes its missing P0 run-all demo-path acceptance and explicit human-gate/real-runner dependency. It does not wait on WS4 live integration. WS3 owns real CONNECT proxy behavior, approved range-feed loading with provenance/freshness, bounded local demo telemetry receiver and config-only retry; synthetic fixtures alone never prove live denial. Model/schema output cannot decide verdicts.
- Completion and step envelopes have distinct allowed modes; model completion stubs use replay/incomplete, severance stubs use stub/incomplete. Data arguments and run-root output_dir are explicit in the shared API.
- Test-package marker ownership is explicit. Before WS4's shared tests/__init__.py lands, stub acceptance uses directory discovery to avoid importing an unrelated installed tests package.
- WS4 retains shared CLI/requirements/README, deterministic evidence, distribution, rehearsals and release ownership. Feature freeze 14:30; code freeze 15:15 with no later merges; pitch and backup maximum five minutes.

## Executed offline verification

On Windows, Python 3.11.16, during the planning review on 2026-11-20:

- `python -B tasks/test_board.py -v`: 19 tests passed. Includes parser/field/status/path errors, duplicates, unknown dependencies, cycles, reciprocal links, exact/prefix cross-stream collisions, deterministic rendering, read-only check, generation, readiness waiting for done (not cut/review), invalid-graph write prevention and human-only ready label.
- `python -B tasks/board.py`: regenerated BOARD.md from 26 tasks.
- `python -B tasks/board.py --check`: schema, graph and ownership valid.
- `python -B tasks/board.py --ready WS0` through WS4: WS0-01 human-only; WS1-01, WS2-01 and WS3-01 ready; no WS4 task ready initially.
- `python -B tasks/summarize.py`: computed counts, per-stream task-minutes and weighted DAG longest path below.
- `python -B tasks/verify_committed.py`: passed in an isolated archive of committed tasks/ without the untracked proposal; repeated all 19 tests, --check, five --ready modes and summary. All 26 task files have exact ordered body sections; communication files, local Markdown links and generated board snapshot match. This is a Windows archive check, not supplied-VM or product acceptance.
- Git status inspected before edits/staging; staged diff checked before commits; only named planning files are eligible. Pre-existing research edits and the untracked local proposal are not framework deliverables and must stay unstaged.

These checks validate the planning utility and documents, not product functionality or Linux/VM behavior. Product acceptance commands in task files are future commands; they were not executed during planning.

## Critical path and schedule risk

Computed weighted DAG chain: WS2-01 -> WS2-02 -> WS2-04 -> WS2-05 -> WS2-06 -> WS4-05 -> WS4-06 -> WS4-07, estimated 390 minutes.

Per-stream estimated task-minutes: WS0 30, WS1 205, WS2 285, WS3 315, WS4 365. These are planning estimates, not measurements. The DAG calculation is a lower bound: one-task-per-executor serialization, reviews, claims, merges, service setup and interruptions can extend it. Current plans are all P0, so merely saying 'cut P1/P2' cannot recover this schedule. Humans must explicitly reprioritize/replan or approve a narrower honestly incomplete/recorded demo before authorizing execution. Original before-lunch/14:00 checkpoints are targets, not claims or a feasible restart promise.

## Remaining human gates

WS0-01 stays todo, owner null. validation.md says NOT RUN. Only a human may record the five VM checks and go/go-with-fallback/switch-to-Airlock decision. Provider/schema/registry, target S3, private credential availability, real EU-hosted model latency or replay fallback, and approved proxy/range feeds remain unverified. All access values stay outside Git.

Humans must approve executor/supervisor allocation, time/scope cuts, any reduced demo, actual post-freeze rehearsals/backup and final publication/release. The framework does not authorize infrastructure apply or production data. Open questions are in tasks/comms/inbox-humans.md. No automated board check can replace the human gate.
