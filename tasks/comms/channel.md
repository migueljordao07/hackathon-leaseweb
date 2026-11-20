# Git-only coordination channel

Read after every pull and before every claim. Append only; never rewrite or delete previous messages. Direct requests go to inbox-WS1.md through inbox-WS4.md; human access/go/cut questions go to inbox-humans.md. GitHub commits are the handoff transport; no shared disk, server or chat is needed.

Each message uses one header and at most about five following lines:

`### 2026-11-20 13:42 · from: codex · to: WS4 · re: WS2-03 · type: request`

Replace example time with actual UTC time; types: request, answer, fyi, blocker, contract-change. Recipients: WS1, WS2, WS3, WS4, humans or all. Append answers referencing the same task. Preserve both entries on merge conflicts. Never put credentials, tokens, signed URLs, private access details or raw object data here.

### 2026-11-20 12:01 · from: planner · to: all · re: contracts-v1 · type: fyi
Foundation fixes package paths, API/envelopes, stub exit 2, and output names in tasks/contracts.md.
The communication home is tasks/comms/; the operator clarified the inconsistent source layout before release.
WS1-01/WS2-01/WS3-01 are independent offline stubs; WS4-01 consumes them. WS0-01 is independent and human-only.
Full parent card recovered, including complete files-field requirements. No truncated requirement was guessed.

### 2026-11-20 12:01 · from: planner · to: all · re: staffing · type: fyi
Recommendation: WS1 claude-1, WS2 gemini, WS3 codex, WS4 claude-2, with human supervision per tasks/README.md.
This resolves conflicting child suggestions in favor of two Claude instances, one Codex, one Gemini, and Claude integration.
Planning is not product implementation. VM gate NOT RUN; feature freeze 14:30, code freeze 15:15, no merges afterward.
Contract changes require broadcast, WS4 edit, and acknowledgments from every affected stream.

### 2026-11-20 12:03 · from: planner · to: all · re: comms-layout · type: fyi
Operator clarification: all channel and inbox files live in tasks/comms/, not repository-root comms/.
The initial untracked files were moved before release and protocol/contract paths corrected.
Downstream planners must use tasks/comms/inbox-WS1.md through inbox-WS4.md and inbox-humans.md.

### 2026-11-20 12:20 · from: verifier · to: all · re: planning-release · type: fyi
All 26 tasks reconciled; board checks and 19 offline utility tests pass. Read tasks/REVIEW.md before claiming.
WS1 claude-1, WS2 gemini, WS3 codex, WS4 claude-2; all tasks todo/unclaimed, VM gate NOT RUN.
Initial contracts clarify data-object inputs/run-root outputs and distinct completion modes; acknowledge before implementation.
Component acceptance must not wait for overall live PASS. WS3-07 now owns explicit gated demo-path verification.
Critical-path lower bound is 390 estimated minutes; humans must replan scope/time, not promise original milestones.
