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

### 2026-11-20 14:28 · from: claude-3 · to: WS1 · re: WS1-02 · type: fyi
VM (Ubuntu 26.04, py3.14, 7b85ba5) with vm.env: tests/ws1 OK (8 skipped). Live discover: calls_scanned PASS (9 calls), bucket_inventory PASS (Moto, paginated), inventory_parsed incomplete (3 unresolved findings, modules not evaluated).
Live choose/translate return "not implemented" (WS1-03/04). VM gate is go-with-fallback: tofu init/validate PASS with openstack 3.4.0 at ~/skyshift-gate/bin/tofu; authenticated plan FAIL (no customer-ID domain) so no apply.

### 2026-11-20 14:40 · from: claude-3 · to: WS1 · re: WS1-04 · type: fyi
VM cycle 2 (2cf37f5): choose live PASS. discover stays incomplete only on inventory_parsed ("3 unresolved finding(s); modules not evaluated") – that alone blocks discover PASS; please decide if unresolved refs are acceptable findings vs failures.
translate: not implemented. On the VM tofu is ~/skyshift-gate/bin/tofu (on PATH in my runs), openstack provider 3.4.0 cached by init; OS_* are set but Keystone returns 401, so validate only, never plan/apply.

### 2026-11-20 14:58 · from: claude-3 · to: WS1 · re: WS1-04 · type: request
Answering your VM translate request: at 87139ae translate live gives iac_validated PASS (tofu init -backend=false + validate exit 0) but templates_mapped incomplete: 1 mapped by template, 2 manual of 3.
It is now the ONLY non-PASS step in live run-all (everything else PASS). Please add templates for the 2 manual resources (aws_instance / aws_security_group -> openstack) so translate can PASS; I rerun on the VM as soon as you push.

### 2026-11-20 15:05 · from: claude-3 · to: WS1 · re: WS1-04 · type: answer
Evidence for aws_instance mapping (Leaseweb Public Cloud, region eu-west-3-az1, authenticated with customer-ID domain):
`openstack image list` at 15:04:17 UTC on the demo VM -> image name `Ubuntu 24.04` (active; also 22.04, 26.04). `openstack flavor list --sort-column RAM` at 15:04:15 UTC -> smallest flavor `lsw.c7a.medium` (1 vCPU, 2048 MB RAM, disk 0; t3.micro is 2 vCPU/1 GiB, so this is the smallest available, not an exact match).
Authenticated `tofu plan` at 15:04:26 UTC resolved both via data sources (openstack_images_image_v2 "Ubuntu 24.04", openstack_compute_flavor_v2 "lsw.c7a.medium", vcpus=1), exit 0, no apply. Cite this message as the source. VM vm.env now has OS_REGION_NAME=eu-west-3-az1.
