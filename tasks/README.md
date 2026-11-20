# Git-only execution guide

Read this file, [contracts.md](contracts.md), [BOARD.md](BOARD.md), `comms/channel.md`, your inbox, and your selected task before claiming. These tracked files are sufficient for a fresh clone; no private vault, untracked proposal, shared server, shared filesystem or chat is required between executors. Runtime services run locally or on the human-approved demo VM, not as agent coordination infrastructure. Planning is not implementation and does not authorize starting features until the framework is released by humans.

## Homes, IDs and suggested staffing

| Stream | Task home | Suggested executor | Human supervisor |
|---|---|---|---|
| WS0 | WS0-setup | human gate; owner stays null | Ricardo (provider), Miguel (VM/integration) |
| WS1 | WS1-discover-translate | claude-1 (Claude Code) | Ricardo, Diogo for discovery/catalogue |
| WS2 | WS2-data-parity | gemini (Gemini CLI) | Carolina, Miguel for migration |
| WS3 | WS3-severance-ai | claude-3 (Claude Code) | Francisco |
| WS4 | WS4-integration-delivery | claude-2 (Claude Code) | Miguel, Diogo for report/pitch |

Recommendation, not subscription/VM-access confirmation. The revised allocation uses three Claude Code processes (WS1, WS3, WS4) and one Gemini CLI process (WS2); Codex is unavailable. `claude-3` is a distinct Git task identity, not a third confirmed Claude subscription seat. Check account concurrency/rate limits before running all three Claude processes. WS4 stays the exclusive owner of shared integration files. Humans retain their original specialties. WS1/WS2/WS3/WS4 IDs occupy separate 01-99 ranges and directories; do not renumber or create tasks in another stream. First claim: WS1-01, WS2-01, WS3-01; WS4-01 becomes ready once those stubs are done. WS0-01 runs independently and must never depend on those stubs.

## Exact task format

One file per task: `tasks/<home>/<ID>-<slug>.md`. The complete original planning card was recovered; no text is missing after the originally truncated `files` requirement. Exactly these YAML fields are mandatory; no additional front-matter keys:

```yaml
---
id: WS1-01
title: Contract-honouring discovery and translation stubs
workstream: WS1
status: todo
owner: null
priority: P0
depends_on: []
blocks: []
files: [skyshift/discover.py, skyshift/translate.py]
estimate: 30m
claimed_at: null
updated_at: null
---
```

This is an illustrative template, not another registered task. Fields:

- id: `WS0-01` through `WS4-99`, two-digit positive suffix, unique and matching filename/home.
- title: nonempty string (quote strings containing punctuation if needed).
- workstream: WS0, WS1, WS2, WS3 or WS4.
- status: todo, claimed, in_progress, blocked, review, done or cut.
- owner: null, claude-1, claude-2, claude-3 or gemini. A human gate uses null; human signatures belong in Log, not an invented owner enum.
- priority: P0, P1 or P2. Every feature stream includes a P0 demo-path task.
- depends_on: required list of task IDs, even `[]`; dependency direction is prerequisite -> this task.
- blocks: required list of task IDs, even `[]`; reciprocal reverse index of depends_on, not a second independent graph.
- files: required nonempty list of exact repository-relative POSIX file paths, the only implementation files that task may edit. No glob, directory, absolute path, parent traversal, credentials file or `.env`. `.env.example` is permitted only for WS4. Serial tasks within the same stream may share files; no overlapping ownership across streams. The task's own status/Log and append-only comms are coordination exceptions, not permission for arbitrary planning edits.
- estimate: integer minutes with `m`, 20m through 60m. Planning estimates, not measured execution durations.
- claimed_at, updated_at: null initially; subsequently quoted ISO-8601 timestamp with timezone (example `2026-11-20T13:42:00+00:00`). Use current actual time, not the example. Claimed/in_progress/review tasks require owner and claimed_at, except the human gate.

Limited parser: simple scalar `key: value`, JSON-style bracket lists with bare or quoted string items, or indented `  - item` lists. No YAML anchors, objects, multiline strings, comments in values or implicit dates. Body headings exactly: `## Goal`, `## Context`, `## Steps`, `## Acceptance criteria`, `## Out of scope`, `## Fallback if blocked`, `## Log`. Steps are ordered. Log is append-only with dated notes. Context cites relevant portable contract entries and original spec section numbers plus enough actual scope not to require the untracked original.

## Claim and work protocol

1. Start with a clean personal clone on main (`git switch main`; `git pull --rebase origin main`). Never pull/rebase over someone else's dirty files. Read channel and your inbox after every pull and before every claim. Run `python tasks/board.py --ready WS1` (substitute stream).
2. Take only one ready task. Edit only its front matter to claimed, set owner and current claimed_at/updated_at; add a dated claim Log. Explicitly stage that task file only. Commit `[WS1-01] chore: claim task (claude-1)` and push immediately. Do not implement before your claim push is accepted.
3. If push is rejected, pull --rebase, re-read task/channel/inbox and recheck readiness. A conflicting accepted claim wins; abandon your unpushed claim edits without discarding other work, choose another ready task. Never force-push or override a winner. If both versions claim the same task, keep the already-remote claim.
4. Change to in_progress and make small scoped commits, e.g. `[WS2-03] feat: compare object hashes (gemini)` or `[WS3-01] feat: add offline stubs (claude-3)`. Owner is the actual executor. Stage named files only; never `git add .`. Edit only files listed on the task. Request shared-file/dependency changes through the appropriate inbox rather than editing another stream's files.
5. Rebase before pushes; rerun affected acceptance and `python tasks/board.py --check`. Feature workers do not regenerate BOARD.md for each claim (shared hotspot); live --ready reads task files. WS4/verifier owns periodic `python tasks/board.py` regeneration. --check validates task structure/graph, not snapshot freshness.
6. Claims with no updated_at/Log progress for 45 minutes may be reclaimed only after a channel notice and checking remote history. Record old/new owner and reason in Log; commit/push claim through the same race protocol. Do not reclaim an active recent task by timestamp alone.
7. If blocked: set blocked, update timestamp, append reason and demo-safe fallback to Log, message the relevant inbox, commit/push, release your active claim and take another ready task. No secret values in requests; humans arrange credentials/access privately. Blocked dependencies are not ready.
8. Review requires runnable acceptance commands plus actual results, environment and limitations in Log. Do not claim VM tests from local stubs. Done requires reviewed acceptance on a VM-like Linux environment, code on origin/main, run-all intact and final dated Log with commands/results and commit reference. Use review while acceptance/code landing is pending. WS0-01 alone requires human VM evidence and human sign-off to become done.

Dependencies resolve only when all depends_on tasks are done. `cut` is NOT done: explicitly remove/replan dependent requirements, update reciprocal blocks, get human approval and rerun --check. Never silently skip a required check to make the graph green. Cross-stream dependencies normally target stub `-01` tasks; unavoidable real integration dependencies must contain the literal phrase `Unavoidable cross-workstream dependency` and justify each dependency in Context. The human VM gate is an unavoidable prerequisite for live tests, never for offline stubs.

## Communication, contracts and conflicts

Canonical comms home is `tasks/comms/`, as explicitly clarified by the operator. Do not create repository-root comms files. [channel](comms/channel.md) broadcasts; inbox-WS1 through WS4 are direct requests; inbox-humans handles provider, credentials availability, go/switch and cuts. Every message is one append-only block with the header documented in `tasks/comms/channel.md`, followed by at most about five lines. Read addressed requests, answer by appending, never rewrite history.

Contract change: append type contract-change to channel plus affected inboxes. Only WS4 edits contracts.md after review; affected streams acknowledge in channel before consuming the changed interface. Until then retain v1 or mark blocked. Dependencies and ownership changes need the same broadcast and reciprocal-link validation. Framework maintenance changes are WS4/verifier-owned and explicitly announced.

Conflict resolution: preserve both comms entries and both dated Log entries. Do not accept ours/theirs blindly. For implementation conflicts, stop, notify owning stream, let the listed owner reconcile and rerun tests. No simultaneous cross-stream file ownership. Never rewrite Git history, force push, commit secrets or stage unrelated local changes. GitHub is the shared truth; local terminal output is not a cross-computer handoff until its sanitized result is committed in Log/comms.

## Gates, freezes and scope control

WS0-01: five real VM checks within 30 minutes, human go if 5/5 or 4/5 plus an explicit fallback; otherwise switch to Airlock Plan B. Offline stubs can proceed without the gate; live tasks depend on it. No autonomous gate completion, infrastructure apply, production data or credential publication.

Targets: early eight-step stubs; discover/translate/migrate/parity real before 12:30; severance by 14:00; feature freeze 14:30, two rehearsals and labelled backup recording; code freeze 15:15, no merges afterward. Schedule recovery requires cutting P1/P2 or a human-approved reduced demo, never representing stubs/replays as live proof. Maximum pitch five minutes. After feature freeze only bug/demo tasks; after code freeze no merges, use approved recorded backup if necessary.

## Board utility

Python 3.10+ standard library only; no installation required:

- `python tasks/board.py`: validate and regenerate BOARD.md in stable workstream/ID order.
- `python tasks/board.py --check`: read-only schema, dependency/DAG, reciprocal blocks, ownership and required-section validation; exit 0 on success, 1 on errors. Does not require all future reserved tasks to exist.
- `python tasks/board.py --ready WS2`: validate, then list todo tasks whose dependencies are all done, ordered by priority/ID. Human gate is labelled human-only.
- `python -B tasks/test_board.py -v`: offline regression tests for the parser, required fields, status/claim values, graph, ownership, unsafe paths and deterministic rendering. These are planning-tool tests, not VM/product acceptance.
- `python -B tasks/summarize.py`: validate and compute task counts, per-stream task-minute totals and the weighted DAG critical path. This is a lower bound, not a same-executor schedule or measured runtime; see REVIEW.md for the release audit and human time/scope decision.
- `python -B tasks/verify_committed.py`: export only HEAD's tasks/ to a disposable Git archive; check exact task sections, links, comms and BOARD.md freshness, then rerun offline tests, --check, all --ready modes and summary without untracked local context. Requires Git; no product/VM validation. Run after committing the full framework.

All WS0-WS4 planning tasks are present; BOARD.md is regenerated from their authoritative files. No product modules or live VM checks have been implemented by planning. Before WS4 adds tests/__init__.py, use `python -B -m unittest discover -s tests/ws2 -p test_stubs.py -v` (substitute stream/pattern), not dotted `tests.ws2` imports that could resolve an installed package. Each stream's stub owns its test-package marker; WS4 owns the shared root marker. Stub done requires its own reviewed Linux-like acceptance on origin/main; run-all checks are follow-ups until WS4-01 exists, never a circular prerequisite. Thereafter replacements must keep the landed run-all intact. Full live exit 0 belongs to WS4-06; WS1/WS2/WS3 component acceptance can finish with overall exit 2 only for unrelated incomplete steps, never incomplete checks in the component itself.
