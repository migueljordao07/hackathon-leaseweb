# Human decisions inbox

Append-only questions/answers using channel.md format. Do not publish secrets or private access details; record availability only and arrange credential delivery privately. Only humans sign the VM go/switch gate. Humans can cut/reprioritize scope; reciprocal dependencies must be updated and validated.

### 2026-11-20 12:01 · from: planner · to: humans · re: WS0-01 · type: request
Please perform/sign the five-check 30-minute VM gate in tasks/WS0-setup/WS0-01-vm-validation.md; all checks currently NOT RUN.
Confirm official Leaseweb provider versus OpenStack, target S3 availability, and credential availability without publishing values.
Confirm EU-hosted model access/latency or labelled replay fallback; if fewer than four VM checks pass, approve Airlock replan.
Confirm executor/human mapping in tasks/README.md and adjust scope to remaining time; timeline checkpoints are targets, not completed work.

### 2026-11-20 12:20 · from: verifier · to: humans · re: planning-release · type: request
Please approve/reprioritize the 26-task plan before implementation: its weighted DAG lower bound is 390 estimated minutes and all tasks are currently P0.
Original before-lunch/14:00 milestones are not a feasible restart promise; select a reduced honestly incomplete/recorded demo or a separately approved Airlock replan if needed.
Please confirm WS0 human operator, provider/schema, target storage, private access availability, model/replay route and approved range feeds; no VM check has run.
Confirm mapping in REVIEW.md and who signs final rehearsals/backup/public release; keep all credential values outside Git.

### 2026-11-20 12:45 · from: claude-1 · to: humans · re: WS1-02 · type: request
WS1-02 offline acceptance passes (Windows + WSL2 Ubuntu, with/without deps); left in review because its read-only live inventory test needs WS0-01 go and source access.
WS1-03/04/05 all chain behind WS1-02 done, so WS1 is idle until either the live test runs or a human accepts offline completion with the live test as a tracked follow-up. Please decide.
Also: WS2/WS3 agents are working in the same local working copy as claude-1 (shared index). Separate clones are strongly advised to avoid cross-stream commits.

### 2026-11-20 13:19 · from: claude-2 · to: humans · re: WS4-scope · type: blocker
WS4-01 is in review (bd1e8c6) and needs a Linux run (WSL2/VM) before it is done; until then WS4-02/03/04, WS2-06 and WS3-07 are not ready.
Remaining WS4 estimates total 305m vs ~74m to feature freeze and ~119m to code freeze; WS0-01 is still todo, so WS4-05/06 (live) cannot start.
WS4-07 (release) depends on WS4-06, so as planned it cannot land before code freeze. Please decide: cut WS4-05/06 or re-point WS4-07 to WS4-03/04.
Recommended order once WS4-01 is done: WS4-03 (README/LICENSE/requirements/.gitignore, mandatory for submission), then WS4-04 (demo script/backup), then WS4-02.
Fallback demo: labelled stub run-all + report.html (exit 2, STUB / NOT VM VALIDATED), never presented as live proof.

### 2026-11-20 14:21 · from: claude-3 · to: all · re: WS0-01 · type: fyi
Human gate decision (Miguel, 14:20 UTC): go-with-fallback 4/5, recorded in tasks/WS0-setup/validation.md.
PASS on the demo VM: 1 Moto + Leaseweb bucket put/get/list; 2 rclone 10/10 SHA-256 match; 3 tofu init/validate (openstack 3.4.0); 5 proxy denies AWS ranges, allows Leaseweb S3.
Check 4 NOT RUN (GPU server had no driver/model); labelled replay fallback tested. Authenticated tofu plan FAIL (OpenStack customer-ID domain missing): no apply.
Live tasks gated on WS0-01 may proceed against Leaseweb S3 target (SKYSHIFT_TARGET_*) and Moto source on 127.0.0.1:5000. Live model retry in progress.

### 2026-11-20 14:52 · from: claude-1 · to: humans · re: WS1-04 · type: request
Live run-all is 7/8 PASS; translate is incomplete only because 2 of 3 resources are manual (iac_validated PASS on VM).
To map aws_instance honestly WS1 needs a real Leaseweb Public Cloud image name and flavor name (non-secret) to put in the catalogue with a source. aws_s3_bucket targets a pre-provisioned Leaseweb Object Storage bucket (no verified OpenTofu resource): stays manual unless a human rules otherwise.
No PASS will be produced without that evidence.
