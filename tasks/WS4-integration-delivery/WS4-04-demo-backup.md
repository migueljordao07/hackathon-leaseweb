---
id: WS4-04
title: Rehearse the five-minute demo and prepare a labelled backup recording
workstream: WS4
status: todo
owner: null
priority: P0
depends_on: [WS4-01]
blocks: [WS4-07]
files: [demo/demo-script.md, demo/backup-recording-checklist.md, demo/rehearsal-log.md]
estimate: 40m
claimed_at: null
updated_at: null
---

## Goal
Create an executable five-minute stage script, rehearsal record and backup-recording checklist that show measured SkyShift results honestly and recover from network/model/demo failures.

## Context
Official pitch limit is five minutes. Original proposal section 7 allocates 0:00-0:40 problem/discover, 0:40-1:30 choose/translate, 1:30-2:20 migrate, 2:20-3:30 run/parity/sever, 3:30-4:10 evidence and 4:10-5:00 business. Sections 8, 10 and 12 require feature freeze at 14:30, two rehearsals plus a backup recording, code freeze at 15:15, replay labels, computed/cited claims and no universal guarantee/certificate/global-first claim. Diogo supervises script/recording; Miguel verifies terminal commands and evidence. Executor remains `claude-2`; this is planning for a future Git-only implementation, not a claim that a recording exists.

## Steps
1. Claim through Git, read current CLI/report/README and edit only listed files. Use command/output placeholders tied to actual `out/*.json` fields; never script invented counts, savings, hashes or blocked connections.
2. Write a timecoded script of at most 4:45 target duration, leaving recovery margin. Name speaker, exact command/screen, one sentence of narration and fallback jump for each segment. Focus live narration on migrate, sever and evidence while `run-all` carries transitions.
3. State claims narrowly: these N checks passed, M measured connections were blocked, object counts/hashes matched, and this is the first open-source combination the team found. Never say mathematical guarantee, zero leakage, certificate, DORA compliance or first in the world.
4. Create a backup checklist covering clean terminal, readable font, sanitized environment, synthetic fixtures, no credential visibility, services/ports, deterministic artifact reset, replay banner, network-off recovery, full run capture, audio, 1080p/local playback, duration under five minutes and two-person verification. A replayed model response is labelled; deterministic copy/checksum/parity/proxy still run live where available.
5. Create an append-only rehearsal log template and record two real timed rehearsals after feature freeze. Capture actual duration, failing transitions, chosen live/recorded segments, evidence hash, commit and corrective action. Do not pre-fill results.
6. At 14:30 cut optional P1/P2 features rather than lengthen or fake the demo. At 15:15 stop merges and use the verified recording if a new issue would require code changes.

## Acceptance criteria
- `demo/demo-script.md` has monotonic timestamps, target duration <= 4:45 and hard maximum 5:00; every stage segment names an exact CLI/report action and a fallback jump. Manual timing from two rehearsals is appended to `demo/rehearsal-log.md`, both <= 5:00 before done.
- `demo/backup-recording-checklist.md` includes all sanitization, reset, service, output, replay-label, deterministic-live-step, audio/video, duration, offline playback and verifier checks. A human checks each item for the actual final recording; an unchecked template stays review, not done.
- Script claims are traceable to output fields or cited README/target sources and use placeholders until measured. It states report limitations and never claims VM validation, certification, universal isolation, invented savings or global novelty.
- Before done, two humans verify the backup opens locally without network, displays the same commit/final hash recorded in the rehearsal log, contains no secret values and finishes within five minutes. The recording file itself stays outside Git unless humans explicitly approve a public artifact location.
- `python tasks/board.py --check` succeeds after reciprocal links. Commit `[WS4-04] docs: prepare demo and backup runbook (claude-2)` with named files only; Git handoff records the recording location without credentials/private URLs.

## Out of scope
Creating product behavior, committing a large video, editing pitch slides, fabricating rehearsal entries, exposing credentials, extending the pitch beyond five minutes and post-freeze feature work.

## Fallback if blocked
If live model/provider access fails, switch to a visibly labelled cached response or verified recording while keeping available deterministic checks live. If a deterministic step is unavailable, show the recorded full run and say which current check is not live; never substitute mock output. Cut business detail before technical proof if rehearsal exceeds five minutes.

## Log
- 2026-11-20: Planned only. No rehearsal, backup recording, VM run or measured demo result has occurred in this task.
