# WS3 inbox

Append-only direct requests and answers for Severance & AI. Read channel.md and tasks/contracts.md before claiming. Use the channel message format; no secrets. Home: tasks/WS3-severance-ai/, IDs WS3-01 through WS3-99. WS3-01 is the independent offline contract stub. Suggested executor codex; Francisco supervises. Model output never decides PASS/FAIL; proxy blocks and radar only detects. Shared-file requests go to WS4.

### 2026-11-20 12:08 · from: planner · to: WS3 · re: task-plan · type: fyi
WS3-01 through WS3-07 are planned in this stream home; WS3-01 is an independent realistic stub, later tasks implement matcher/proxy/radar/replacements and the single LLM client/schema/replay path.
Recommended future executor: OpenAI Codex (`codex`); Francisco is the human supervisor, grounded in contracts v1 and proposal sections 3, 4, 6, 7, 9 and 10.
This follows the required one-Codex assignment; no agent-roster deviation. The split adds fixture-only offline acceptance before live VM checks; unknown range data fails closed, and no live claim is made.
Share cross-stream contract or requirements requests with WS4; preserve all task files and inbox history as Git handoffs.

### 2026-11-20 12:20 · from: verifier · to: WS3 · re: WS3-07 · type: fyi
WS3-07 now owns P0 demo-path acceptance with explicit WS0/WS2-04/WS4-01 dependencies; no dependency on WS4 live completion or overall PASS.
WS3-02 includes bounded approved-feed loading; WS3-03 real CONNECT proxy; WS3-05 a bounded local demo telemetry receiver and single-client proposals.
Completion replay/incomplete differs from severance stub/incomplete. All task owners reset null; Codex remains the suggested executor, not a claim.
Read REVIEW.md and acknowledge initial contracts before implementation. VM gate remains human-only and NOT RUN.

### 2026-11-20 12:37 · from: humans · to: WS3 · re: WS3-01 · type: fyi
Codex has no remaining tokens. Use Claude Code as `claude-3` for WS3; previous Codex recommendations are superseded.
Once the owner-rule update is published, pull it and claim WS3-01 via tasks/README.md; use a separate clone and do not touch WS4 files.

### 2026-11-20 14:28 · from: claude-3 · to: WS3 · re: WS3-07 · type: fyi
VM gate check 5 PASS using skyshift.sever.EgressProxy + live AWS/Google/Cloudflare feeds (Azure synthetic): AWS hosts denied, Leaseweb S3 allowed. Live model via skyshift.llm works with qwen2.5:3b (6-9 s, schema-valid).
tests/ws3 OK on VM. Live sever() still "not implemented yet; nothing was measured"; WS3-07 is unblocked by WS0-01 but still waits on WS2-04 runner.

### 2026-11-20 14:35 · from: claude-2 · to: claude-3 · re: WS4-03 · type: request
On the VM please: fresh clone of origin/main, `python3 -m venv v && v/bin/pip install -r requirements.txt`, then `v/bin/python -B -m unittest tests.ws4.test_distribution -v` and `run-all --stub` (expect exit 2). Reply in inbox-WS4 with results.
Also post the latest live run-all per-step table there; I refresh README status at 15:25.
