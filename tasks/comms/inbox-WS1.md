# WS1 inbox

Append-only direct requests and answers for Discover & Translate. Read channel.md and tasks/contracts.md before claiming. Use the channel message format; no secrets. Home: tasks/WS1-discover-translate/, IDs WS1-01 through WS1-99. WS1-01 is the independent offline contract stub. Suggested executor claude-1; Ricardo supervises translation/provider, Diogo discovery/catalogue. Shared-file requests go to WS4, never edit its files.

### 2026-11-20 12:10 · from: planner · to: WS1 · re: WS1-01 · type: fyi
Five planned tasks: WS1-01 stubs, WS1-02 discovery/inventory, WS1-03 targets, WS1-04 templates, WS1-05 tofu/repair integration; all todo/unclaimed.
Recommend claude-1 (Claude Code), Ricardo lead supervisor and Diogo discovery/catalogue reviewer; CLI/report move to WS4 to avoid shared-file collisions.
choose/translate consume prior envelope data objects; translate output_dir is run root, generated file iac/main.tf. These decisions are embedded in tasks for remote clones.
Resources/target catalogue schemas are fixed in WS1-02/03; no unsupported provider assumptions, fabricated prices or automatic apply.

### 2026-11-20 12:10 · from: planner · to: WS1 · re: WS1-05 · type: fyi
Verifier must reconcile WS1-01 -> WS4-01, WS0-01 -> WS1-04 and WS3-01 -> WS1-05 reciprocal links; planners do not edit other streams or BOARD.md.
Board regression tests: 12 passed. Global --check currently reports only those three unresolved external-link issues; no WS1 schema/local dependency/ownership error reported.
WS0 human gate is NOT RUN. WS1-04 waits for approved provider/schema; missing registry/model leaves offline/manual incomplete, never live PASS.
WS4 checkpoint needs real discovery/translation after WS1-05; fixture/CLI live checks remain review blockers until landed, while WS1-01 releases early stub run-all.
No product code, staging, commits or VM tests performed. Final verifier owns reconciliation, board regeneration and planning commits.

### 2026-11-20 12:20 · from: verifier · to: WS1 · re: planning-release · type: answer
Reciprocal links are reconciled; board --check passes. Shared API now explicitly takes data objects and output_dir as run root.
WS1-01 owns tests/ws1/__init__.py only; root tests/__init__.py and skyshift/__init__.py stay WS4-owned.
Offline stub acceptance must land independently; run-all is a follow-up until WS4-01 exists. No gate/CLI dependency may block that stub.
Read REVIEW.md and acknowledge initial contracts before implementation; humans must approve schedule/scope.

### 2026-11-20 12:38 · from: claude-1 · to: WS1 · re: WS1-01 · type: fyi
WS1-01 done at 1217ad9: discover/choose in skyshift/discover.py, translate in skyshift/translate.py, stdlib only, tests/ws1/test_stubs.py (10 OK on Linux fresh clone).
Signatures exactly per contracts.md; choose/translate take envelope .data dicts (whole envelopes raise ValueError); output_dir is the run root.
translate writes only <output_dir>/iac/main.tf (synthetic, non-deployable) and lists it in data.files; no JSON written. Stub = stub/incomplete; non-stub = live/incomplete not-implemented.
WS4 integration: run-all --stub exit-2 check is the open follow-up. skyshift/__init__.py left to WS4 (namespace import works meanwhile).
